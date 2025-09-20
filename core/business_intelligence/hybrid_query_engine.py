"""
Motor de Consultas Híbrido - Economia Inteligente de LLM
Sistema que usa consultas diretas SEMPRE que possível e LLM apenas em último caso.
"""

import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
import re

from .direct_query_engine import DirectQueryEngine
from .smart_cache import SmartCache

logger = logging.getLogger(__name__)

class HybridQueryEngine:
    """
    Motor híbrido que economiza LLM ao máximo:
    1. Cache primeiro
    2. Consultas diretas
    3. LLM apenas se absolutamente necessário
    """

    def __init__(self, parquet_adapter, llm_adapter=None, enable_llm_fallback=False):
        """
        Inicializa motor híbrido.

        Args:
            parquet_adapter: Adapter para dados
            llm_adapter: Adapter LLM (opcional)
            enable_llm_fallback: Se True, permite usar LLM em último caso
        """
        self.parquet_adapter = parquet_adapter
        self.llm_adapter = llm_adapter
        self.enable_llm_fallback = enable_llm_fallback

        # Componentes principais
        self.cache = SmartCache(cache_dir="cache", max_size_mb=100)
        self.direct_engine = DirectQueryEngine(parquet_adapter)

        # Estatísticas de economia
        self.stats = {
            "cache_hits": 0,
            "direct_queries": 0,
            "llm_queries": 0,
            "total_tokens_saved": 0,
            "total_queries": 0
        }

        # Configuração de fallback
        self.llm_fallback_config = {
            "max_tokens_per_query": 200,  # Limite por consulta
            "daily_token_limit": 5000,    # Limite diário
            "enable_complex_queries": enable_llm_fallback,
            "fallback_threshold": 0.7     # Confiança mínima para usar direto
        }

        logger.info(f"HybridQueryEngine inicializado - LLM fallback: {enable_llm_fallback}")

    def process_query(self, user_query: str, force_direct: bool = False) -> Dict[str, Any]:
        """
        Processa consulta com estratégia híbrida de economia.

        Args:
            user_query: Consulta do usuário
            force_direct: Se True, força uso apenas de consultas diretas

        Returns:
            Resultado da consulta com informações de economia
        """
        start_time = datetime.now()
        self.stats["total_queries"] += 1

        query_lower = user_query.lower()
        logger.info(f"Processando query híbrida: '{user_query[:50]}...'")

        # 1. PRIMEIRO: Verificar cache
        result = self._try_cache(user_query)
        if result:
            result["processing_time"] = (datetime.now() - start_time).total_seconds()
            result["source"] = "cache"
            result["tokens_used"] = 0
            self.stats["cache_hits"] += 1
            logger.info("✅ Resultado do CACHE - 0 tokens")
            return result

        # 2. SEGUNDO: Tentar consulta direta
        result = self._try_direct_query(user_query)
        if result and result.get("type") != "not_implemented":
            # Salvar no cache para próximas consultas
            query_type, params = self.direct_engine.classify_intent_direct(user_query)
            estimated_tokens = self._estimate_tokens_for_query(user_query)
            self.cache.set(query_type, params, result, tokens_would_use=estimated_tokens)

            result["processing_time"] = (datetime.now() - start_time).total_seconds()
            result["source"] = "direct"
            result["tokens_used"] = 0
            result["tokens_saved"] = estimated_tokens
            self.stats["direct_queries"] += 1
            self.stats["total_tokens_saved"] += estimated_tokens
            logger.info(f"✅ Consulta DIRETA - {estimated_tokens} tokens economizados")
            return result

        # 3. TERCEIRO: Fallback para LLM (apenas se habilitado e necessário)
        if not force_direct and self.enable_llm_fallback and self.llm_adapter:
            if self._should_use_llm_fallback(user_query):
                result = self._try_llm_query(user_query)
                if result:
                    result["processing_time"] = (datetime.now() - start_time).total_seconds()
                    result["source"] = "llm"
                    self.stats["llm_queries"] += 1
                    logger.info(f"⚠️ Usado LLM fallback - {result.get('tokens_used', 0)} tokens")
                    return result

        # 4. ÚLTIMO RECURSO: Resposta de fallback
        logger.warning(f"Nenhuma estratégia funcionou para: '{user_query}'")
        return self._create_fallback_response(user_query, start_time)

    def _try_cache(self, user_query: str) -> Optional[Dict[str, Any]]:
        """Tenta obter resultado do cache."""
        try:
            query_type, params = self.direct_engine.classify_intent_direct(user_query)
            return self.cache.get(query_type, params)
        except Exception as e:
            logger.debug(f"Cache lookup falhou: {e}")
            return None

    def _try_direct_query(self, user_query: str) -> Optional[Dict[str, Any]]:
        """Tenta executar consulta direta."""
        try:
            return self.direct_engine.process_query(user_query)
        except Exception as e:
            logger.warning(f"Consulta direta falhou: {e}")
            return None

    def _should_use_llm_fallback(self, user_query: str) -> bool:
        """Determina se deve usar LLM como fallback."""
        if not self.enable_llm_fallback:
            return False

        # Verificar limite diário
        if self._get_daily_token_usage() >= self.llm_fallback_config["daily_token_limit"]:
            logger.warning("Limite diário de tokens atingido - negando LLM")
            return False

        # Verificar complexidade da query
        complexity_indicators = [
            "análise", "analise", "tendência", "tendencia", "previsão", "previsao",
            "correlação", "correlacao", "comparativo complexo", "detalhado",
            "personalizado", "específico", "especifico", "customizado"
        ]

        is_complex = any(indicator in user_query.lower() for indicator in complexity_indicators)

        if is_complex and self.llm_fallback_config["enable_complex_queries"]:
            logger.info("Query complexa detectada - permitindo LLM")
            return True

        # Verificar se é uma pergunta muito específica que requer interpretação
        question_patterns = [
            r"por que\s+.*",
            r"como\s+.*",
            r"quando\s+.*",
            r"onde\s+.*",
            r"qual.*motivo.*",
            r"explique.*",
            r"detalhe.*"
        ]

        for pattern in question_patterns:
            if re.search(pattern, user_query.lower()):
                logger.info("Pergunta interpretativa detectada - permitindo LLM")
                return True

        return False

    def _try_llm_query(self, user_query: str) -> Optional[Dict[str, Any]]:
        """Executa consulta usando LLM (último recurso)."""
        if not self.llm_adapter:
            return None

        try:
            # Usar prompt otimizado para economia
            optimized_prompt = self._create_optimized_prompt(user_query)

            # Executar com limite de tokens
            response = self.llm_adapter.get_completion(
                messages=[{"role": "user", "content": optimized_prompt}],
                max_tokens=self.llm_fallback_config["max_tokens_per_query"],
                temperature=0.1  # Baixa criatividade para economia
            )

            tokens_used = response.get("usage", {}).get("total_tokens", 100)

            return {
                "type": "llm_response",
                "title": "Resposta via LLM (Fallback)",
                "result": {"response": response.get("content", "Sem resposta")},
                "summary": response.get("content", "Resposta gerada via LLM")[:200] + "...",
                "tokens_used": tokens_used,
                "method": "llm_fallback"
            }

        except Exception as e:
            logger.error(f"LLM fallback falhou: {e}")
            return None

    def _create_optimized_prompt(self, user_query: str) -> str:
        """Cria prompt otimizado para economia máxima de tokens."""
        # Prompt super conciso para economia
        return f"""Consulta: {user_query}

Dataset: vendas de produtos, filiais, segmentos.
Colunas: codigo, nome_produto, une_nome, nomesegmento, vendas mensais.

Responda de forma concisa e direta em português. Máximo 100 palavras."""

    def _estimate_tokens_for_query(self, user_query: str) -> int:
        """Estima quantos tokens essa consulta usaria na LLM."""
        # Estimativa baseada no comprimento e complexidade
        base_tokens = len(user_query.split()) * 2  # Aproximação
        prompt_tokens = 50  # Tokens do prompt
        response_tokens = 100  # Resposta média

        complexity_multiplier = 1.0

        if any(word in user_query.lower() for word in ["gráfico", "grafico", "análise", "analise"]):
            complexity_multiplier = 1.5

        return int((base_tokens + prompt_tokens + response_tokens) * complexity_multiplier)

    def _get_daily_token_usage(self) -> int:
        """Retorna uso de tokens do dia atual."""
        # Implementação simples - em produção, usaria banco de dados
        return self.stats.get("llm_tokens_today", 0)

    def _create_fallback_response(self, user_query: str, start_time: datetime) -> Dict[str, Any]:
        """Cria resposta de fallback quando nenhuma estratégia funciona."""
        suggestions = self.direct_engine.get_available_queries()[:5]

        return {
            "type": "fallback",
            "title": "Consulta Não Disponível",
            "result": {
                "message": "Esta consulta específica não está disponível no modo economia de LLM.",
                "suggestions": [q["keyword"] for q in suggestions]
            },
            "summary": "Consulta não implementada. Tente uma das sugestões disponíveis.",
            "tokens_used": 0,
            "processing_time": (datetime.now() - start_time).total_seconds(),
            "source": "fallback",
            "available_queries": suggestions
        }

    def get_economy_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas de economia de tokens."""
        total = self.stats["total_queries"]
        if total == 0:
            return {"message": "Nenhuma consulta processada ainda"}

        cache_rate = self.stats["cache_hits"] / total * 100
        direct_rate = self.stats["direct_queries"] / total * 100
        llm_rate = self.stats["llm_queries"] / total * 100

        return {
            "total_queries": total,
            "cache_hit_rate": round(cache_rate, 1),
            "direct_query_rate": round(direct_rate, 1),
            "llm_usage_rate": round(llm_rate, 1),
            "total_tokens_saved": self.stats["total_tokens_saved"],
            "average_tokens_saved_per_query": round(self.stats["total_tokens_saved"] / max(total, 1), 1),
            "economy_efficiency": round((cache_rate + direct_rate), 1)  # % de consultas sem LLM
        }

    def enable_llm_mode(self, enable: bool = True):
        """Habilita ou desabilita modo LLM."""
        self.enable_llm_fallback = enable
        logger.info(f"LLM fallback {'habilitado' if enable else 'desabilitado'}")

    def set_daily_token_limit(self, limit: int):
        """Define limite diário de tokens LLM."""
        self.llm_fallback_config["daily_token_limit"] = limit
        logger.info(f"Limite diário de tokens definido para: {limit}")

    def warm_up_cache(self):
        """Aquece cache com consultas populares."""
        popular_queries = [
            "produto mais vendido",
            "filial mais vendeu",
            "segmento mais vendeu",
            "produtos sem movimento",
            "estoque parado"
        ]

        logger.info("Aquecendo cache com consultas populares...")
        results = self.cache.warm_up_cache(popular_queries, self.parquet_adapter)
        logger.info(f"Cache aquecido: {results}")

        return results
