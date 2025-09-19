import logging
from openai import OpenAI
from core.utils.response_cache import ResponseCache

logger = logging.getLogger(__name__)

class OpenAILLMAdapter:
    def __init__(self, api_key: str, enable_cache: bool = True):
        """
        Inicializa o cliente da OpenAI com a chave da API fornecida.
        """
        if not api_key:
            raise ValueError("A chave da API da OpenAI não foi fornecida.")
        self.client = OpenAI(api_key=api_key)

        # Inicializar cache para economizar créditos
        self.cache_enabled = enable_cache
        if enable_cache:
            self.cache = ResponseCache(ttl_hours=48)  # Cache válido por 48h
            self.cache.clear_expired()  # Limpar caches expirados
            logger.info("✅ Cache de respostas ativado - ECONOMIA DE CRÉDITOS")
        else:
            self.cache = None

        logger.info("Adaptador da OpenAI inicializado com sucesso.")

    def get_completion(self, messages, model="gpt-4o-mini", temperature=0, max_tokens=1024, json_mode=False):
        """
        Obtém uma conclusão do modelo da OpenAI com cache inteligente.
        """
        try:
            # Tentar recuperar do cache primeiro
            if self.cache_enabled and self.cache:
                cached_response = self.cache.get(messages, model, temperature)
                if cached_response:
                    return cached_response

            # Preparar parâmetros da API
            params = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            if json_mode:
                params["response_format"] = {"type": "json_object"}

            # Chamar API OpenAI
            logger.info(f"💰 Chamada API OpenAI: {model} - tokens: {max_tokens}")
            response = self.client.chat.completions.create(**params)

            content = response.choices[0].message.content
            result = {"content": content}

            # Salvar no cache para futuras consultas
            if self.cache_enabled and self.cache:
                self.cache.set(messages, model, temperature, result)

            return result

        except Exception as e:
            logger.error(f"Erro ao chamar a API da OpenAI: {e}", exc_info=True)
            return {"error": str(e)}

    def get_cache_stats(self):
        """Retorna estatísticas de economia do cache"""
        if not self.cache_enabled or not self.cache:
            return {"cache_enabled": False}

        stats = self.cache.get_stats()
        stats["cache_enabled"] = True
        return stats

    def clear_cache(self):
        """Limpa todo o cache (use com cuidado)"""
        if self.cache_enabled and self.cache:
            self.cache.clear_expired()
            logger.info("🧹 Cache limpo")
