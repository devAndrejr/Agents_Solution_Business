"""
Sistema de Cache Inteligente para Economia Máxima de LLM
Cache agressivo de consultas e resultados para evitar re-processamento.
"""

import json
import hashlib
import pickle
import gzip
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)

class SmartCache:
    """Cache inteligente para consultas e gráficos - economia máxima de LLM."""

    def __init__(self, cache_dir: str = "cache", max_size_mb: int = 100):
        """
        Inicializa o cache.

        Args:
            cache_dir: Diretório para arquivos de cache
            max_size_mb: Tamanho máximo do cache em MB
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.max_size_bytes = max_size_mb * 1024 * 1024

        # Cache em memória para acesso ultra-rápido
        self._memory_cache = {}
        self._cache_stats = {
            "hits": 0,
            "misses": 0,
            "saves": 0,
            "tokens_saved": 0
        }

        # Configurações de TTL (time to live)
        self.cache_config = {
            # Consultas básicas - cache longo
            "produto_mais_vendido": timedelta(hours=6),
            "filial_mais_vendeu": timedelta(hours=4),
            "segmento_campao": timedelta(hours=4),
            "produtos_sem_vendas": timedelta(hours=12),
            "estoque_parado": timedelta(hours=2),

            # Consultas específicas - cache médio
            "consulta_produto_especifico": timedelta(hours=1),
            "consulta_une_especifica": timedelta(hours=2),

            # Dados base - cache curto
            "base_data": timedelta(minutes=30),

            # Default para outras consultas
            "default": timedelta(minutes=15)
        }

        logger.info(f"SmartCache inicializado - Diretório: {self.cache_dir}")

    def _generate_cache_key(self, query_type: str, params: Dict[str, Any]) -> str:
        """Gera chave única para cache baseada no tipo e parâmetros."""
        # Serializar parâmetros de forma consistente
        params_str = json.dumps(params, sort_keys=True, ensure_ascii=False)

        # Criar hash único
        content = f"{query_type}:{params_str}"
        return hashlib.md5(content.encode('utf-8')).hexdigest()

    def _get_cache_file_path(self, cache_key: str) -> Path:
        """Retorna caminho do arquivo de cache."""
        return self.cache_dir / f"{cache_key}.cache.gz"

    def _get_ttl_for_query(self, query_type: str) -> timedelta:
        """Retorna TTL apropriado para o tipo de consulta."""
        return self.cache_config.get(query_type, self.cache_config["default"])

    def get(self, query_type: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Recupera resultado do cache se disponível e válido.

        Returns:
            Resultado cached ou None se não encontrado/expirado
        """
        cache_key = self._generate_cache_key(query_type, params)

        # 1. Verificar cache em memória primeiro (mais rápido)
        if cache_key in self._memory_cache:
            cached_item = self._memory_cache[cache_key]
            if self._is_cache_valid(cached_item, query_type):
                self._cache_stats["hits"] += 1
                logger.debug(f"Cache HIT (memória): {query_type}")
                return cached_item["result"]
            else:
                # Remover do cache em memória se expirado
                del self._memory_cache[cache_key]

        # 2. Verificar cache em disco
        cache_file = self._get_cache_file_path(cache_key)
        if cache_file.exists():
            try:
                with gzip.open(cache_file, 'rb') as f:
                    cached_item = pickle.load(f)

                if self._is_cache_valid(cached_item, query_type):
                    # Colocar de volta no cache em memória
                    self._memory_cache[cache_key] = cached_item
                    self._cache_stats["hits"] += 1

                    # Adicionar tokens economizados
                    tokens_saved = cached_item.get("tokens_would_use", 100)
                    self._cache_stats["tokens_saved"] += tokens_saved

                    logger.debug(f"Cache HIT (disco): {query_type} - {tokens_saved} tokens economizados")
                    return cached_item["result"]
                else:
                    # Remover arquivo expirado
                    cache_file.unlink()

            except Exception as e:
                logger.warning(f"Erro ao ler cache: {e}")
                cache_file.unlink()  # Remove arquivo corrompido

        # Cache miss
        self._cache_stats["misses"] += 1
        logger.debug(f"Cache MISS: {query_type}")
        return None

    def set(self, query_type: str, params: Dict[str, Any], result: Dict[str, Any],
            tokens_would_use: int = 100) -> None:
        """
        Salva resultado no cache.

        Args:
            query_type: Tipo da consulta
            params: Parâmetros da consulta
            result: Resultado a ser cached
            tokens_would_use: Quantos tokens essa consulta usaria na LLM
        """
        cache_key = self._generate_cache_key(query_type, params)

        cached_item = {
            "result": result,
            "timestamp": datetime.now(),
            "query_type": query_type,
            "params": params,
            "tokens_would_use": tokens_would_use
        }

        # Salvar em memória
        self._memory_cache[cache_key] = cached_item

        # Salvar em disco (comprimido)
        try:
            cache_file = self._get_cache_file_path(cache_key)
            with gzip.open(cache_file, 'wb') as f:
                pickle.dump(cached_item, f)

            self._cache_stats["saves"] += 1
            logger.debug(f"Cache SAVE: {query_type}")

        except Exception as e:
            logger.error(f"Erro ao salvar cache: {e}")

        # Limpar cache se necessário
        self._cleanup_if_needed()

    def _is_cache_valid(self, cached_item: Dict[str, Any], query_type: str) -> bool:
        """Verifica se item do cache ainda é válido."""
        timestamp = cached_item.get("timestamp")
        if not timestamp:
            return False

        ttl = self._get_ttl_for_query(query_type)
        expiry_time = timestamp + ttl

        return datetime.now() < expiry_time

    def _cleanup_if_needed(self) -> None:
        """Limpa cache se exceder tamanho máximo."""
        try:
            # Verificar tamanho do diretório de cache
            total_size = sum(f.stat().st_size for f in self.cache_dir.glob("*.cache.gz"))

            if total_size > self.max_size_bytes:
                logger.info(f"Cache excedeu limite ({total_size/1024/1024:.1f}MB) - limpando...")

                # Listar arquivos por data de modificação (mais antigos primeiro)
                cache_files = sorted(
                    self.cache_dir.glob("*.cache.gz"),
                    key=lambda f: f.stat().st_mtime
                )

                # Remover arquivos mais antigos até ficar dentro do limite
                for cache_file in cache_files:
                    cache_file.unlink()
                    total_size -= cache_file.stat().st_size

                    if total_size <= self.max_size_bytes * 0.8:  # Deixar 20% de margem
                        break

                # Limpar cache em memória também
                self._memory_cache.clear()

                logger.info("Limpeza de cache concluída")

        except Exception as e:
            logger.error(f"Erro na limpeza de cache: {e}")

    def clear_all(self) -> None:
        """Limpa todo o cache."""
        # Limpar memória
        self._memory_cache.clear()

        # Limpar disco
        for cache_file in self.cache_dir.glob("*.cache.gz"):
            cache_file.unlink()

        # Resetar estatísticas
        self._cache_stats = {
            "hits": 0,
            "misses": 0,
            "saves": 0,
            "tokens_saved": 0
        }

        logger.info("Cache completamente limpo")

    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do cache."""
        total_requests = self._cache_stats["hits"] + self._cache_stats["misses"]
        hit_rate = (self._cache_stats["hits"] / total_requests * 100) if total_requests > 0 else 0

        return {
            "hits": self._cache_stats["hits"],
            "misses": self._cache_stats["misses"],
            "saves": self._cache_stats["saves"],
            "hit_rate_percent": round(hit_rate, 1),
            "tokens_saved": self._cache_stats["tokens_saved"],
            "cache_files": len(list(self.cache_dir.glob("*.cache.gz"))),
            "memory_cache_size": len(self._memory_cache)
        }

    def preload_frequent_queries(self, parquet_adapter) -> None:
        """Pre-carrega consultas mais frequentes no cache."""
        logger.info("Pre-carregando consultas frequentes...")

        from .direct_query_engine import DirectQueryEngine

        engine = DirectQueryEngine(parquet_adapter)

        # Lista de consultas para pre-load
        frequent_queries = [
            ("produto mais vendido", {}),
            ("filial mais vendeu", {}),
            ("segmento mais vendeu", {}),
            ("produtos sem movimento", {}),
            ("estoque parado", {})
        ]

        for query_text, extra_params in frequent_queries:
            try:
                query_type, params = engine.classify_intent_direct(query_text)
                params.update(extra_params)

                # Verificar se já está no cache
                if self.get(query_type, params) is None:
                    # Executar e cachear
                    result = engine.execute_direct_query(query_type, params)
                    self.set(query_type, params, result, tokens_would_use=150)
                    logger.debug(f"Pre-load: {query_text}")

            except Exception as e:
                logger.warning(f"Erro no pre-load de '{query_text}': {e}")

        logger.info(f"Pre-load concluído: {len(frequent_queries)} consultas")

    def get_popular_queries(self) -> List[str]:
        """Retorna lista de consultas populares baseada no cache."""
        popular = [
            "produto mais vendido",
            "filial mais vendeu",
            "segmento mais vendeu",
            "produtos sem movimento",
            "estoque parado",
            "faturamento mensal",
            "ranking filiais",
            "ranking segmentos"
        ]

        return popular

    def warm_up_cache(self, queries: List[str], parquet_adapter) -> Dict[str, Any]:
        """Aquece o cache com consultas específicas."""
        from .direct_query_engine import DirectQueryEngine

        engine = DirectQueryEngine(parquet_adapter)
        results = {"success": 0, "errors": 0, "skipped": 0}

        for query in queries:
            try:
                query_type, params = engine.classify_intent_direct(query)

                if self.get(query_type, params) is not None:
                    results["skipped"] += 1
                    continue

                result = engine.execute_direct_query(query_type, params)
                if result.get("type") != "error":
                    self.set(query_type, params, result, tokens_would_use=120)
                    results["success"] += 1
                else:
                    results["errors"] += 1

            except Exception as e:
                logger.warning(f"Erro no warm-up de '{query}': {e}")
                results["errors"] += 1

        return results