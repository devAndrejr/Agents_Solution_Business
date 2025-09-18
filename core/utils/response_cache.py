"""
Sistema de cache inteligente para respostas da OpenAI
Economiza créditos evitando chamadas repetidas
"""
import hashlib
import json
import os
import time
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class ResponseCache:
    """Cache inteligente para respostas da OpenAI"""

    def __init__(self, cache_dir: str = "data/cache", ttl_hours: int = 24):
        self.cache_dir = cache_dir
        self.ttl_seconds = ttl_hours * 3600
        os.makedirs(cache_dir, exist_ok=True)
        logger.info(f"Cache inicializado: {cache_dir}, TTL: {ttl_hours}h")

    def _generate_key(self, messages: list, model: str, temperature: float) -> str:
        """Gera chave única para a consulta"""
        # Criar hash baseado nos parâmetros da consulta
        query_data = {
            "messages": messages,
            "model": model,
            "temperature": temperature
        }
        query_str = json.dumps(query_data, sort_keys=True)
        return hashlib.md5(query_str.encode()).hexdigest()

    def get(self, messages: list, model: str, temperature: float) -> Optional[Dict[str, Any]]:
        """Recupera resposta do cache se disponível e válida"""
        cache_key = self._generate_key(messages, model, temperature)
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.json")

        try:
            if not os.path.exists(cache_file):
                return None

            with open(cache_file, 'r', encoding='utf-8') as f:
                cached_data = json.load(f)

            # Verificar se ainda está válido (TTL)
            cache_time = cached_data.get('timestamp', 0)
            if time.time() - cache_time > self.ttl_seconds:
                os.remove(cache_file)  # Remove cache expirado
                logger.info(f"Cache expirado removido: {cache_key}")
                return None

            logger.info(f"✅ Cache HIT - Economia de tokens: {cache_key[:8]}")
            return cached_data.get('response')

        except Exception as e:
            logger.error(f"Erro ao ler cache: {e}")
            return None

    def set(self, messages: list, model: str, temperature: float, response: Dict[str, Any]):
        """Armazena resposta no cache"""
        cache_key = self._generate_key(messages, model, temperature)
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.json")

        try:
            cache_data = {
                'timestamp': time.time(),
                'response': response,
                'metadata': {
                    'model': model,
                    'temperature': temperature,
                    'query_hash': cache_key
                }
            }

            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)

            logger.info(f"💾 Resposta cacheada: {cache_key[:8]}")

        except Exception as e:
            logger.error(f"Erro ao salvar cache: {e}")

    def clear_expired(self):
        """Remove todos os caches expirados"""
        if not os.path.exists(self.cache_dir):
            return

        removed_count = 0
        for filename in os.listdir(self.cache_dir):
            if filename.endswith('.json'):
                cache_file = os.path.join(self.cache_dir, filename)
                try:
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        cached_data = json.load(f)

                    cache_time = cached_data.get('timestamp', 0)
                    if time.time() - cache_time > self.ttl_seconds:
                        os.remove(cache_file)
                        removed_count += 1

                except Exception:
                    # Remove arquivos corrompidos
                    os.remove(cache_file)
                    removed_count += 1

        if removed_count > 0:
            logger.info(f"🧹 Limpeza: {removed_count} caches expirados removidos")

    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do cache"""
        if not os.path.exists(self.cache_dir):
            return {"total_files": 0, "total_size_mb": 0}

        total_files = len([f for f in os.listdir(self.cache_dir) if f.endswith('.json')])
        total_size = sum(
            os.path.getsize(os.path.join(self.cache_dir, f))
            for f in os.listdir(self.cache_dir)
            if f.endswith('.json')
        )

        return {
            "total_files": total_files,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "ttl_hours": self.ttl_seconds / 3600
        }