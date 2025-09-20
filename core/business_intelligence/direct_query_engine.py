"""
Motor de Consultas Diretas - Zero LLM para Economia Máxima
Sistema que executa consultas pré-definidas sem usar tokens da LLM.
"""

import pandas as pd
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import re
from pathlib import Path
import traceback

from core.connectivity.parquet_adapter import ParquetAdapter
from core.visualization.advanced_charts import AdvancedChartGenerator
from core.utils.logger_config import (
    get_logger,
    log_query_attempt,
    log_performance_metric,
    log_critical_error
)

logger = get_logger('agent_bi.direct_query')

class DirectQueryEngine:
    """Motor de consultas diretas que NÃO usa LLM para economizar tokens."""

    def __init__(self, parquet_adapter: ParquetAdapter):
        """Inicializa o motor com o adapter do parquet."""
        self.parquet_adapter = parquet_adapter
        self.chart_generator = AdvancedChartGenerator()
        self.query_cache = {}
        self.templates = self._load_query_templates()
        self.keywords_map = self._build_keywords_map()

        # Cache de dados frequentes
        self._cached_data = {}
        self._cache_timestamp = None

        logger.info("DirectQueryEngine inicializado - ZERO LLM tokens usados")

    def _load_query_templates(self) -> Dict[str, Any]:
        """Carrega templates de consultas pré-definidas."""
        templates_path = Path("data/business_question_templates_expanded.json")

        if templates_path.exists():
            with open(templates_path, 'r', encoding='utf-8') as f:
                return json.load(f)

        # Fallback com templates essenciais hardcoded
        return {
            "essential_queries": {
                "produto_mais_vendido": {
                    "type": "ranking",
                    "data_source": "vendas_totais",
                    "group_by": "nome_produto",
                    "order": "desc",
                    "limit": 1
                },
                "filial_mais_vendeu": {
                    "type": "ranking",
                    "data_source": "vendas_totais",
                    "group_by": "une_nome",
                    "order": "desc",
                    "limit": 1
                },
                "segmento_campao": {
                    "type": "ranking",
                    "data_source": "vendas_totais",
                    "group_by": "nomesegmento",
                    "order": "desc",
                    "limit": 1
                }
            }
        }

    def _build_keywords_map(self) -> Dict[str, str]:
        """Mapeia palavras-chave para queries diretas - SEM LLM."""
        return {
            # Produtos
            "produto mais vendido": "produto_mais_vendido",
            "top produto": "produto_mais_vendido",
            "produto líder": "produto_mais_vendido",
            "produto campeão": "produto_mais_vendido",
            "produtos sem movimento": "produtos_sem_vendas",
            "produtos parados": "produtos_sem_vendas",
            "produtos sem vendas": "produtos_sem_vendas",

            # Filiais
            "filial mais vendeu": "filial_mais_vendeu",
            "filial líder": "filial_mais_vendeu",
            "top filial": "filial_mais_vendeu",
            "une mais vendeu": "filial_mais_vendeu",
            "ranking filiais": "ranking_filiais",
            "ranking unes": "ranking_filiais",

            # Segmentos
            "segmento mais vendeu": "segmento_campao",
            "segmento líder": "segmento_campao",
            "top segmento": "segmento_campao",
            "segmento campeão": "segmento_campao",
            "ranking segmentos": "ranking_segmentos",

            # Top produtos por segmento
            "top 10 produtos": "top_produtos_por_segmento",
            "10 produtos mais vendidos": "top_produtos_por_segmento",
            "produtos mais vendidos segmento": "top_produtos_por_segmento",
            "top produtos segmento": "top_produtos_por_segmento",
            "produtos por segmento": "top_produtos_por_segmento",

            # Estoque
            "estoque parado": "estoque_parado",
            "produtos estoque parado": "estoque_parado",
            "estoque sem giro": "estoque_parado",
            "produtos reposição": "produtos_reposicao",
            "estoque baixo": "produtos_reposicao",

            # Financeiro
            "faturamento": "faturamento_mensal",
            "faturamento mês": "faturamento_mensal",
            "receita": "faturamento_mensal",

            # Temporais
            "evolução vendas": "evolucao_vendas_mensais",
            "vendas mensais": "evolucao_vendas_mensais",
            "comparação mensal": "comparacao_mensal",
            "variação mensal": "variacao_mensal"
        }

    def _get_cached_base_data(self, full_dataset: bool = False) -> pd.DataFrame:
        """Obtém dados base do cache ou carrega se necessário.

        Args:
            full_dataset: Se True, carrega dataset completo. Se False, carrega amostra (500 registros).
        """
        cache_key = "full_data" if full_dataset else "base_data"
        current_time = datetime.now()

        # Cache por 5 minutos
        if (self._cache_timestamp is None or
            (current_time - self._cache_timestamp).seconds > 300 or
            cache_key not in self._cached_data):

            if full_dataset:
                logger.info("Carregando dataset COMPLETO - necessário para consulta específica")
            else:
                logger.info("Carregando dados base - cache expirado")

            self.parquet_adapter.connect()

            if full_dataset:
                # Para dataset completo, carregar diretamente do parquet
                self.parquet_adapter._load_dataframe()
                if self.parquet_adapter._dataframe is not None:
                    df = self.parquet_adapter._dataframe.copy()
                    logger.info(f"Dataset completo carregado: {len(df)} registros")
                else:
                    logger.error("Falha ao carregar dataset completo")
                    return pd.DataFrame()
            else:
                # Carregar apenas amostra para economizar memória
                base_data = self.parquet_adapter.execute_query({})

                if base_data and len(base_data) > 0:
                    df = pd.DataFrame(base_data)
                    logger.info(f"Amostra carregada: {len(df)} registros")
                else:
                    logger.error("Falha ao carregar dados base")
                    return pd.DataFrame()

            # Garantir que vendas_total existe
            vendas_cols = [col for col in df.columns if col.startswith('mes_') and col[4:].isdigit()]
            if vendas_cols and 'vendas_total' not in df.columns:
                df['vendas_total'] = df[vendas_cols].sum(axis=1)
                logger.info("Coluna vendas_total criada no dataset")

            self._cached_data[cache_key] = df
            self._cache_timestamp = current_time
            logger.info(f"Cache atualizado: {len(df)} registros")

        return self._cached_data[cache_key]

    def classify_intent_direct(self, user_query: str) -> Tuple[str, Dict[str, Any]]:
        """Classifica intenção SEM usar LLM - apenas keywords."""
        start_time = datetime.now()
        logger.info(f"CLASSIFICANDO INTENT: '{user_query}'")

        try:
            query_lower = user_query.lower()

            # ALTA PRIORIDADE: Detectar consultas de PREÇO de produto em UNE específica
            preco_produto_une_match = re.search(r'(pre[çc]o|valor|custo).*produto\s*(\d{5,7}).*une\s*([A-Za-z0-9]+)', query_lower)
            if preco_produto_une_match:
                produto_codigo = preco_produto_une_match.group(2)
                une_nome = preco_produto_une_match.group(3).upper()
                result = ("preco_produto_une_especifica", {"produto_codigo": produto_codigo, "une_nome": une_nome})
                logger.info(f"CLASSIFICADO COMO: preco_produto_une_especifica (produto: {produto_codigo}, une: {une_nome})")
                return result

            # ALTA PRIORIDADE: Detectar consultas de TOP PRODUTOS em UNE específica
            top_produtos_une_match = re.search(r'(\d+)\s*produtos\s*mais\s*vendidos.*une\s*([A-Za-z0-9]+)', query_lower)
            if top_produtos_une_match:
                limite = int(top_produtos_une_match.group(1))
                une_nome = top_produtos_une_match.group(2).upper()
                result = ("top_produtos_une_especifica", {"limite": limite, "une_nome": une_nome})
                logger.info(f"CLASSIFICADO COMO: top_produtos_une_especifica (limite: {limite}, une: {une_nome})")
                return result

            # ALTA PRIORIDADE: Detectar consultas de VENDAS DE UNE em MÊS específico
            vendas_une_mes_match = re.search(r'vendas.*une\s*([A-Za-z0-9]+).*em\s*(janeiro|fevereiro|março|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro|jan|fev|mar|abr|mai|jun|jul|ago|set|out|nov|dez)', query_lower)
            if vendas_une_mes_match:
                une_nome = vendas_une_mes_match.group(1).upper()
                mes_nome = vendas_une_mes_match.group(2).lower()
                result = ("vendas_une_mes_especifico", {"une_nome": une_nome, "mes_nome": mes_nome})
                logger.info(f"CLASSIFICADO COMO: vendas_une_mes_especifico (une: {une_nome}, mes: {mes_nome})")
                return result

            # ALTA PRIORIDADE: Detectar consultas de VENDAS TOTAIS DE CADA UNE
            vendas_todas_unes_match = re.search(r'vendas\s*(totais|total).*(cada\s*une|todas\s*unes|por\s*une)', query_lower)
            if vendas_todas_unes_match:
                result = ("ranking_vendas_unes", {})
                logger.info(f"CLASSIFICADO COMO: ranking_vendas_unes")
                return result

            # ALTA PRIORIDADE: Detectar consultas de PRODUTO MAIS VENDIDO EM CADA UNE
            produto_cada_une_match = re.search(r'produto\s*mais\s*vendido.*(cada\s*une|em\s*cada\s*une|por\s*une)', query_lower)
            if produto_cada_une_match:
                result = ("produto_mais_vendido_cada_une", {})
                logger.info(f"CLASSIFICADO COMO: produto_mais_vendido_cada_une")
                return result

            # ALTA PRIORIDADE: Detectar consultas de PRODUTO MAIS VENDIDO EM TODAS AS UNES
            produto_todas_unes_match = re.search(r'produto\s*mais\s*vendido.*(todas?\s*unes?|todas?\s*as\s*unes?|em\s*todas?\s*unes?)', query_lower)
            if produto_todas_unes_match:
                result = ("produto_mais_vendido_cada_une", {})  # Usar o mesmo método
                logger.info(f"CLASSIFICADO COMO: produto_mais_vendido_cada_une (todas as UNEs)")
                return result

            # CORREÇÃO: Detectar GRÁFICO DE BARRAS para produto em TODAS AS UNEs (MAIOR PRIORIDADE)
            product_all_unes_match = re.search(r'(gr[áa]fico.*barras?|barras?).*produto\s*(\d{5,7}).*(todas.*unes?|todas.*filiais?)', query_lower)
            if product_all_unes_match:
                produto_codigo = product_all_unes_match.group(2)
                result = ("produto_vendas_todas_unes", {"produto_codigo": produto_codigo})
                logger.info(f"CLASSIFICADO COMO: produto_vendas_todas_unes (produto: {produto_codigo})")
                return result

            # Detectar GRÁFICO DE BARRAS para produto específico com UNE específica
            product_bar_une_match = re.search(r'(gr[áa]fico.*barras?|barras?).*produto\s*(\d{5,7}).*une\s*(\d+)', query_lower)
            if product_bar_une_match:
                produto_codigo = product_bar_une_match.group(2)
                une_codigo = product_bar_une_match.group(3)
                result = ("produto_vendas_une_barras", {"produto_codigo": produto_codigo, "une_codigo": une_codigo})
                logger.info(f"CLASSIFICADO COMO: produto_vendas_une_barras (produto: {produto_codigo}, une: {une_codigo})")
                return result

            # Detectar EVOLUÇÃO DE VENDAS para um produto específico
            product_evo_match = re.search(r'(gr[áa]fico|evolu[çc][ãa]o|hist[óo]rico|vendas\s+do\s+produto)\s.*?(\b\d{5,7}\b)', query_lower)
            if product_evo_match:
                produto_codigo = product_evo_match.group(2)
                result = ("evolucao_vendas_produto", {"produto_codigo": produto_codigo})
                logger.info(f"CLASSIFICADO COMO: evolucao_vendas_produto (código: {produto_codigo})")
                return result

            # Detectar top produtos por segmento com nome do segmento
            segmento_match = re.search(r'(top\s+\d+\s+produtos|produtos\s+mais\s+vendidos).*(segmento\s+(\w+)|(\w+)\s+segmento)', query_lower)
            if segmento_match:
                segmento_nome = segmento_match.group(3) or segmento_match.group(4)
                result = ("top_produtos_por_segmento", {"segmento": segmento_nome, "limit": 10})
                logger.info(f"CLASSIFICADO COMO: top_produtos_por_segmento (segmento: {segmento_nome})")
                return result

            # Buscar correspondência direta por keywords
            for keywords, query_type in self.keywords_map.items():
                if keywords in query_lower:
                    # Se for top produtos e não tem segmento específico, assumir que quer de todos
                    if query_type == "top_produtos_por_segmento" and "segmento" not in query_lower:
                        result = (query_type, {"segmento": "todos", "limit": 10})
                        logger.info(f"CLASSIFICADO COMO: {query_type} (todos os segmentos)")
                        return result

                    result = (query_type, {"matched_keywords": keywords})
                    logger.info(f"CLASSIFICADO COMO: {query_type} (keyword: {keywords})")
                    return result

            # Detectar números de produtos (agora com menor prioridade)
            product_match = re.search(r'\b\d{5,7}\b', user_query)
            if product_match:
                produto_codigo = product_match.group()
                result = ("consulta_produto_especifico", {"produto_codigo": produto_codigo})
                logger.info(f"CLASSIFICADO COMO: consulta_produto_especifico (código: {produto_codigo})")
                return result

            # Detectar nomes de UNE
            une_match = re.search(r'\bune\s+(\w+)\b|\b(\w+)\s+une\b', query_lower)
            if une_match:
                une_name = une_match.group(1) or une_match.group(2)
                result = ("consulta_une_especifica", {"une_nome": une_name.upper()})
                logger.info(f"CLASSIFICADO COMO: consulta_une_especifica (UNE: {une_name})")
                return result

            # Default para análise geral
            result = ("analise_geral", {"tipo": "geral"})
            logger.warning(f"CLASSIFICADO COMO PADRÃO: analise_geral")
            return result

        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            log_critical_error(e, "classify_intent_direct", {"user_query": user_query})
            logger.error(f"ERRO NA CLASSIFICAÇÃO: {e}")
            return "analise_geral", {"tipo": "geral", "error": str(e)}

        finally:
            duration = (datetime.now() - start_time).total_seconds()
            log_performance_metric("classify_intent", duration, {"query_length": len(user_query)})

    def execute_direct_query(self, query_type: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Executa consulta direta SEM usar LLM."""
        start_time = datetime.now()
        logger.info(f"EXECUTANDO CONSULTA: {query_type} | Params: {params}")

        try:
            # 🔧 FIX CRÍTICO: Para consultas específicas de produtos, carregar dataset completo
            full_dataset_queries = ["consulta_produto_especifico", "consulta_une_especifica", "evolucao_vendas_produto", "produto_vendas_une_barras", "produto_vendas_todas_unes", "preco_produto_une_especifica", "top_produtos_une_especifica", "vendas_une_mes_especifico", "ranking_vendas_unes", "produto_mais_vendido_cada_une"]
            use_full_dataset = query_type in full_dataset_queries

            if use_full_dataset:
                logger.info("⚡ CONSULTA ESPECÍFICA DETECTADA - Carregando dataset COMPLETO")

            df = self._get_cached_base_data(full_dataset=use_full_dataset)

            if df.empty:
                error_msg = "Dados não disponíveis"
                logger.error(f"ERRO - DADOS VAZIOS: {error_msg}")
                log_query_attempt(f"{query_type}", query_type, params, False, error_msg)
                return {"error": error_msg, "type": "error"}

            logger.info(f"DADOS CARREGADOS: {len(df)} registros, {list(df.columns)}")

            # Dispatch para método específico
            method_name = f"_query_{query_type}"
            if hasattr(self, method_name):
                logger.info(f"EXECUTANDO MÉTODO: {method_name}")
                method = getattr(self, method_name)
                result = method(df, params)
            else:
                logger.warning(f"MÉTODO NÃO ENCONTRADO: {method_name} - usando fallback")
                result = self._query_fallback(df, query_type, params)

            # Log do resultado
            success = result.get("type") != "error"
            error_msg = result.get("error") if not success else None

            log_query_attempt(f"{query_type}", query_type, params, success, error_msg)

            if success:
                logger.info(f"CONSULTA SUCESSO: {query_type} - {result.get('title', 'N/A')}")
            else:
                logger.error(f"CONSULTA FALHOU: {query_type} - {error_msg}")

            return result

        except Exception as e:
            error_msg = str(e)
            log_critical_error(e, "execute_direct_query", {"query_type": query_type, "params": params})
            log_query_attempt(f"{query_type}", query_type, params, False, error_msg)
            logger.error(f"ERRO CRÍTICO NA EXECUÇÃO: {query_type} - {error_msg}")
            logger.error(f"TRACEBACK: {traceback.format_exc()}")
            return {"error": error_msg, "type": "error"}

        finally:
            duration = (datetime.now() - start_time).total_seconds()
            log_performance_metric("execute_direct_query", duration, {
                "query_type": query_type,
                "params_count": len(params),
                "data_rows": len(df) if 'df' in locals() and not df.empty else 0
            })

    def _query_produto_mais_vendido(self, df: pd.DataFrame, params: Dict[str, Any]) -> Dict[str, Any]:
        """Query: Produto mais vendido."""
        if 'vendas_total' not in df.columns:
            return {"error": "Dados de vendas não disponíveis", "type": "error"}

        top_produto = df.nlargest(1, 'vendas_total')

        if top_produto.empty:
            return {"error": "Nenhum produto encontrado", "type": "error"}

        produto = top_produto.iloc[0]

        # Gerar gráfico
        top_10 = df.nlargest(10, 'vendas_total')
        chart = self.chart_generator.create_product_ranking_chart(
            top_10[['nome_produto', 'vendas_total']],
            limit=10,
            chart_type='horizontal_bar'
        )

        return {
            "type": "produto_ranking",
            "title": "Produto Mais Vendido",
            "result": {
                "produto": produto['nome_produto'],
                "vendas": float(produto['vendas_total']),
                "codigo": produto.get('codigo', 'N/A')
            },
            "chart": chart,
            "summary": f"O produto mais vendido é '{produto['nome_produto']}' com {produto['vendas_total']:,.0f} vendas.",
            "tokens_used": 0  # ZERO tokens LLM
        }

    def _query_filial_mais_vendeu(self, df: pd.DataFrame, params: Dict[str, Any]) -> Dict[str, Any]:
        """Query: Filial que mais vendeu."""
        if 'vendas_total' not in df.columns or 'une_nome' not in df.columns:
            return {"error": "Dados de filiais/vendas não disponíveis", "type": "error"}

        vendas_por_filial = df.groupby('une_nome')['vendas_total'].sum().reset_index()
        vendas_por_filial = vendas_por_filial.sort_values('vendas_total', ascending=False)

        top_filial = vendas_por_filial.iloc[0]

        # Gerar gráfico
        chart = self.chart_generator.create_filial_performance_chart(
            vendas_por_filial.head(10),
            chart_type='bar'
        )

        return {
            "type": "filial_ranking",
            "title": "Filial que Mais Vendeu",
            "result": {
                "filial": top_filial['une_nome'],
                "vendas": float(top_filial['vendas_total'])
            },
            "chart": chart,
            "summary": f"A filial que mais vendeu é '{top_filial['une_nome']}' com {top_filial['vendas_total']:,.0f} vendas.",
            "tokens_used": 0
        }

    def _query_segmento_campao(self, df: pd.DataFrame, params: Dict[str, Any]) -> Dict[str, Any]:
        """Query: Segmento campeão."""
        if 'vendas_total' not in df.columns or 'nomesegmento' not in df.columns:
            return {"error": "Dados de segmentos não disponíveis", "type": "error"}

        vendas_por_segmento = df.groupby('nomesegmento')['vendas_total'].sum().reset_index()
        vendas_por_segmento = vendas_por_segmento.sort_values('vendas_total', ascending=False)

        top_segmento = vendas_por_segmento.iloc[0]

        # Gerar gráfico
        chart = self.chart_generator.create_segmentation_chart(
            df, 'nomesegmento', 'vendas_total', chart_type='pie'
        )

        return {
            "type": "segmento_ranking",
            "title": "Segmento Campeão",
            "result": {
                "segmento": top_segmento['nomesegmento'],
                "vendas": float(top_segmento['vendas_total'])
            },
            "chart": chart,
            "summary": f"O segmento campeão é '{top_segmento['nomesegmento']}' com {top_segmento['vendas_total']:,.0f} vendas.",
            "tokens_used": 0
        }

    def _query_produtos_sem_vendas(self, df: pd.DataFrame, params: Dict[str, Any]) -> Dict[str, Any]:
        """Query: Produtos sem movimento."""
        if 'vendas_total' not in df.columns:
            return {"error": "Dados de vendas não disponíveis", "type": "error"}

        produtos_sem_vendas = df[df['vendas_total'] == 0]
        count_sem_vendas = len(produtos_sem_vendas)

        # Top 10 produtos sem vendas com maior estoque
        if 'estoque_atual' in df.columns:
            top_sem_vendas = produtos_sem_vendas[produtos_sem_vendas['estoque_atual'] > 0].nlargest(10, 'estoque_atual')
        else:
            top_sem_vendas = produtos_sem_vendas.head(10)

        return {
            "type": "produtos_sem_movimento",
            "title": "Produtos Sem Movimento",
            "result": {
                "total_produtos": count_sem_vendas,
                "percentual": round(count_sem_vendas / len(df) * 100, 1),
                "produtos_exemplo": top_sem_vendas[['nome_produto']].head(5).to_dict('records') if not top_sem_vendas.empty else []
            },
            "summary": f"Encontrados {count_sem_vendas} produtos sem movimento ({count_sem_vendas/len(df)*100:.1f}% do total).",
            "tokens_used": 0
        }

    def _query_estoque_parado(self, df: pd.DataFrame, params: Dict[str, Any]) -> Dict[str, Any]:
        """Query: Estoque parado."""
        if 'vendas_total' not in df.columns or 'estoque_atual' not in df.columns:
            return {"error": "Dados de estoque não disponíveis", "type": "error"}

        estoque_parado = df[(df['vendas_total'] == 0) & (df['estoque_atual'] > 0)]
        total_estoque_parado = estoque_parado['estoque_atual'].sum()
        count_produtos = len(estoque_parado)

        return {
            "type": "estoque_parado",
            "title": "Estoque Parado",
            "result": {
                "produtos_parados": count_produtos,
                "quantidade_total": float(total_estoque_parado),
                "valor_estimado": float(total_estoque_parado * df['preco_38_percent'].mean()) if 'preco_38_percent' in df.columns else None
            },
            "summary": f"Identificados {count_produtos} produtos com estoque parado totalizando {total_estoque_parado:,.0f} unidades.",
            "tokens_used": 0
        }

    def _query_consulta_produto_especifico(self, df: pd.DataFrame, params: Dict[str, Any]) -> Dict[str, Any]:
        """Query: Consulta produto específico por código."""
        produto_codigo = params.get('produto_codigo')

        try:
            produto_codigo = int(produto_codigo)
        except (ValueError, TypeError):
            return {"error": f"Código de produto inválido: {produto_codigo}", "type": "error"}

        produto_data = df[df['codigo'] == produto_codigo]

        if produto_data.empty:
            return {"error": f"Produto {produto_codigo} não encontrado", "type": "error"}

        # Se há múltiplas UNEs, agregar
        if len(produto_data) > 1:
            produto_info = {
                "codigo": produto_codigo,
                "nome": produto_data.iloc[0]['nome_produto'],
                "vendas_total": float(produto_data['vendas_total'].sum()),
                "unes": len(produto_data),
                "preco": float(produto_data.iloc[0].get('preco_38_percent', 0))
            }
        else:
            produto = produto_data.iloc[0]
            produto_info = {
                "codigo": produto_codigo,
                "nome": produto['nome_produto'],
                "vendas_total": float(produto['vendas_total']),
                "une": produto.get('une_nome', 'N/A'),
                "preco": float(produto.get('preco_38_percent', 0))
            }

        return {
            "type": "produto_especifico",
            "title": f"Produto {produto_codigo}",
            "result": produto_info,
            "summary": f"Produto '{produto_info['nome']}' - Vendas: {produto_info['vendas_total']:,.0f} - Preço: R$ {produto_info['preco']:.2f}",
            "tokens_used": 0
        }

    def _query_preco_produto_une_especifica(self, df: pd.DataFrame, params: Dict[str, Any]) -> Dict[str, Any]:
        """Query: Preço de produto específico em UNE específica."""
        produto_codigo = params.get('produto_codigo')
        une_nome = params.get('une_nome')

        try:
            produto_codigo = int(produto_codigo)
        except (ValueError, TypeError):
            return {"error": f"Código de produto inválido: {produto_codigo}", "type": "error"}

        # Verificar se produto existe na UNE específica
        produto_une_data = df[(df['codigo'] == produto_codigo) & (df['une_nome'] == une_nome)]

        if produto_une_data.empty:
            # Verificar se produto existe em outras UNEs
            produto_geral = df[df['codigo'] == produto_codigo]
            if produto_geral.empty:
                return {"error": f"Produto {produto_codigo} não encontrado no sistema", "type": "error"}
            else:
                unes_disponiveis = produto_geral['une_nome'].unique()
                return {
                    "error": f"Produto {produto_codigo} não encontrado na UNE {une_nome}",
                    "type": "error",
                    "suggestion": f"Produto disponível nas UNEs: {', '.join(unes_disponiveis)}"
                }

        produto = produto_une_data.iloc[0]
        preco = float(produto.get('preco_38_percent', 0))

        # Calcular vendas se disponível
        vendas_meses = [f'mes_{i:02d}' for i in range(1, 13)]
        available_vendas = [col for col in vendas_meses if col in df.columns]
        vendas_total = 0
        if available_vendas:
            vendas_total = float(produto[available_vendas].sum())

        produto_info = {
            "codigo": produto_codigo,
            "nome": produto['nome_produto'],
            "une_codigo": produto['une'],
            "une_nome": produto['une_nome'],
            "preco": preco,
            "vendas_total": vendas_total,
            "estoque": float(produto.get('estoque_atual', 0)) if 'estoque_atual' in produto else None
        }

        return {
            "type": "preco_produto_une",
            "title": f"Preço do Produto {produto_codigo} na UNE {une_nome}",
            "result": produto_info,
            "summary": f"Produto '{produto_info['nome']}' na UNE {une_nome}: R$ {preco:.2f}",
            "tokens_used": 0
        }

    def _query_top_produtos_une_especifica(self, df: pd.DataFrame, params: Dict[str, Any]) -> Dict[str, Any]:
        """Query: Top N produtos mais vendidos em UNE específica."""
        limite = params.get('limite', 10)
        une_nome = params.get('une_nome')

        if 'vendas_total' not in df.columns:
            return {"error": "Dados de vendas não disponíveis", "type": "error"}

        # Verificar se UNE existe
        une_data = df[df['une_nome'] == une_nome]
        if une_data.empty:
            unes_disponiveis = df['une_nome'].unique()
            return {
                "error": f"UNE {une_nome} não encontrada",
                "type": "error",
                "suggestion": f"UNEs disponíveis: {', '.join(unes_disponiveis[:10])}"
            }

        # Filtrar apenas produtos da UNE específica com vendas > 0
        produtos_une = une_data[une_data['vendas_total'] > 0].copy()

        if produtos_une.empty:
            return {
                "error": f"Nenhum produto com vendas encontrado na UNE {une_nome}",
                "type": "error"
            }

        # Agrupar apenas por código (mais eficiente) e somar vendas
        produtos_agrupados = produtos_une.groupby('codigo').agg({
            'vendas_total': 'sum',
            'nome_produto': 'first',
            'preco_38_percent': 'first',
            'nomesegmento': 'first'
        }).reset_index()

        # Ordenar por vendas e pegar o top N
        top_produtos = produtos_agrupados.nlargest(limite, 'vendas_total')

        # Preparar dados para gráfico
        x_data = [produto['nome_produto'][:50] + '...' if len(produto['nome_produto']) > 50 else produto['nome_produto']
                  for _, produto in top_produtos.iterrows()]
        y_data = [float(produto['vendas_total']) for _, produto in top_produtos.iterrows()]

        # Cores baseadas na performance
        max_vendas = max(y_data) if y_data else 1
        colors = []
        for valor in y_data:
            if valor >= max_vendas * 0.7:
                colors.append('#2E8B57')  # Verde escuro para top performers
            elif valor >= max_vendas * 0.3:
                colors.append('#FFD700')  # Dourado para performance média
            else:
                colors.append('#CD5C5C')  # Vermelho suave para baixa performance

        # Criar dados do gráfico
        chart_data = {
            "x": x_data,
            "y": y_data,
            "type": "bar",
            "colors": colors,
            "show_values": True,
            "height": max(400, min(800, len(x_data) * 50)),
            "margin": {"l": 80, "r": 80, "t": 100, "b": 120}
        }

        # Preparar lista de produtos para resultado
        produtos_list = []
        for _, produto in top_produtos.iterrows():
            produtos_list.append({
                "codigo": int(produto['codigo']),
                "nome": produto['nome_produto'],
                "vendas": float(produto['vendas_total']),
                "preco": float(produto.get('preco_38_percent', 0)),
                "segmento": produto.get('nomesegmento', 'N/A')
            })

        total_vendas = sum(y_data)

        return {
            "type": "chart",
            "title": f"Top {limite} Produtos Mais Vendidos - UNE {une_nome}",
            "result": {
                "chart_data": chart_data,
                "une_nome": une_nome,
                "limite": limite,
                "produtos": produtos_list,
                "total_vendas": total_vendas,
                "total_produtos_une": len(produtos_une)
            },
            "summary": f"Top {limite} produtos mais vendidos na UNE {une_nome}. Total de vendas: {total_vendas:,.0f} unidades.",
            "tokens_used": 0
        }

    def _query_vendas_une_mes_especifico(self, df: pd.DataFrame, params: Dict[str, Any]) -> Dict[str, Any]:
        """Query: Vendas de UNE específica em mês específico."""
        une_nome = params.get('une_nome')
        mes_nome = params.get('mes_nome', '').lower()

        # Mapear nome do mês para coluna
        meses_map = {
            'janeiro': 'mes_01', 'jan': 'mes_01',
            'fevereiro': 'mes_02', 'fev': 'mes_02',
            'março': 'mes_03', 'mar': 'mes_03',
            'abril': 'mes_04', 'abr': 'mes_04',
            'maio': 'mes_05', 'mai': 'mes_05',
            'junho': 'mes_06', 'jun': 'mes_06',
            'julho': 'mes_07', 'jul': 'mes_07',
            'agosto': 'mes_08', 'ago': 'mes_08',
            'setembro': 'mes_09', 'set': 'mes_09',
            'outubro': 'mes_10', 'out': 'mes_10',
            'novembro': 'mes_11', 'nov': 'mes_11',
            'dezembro': 'mes_12', 'dez': 'mes_12'
        }

        coluna_mes = meses_map.get(mes_nome)
        if not coluna_mes:
            return {"error": f"Mês '{mes_nome}' não reconhecido", "type": "error"}

        # Verificar se UNE existe
        une_data = df[df['une_nome'] == une_nome]
        if une_data.empty:
            unes_disponiveis = df['une_nome'].unique()
            return {
                "error": f"UNE {une_nome} não encontrada",
                "type": "error",
                "suggestion": f"UNEs disponíveis: {', '.join(unes_disponiveis[:10])}"
            }

        # Calcular total de vendas da UNE no mês específico
        if coluna_mes not in df.columns:
            return {"error": f"Dados de vendas para {mes_nome} não disponíveis", "type": "error"}

        total_vendas_mes = float(une_data[coluna_mes].sum())
        total_produtos = len(une_data[une_data[coluna_mes] > 0])

        return {
            "type": "vendas_une_mes",
            "title": f"Vendas da UNE {une_nome} em {mes_nome.title()}",
            "result": {
                "une_nome": une_nome,
                "mes_nome": mes_nome.title(),
                "total_vendas": total_vendas_mes,
                "total_produtos": total_produtos,
                "media_por_produto": total_vendas_mes / total_produtos if total_produtos > 0 else 0
            },
            "summary": f"UNE {une_nome} vendeu {total_vendas_mes:,.0f} unidades em {mes_nome.title()}.",
            "tokens_used": 0
        }

    def _query_ranking_vendas_unes(self, df: pd.DataFrame, params: Dict[str, Any]) -> Dict[str, Any]:
        """Query: Ranking de vendas totais por UNE."""
        if 'vendas_total' not in df.columns:
            return {"error": "Dados de vendas não disponíveis", "type": "error"}

        # Agrupar por UNE e somar todas as vendas
        vendas_por_une = df.groupby(['une', 'une_nome']).agg({
            'vendas_total': 'sum'
        }).reset_index()

        # Ordenar por vendas totais (decrescente)
        vendas_por_une = vendas_por_une.sort_values('vendas_total', ascending=False)

        # Preparar dados para gráfico
        x_data = [f"{row['une_nome']}\n(UNE {row['une']})" for _, row in vendas_por_une.iterrows()]
        y_data = [float(row['vendas_total']) for _, row in vendas_por_une.iterrows()]

        # Cores baseadas na performance
        max_vendas = max(y_data) if y_data else 1
        colors = []
        for valor in y_data:
            if valor >= max_vendas * 0.7:
                colors.append('#2E8B57')  # Verde escuro para top performers
            elif valor >= max_vendas * 0.3:
                colors.append('#FFD700')  # Dourado para performance média
            else:
                colors.append('#CD5C5C')  # Vermelho suave para baixa performance

        # Criar dados do gráfico
        chart_data = {
            "x": x_data,
            "y": y_data,
            "type": "bar",
            "colors": colors,
            "show_values": True,
            "height": max(400, min(800, len(x_data) * 60)),
            "margin": {"l": 80, "r": 80, "t": 100, "b": 120}
        }

        total_vendas_geral = sum(y_data)

        return {
            "type": "chart",
            "title": "Ranking de Vendas por UNE",
            "result": {
                "chart_data": chart_data,
                "unes": len(vendas_por_une),
                "total_vendas": total_vendas_geral,
                "melhor_une": vendas_por_une.iloc[0]['une_nome'] if len(vendas_por_une) > 0 else None,
                "vendas_melhor": vendas_por_une.iloc[0]['vendas_total'] if len(vendas_por_une) > 0 else 0
            },
            "summary": f"Ranking de {len(vendas_por_une)} UNEs. Melhor: {vendas_por_une.iloc[0]['une_nome'] if len(vendas_por_une) > 0 else 'N/A'} com {vendas_por_une.iloc[0]['vendas_total'] if len(vendas_por_une) > 0 else 0:,.0f} vendas.",
            "tokens_used": 0
        }

    def _query_produto_mais_vendido_cada_une(self, df: pd.DataFrame, params: Dict[str, Any]) -> Dict[str, Any]:
        """Query: Produto mais vendido em cada UNE."""
        if 'vendas_total' not in df.columns or 'une_nome' not in df.columns:
            return {"error": "Dados de vendas/UNE não disponíveis", "type": "error"}

        # Encontrar o produto mais vendido por UNE
        produtos_por_une = []

        # Agrupar por UNE
        for une_nome in df['une_nome'].unique():
            une_data = df[df['une_nome'] == une_nome]

            # Encontrar produto mais vendido desta UNE
            produto_top = une_data.loc[une_data['vendas_total'].idxmax()]

            produtos_por_une.append({
                'une_nome': une_nome,
                'produto_codigo': produto_top['codigo'],
                'produto_nome': produto_top['nome_produto'],
                'vendas_total': produto_top['vendas_total']
            })

        # Ordenar por vendas (descendente)
        produtos_por_une.sort(key=lambda x: x['vendas_total'], reverse=True)

        # Preparar dados para gráfico com nome do produto
        x_data = [f"UNE {item['une_nome']}\n{item['produto_nome'][:30]}{'...' if len(item['produto_nome']) > 30 else ''}" for item in produtos_por_une]
        y_data = [float(item['vendas_total']) for item in produtos_por_une]

        # Cores baseadas na performance
        max_vendas = max(y_data) if y_data else 1
        colors = []
        for valor in y_data:
            if valor >= max_vendas * 0.7:
                colors.append('#2E8B57')  # Verde escuro para top performers
            elif valor >= max_vendas * 0.3:
                colors.append('#FFD700')  # Dourado para performance média
            else:
                colors.append('#CD5C5C')  # Vermelho suave para baixa performance

        # Criar dados do gráfico
        chart_data = {
            "x": x_data,
            "y": y_data,
            "type": "bar",
            "colors": colors,
            "show_values": True,
            "height": max(400, min(800, len(x_data) * 60)),
            "margin": {"l": 80, "r": 80, "t": 100, "b": 120}
        }

        return {
            "type": "chart",
            "title": "Produto Mais Vendido em Cada UNE",
            "result": {
                "chart_data": chart_data,
                "produtos_por_une": produtos_por_une,
                "total_unes": len(produtos_por_une),
                "melhor_produto_geral": produtos_por_une[0] if produtos_por_une else None
            },
            "summary": f"Produtos mais vendidos em {len(produtos_por_une)} UNEs. Líder geral: {produtos_por_une[0]['produto_nome'] if produtos_por_une else 'N/A'} na UNE {produtos_por_une[0]['une_nome'] if produtos_por_une else 'N/A'} com {produtos_por_une[0]['vendas_total'] if produtos_por_une else 0:,.0f} vendas.",
            "tokens_used": 0
        }

    def _query_top_produtos_por_segmento(self, df: pd.DataFrame, params: Dict[str, Any]) -> Dict[str, Any]:
        """Query: Top 10 produtos mais vendidos por segmento."""
        if 'vendas_total' not in df.columns or 'nomesegmento' not in df.columns:
            return {"error": "Dados de vendas/segmento não disponíveis", "type": "error"}

        segmento = params.get('segmento', 'todos')
        limit = params.get('limit', 10)

        # Filtrar por segmento se especificado
        if segmento.lower() != 'todos':
            # Buscar segmento (case insensitive)
            segmento_filter = df['nomesegmento'].str.lower().str.contains(segmento.lower(), na=False)
            if not segmento_filter.any():
                return {"error": f"Segmento '{segmento}' não encontrado", "type": "error"}

            df_filtered = df[segmento_filter]
            segmento_real = df_filtered['nomesegmento'].iloc[0]  # Nome real do segmento
        else:
            df_filtered = df
            segmento_real = "Todos os Segmentos"

        # Agrupar por produto e somar vendas
        produtos_vendas = df_filtered.groupby(['codigo', 'nome_produto', 'nomesegmento']).agg({
            'vendas_total': 'sum',
            'preco_38_percent': 'first'
        }).reset_index()

        # Pegar top N produtos
        top_produtos = produtos_vendas.nlargest(limit, 'vendas_total')

        if top_produtos.empty:
            return {"error": f"Nenhum produto encontrado no segmento '{segmento}'", "type": "error"}

        # Preparar resultado
        produtos_list = []
        for _, produto in top_produtos.iterrows():
            produtos_list.append({
                "codigo": int(produto['codigo']),
                "nome": produto['nome_produto'],
                "vendas": float(produto['vendas_total']),
                "segmento": produto['nomesegmento'],
                "preco": float(produto.get('preco_38_percent', 0))
            })

        # Criar gráfico se necessário
        chart = None
        if len(produtos_list) > 1:
            try:
                chart = self.chart_generator.create_top_produtos_chart(produtos_list, segmento_real)
            except Exception as e:
                logger.warning(f"Erro ao criar gráfico: {e}")

        return {
            "type": "top_produtos_segmento",
            "title": f"Top {limit} Produtos - {segmento_real}",
            "result": {
                "produtos": produtos_list,
                "segmento": segmento_real,
                "total_produtos": len(produtos_list),
                "vendas_total": sum(p['vendas'] for p in produtos_list)
            },
            "summary": f"Top {len(produtos_list)} produtos em '{segmento_real}'. Líder: {produtos_list[0]['nome']} ({produtos_list[0]['vendas']:,.0f} vendas)",
            "chart": chart,
            "tokens_used": 0
        }

    def _query_evolucao_vendas_produto(self, df: pd.DataFrame, params: Dict[str, Any]) -> Dict[str, Any]:
        """Query: Evolução de vendas para um produto específico."""
        produto_codigo = params.get('produto_codigo')
        try:
            produto_codigo = int(produto_codigo)
        except (ValueError, TypeError):
            return {"error": f"Código de produto inválido: {produto_codigo}", "type": "error"}

        produto_data = df[df['codigo'] == produto_codigo]
        if produto_data.empty:
            return {"error": f"Produto {produto_codigo} não encontrado", "type": "error"}

        produto_nome = produto_data.iloc[0]['nome_produto']

        # Regex para encontrar colunas de vendas mensais (ex: 'mai-23', 'jun/23', 'mes_01', 'jan-24')
        sales_cols_re = re.compile(r'^(?:[a-z]{3}[-/]\d{2,4}|mes_\d{1,2})$', re.IGNORECASE)
        sales_cols = [col for col in df.columns if sales_cols_re.match(col)]

        if not sales_cols:
            return {"error": "Nenhuma coluna de vendas mensais encontrada no formato esperado.", "type": "error"}

        # Mapear nomes de meses para números
        month_map = {
            'jan': 1, 'fev': 2, 'mar': 3, 'abr': 4, 'mai': 5, 'jun': 6,
            'jul': 7, 'ago': 8, 'set': 9, 'out': 10, 'nov': 11, 'dez': 12
        }

        sales_timeseries = []
        product_sales_series = produto_data[sales_cols].iloc[0]

        for col_name, sales_value in product_sales_series.items():
            try:
                clean_col = col_name.lower().replace('/', '-')
                
                if clean_col.startswith('mes_'):
                    # Processar colunas 'mes_xx' sem ano específico
                    mes_num = int(clean_col.split('_')[1])
                    sales_timeseries.append({
                        "date": datetime(2023, mes_num, 1),  # Ano padrão 2023
                        "mes": f"{mes_num:02d}/2023",
                        "vendas": float(sales_value) if pd.notna(sales_value) else 0
                    })
                    continue

                month_str, year_str = clean_col.split('-')
                month = month_map[month_str[:3]]
                year = int(year_str)
                if year < 100: # Formato '23' -> 2023
                    year += 2000
                
                sales_timeseries.append({
                    "date": datetime(year, month, 1),
                    "mes": f"{month:02d}/{year}",
                    "vendas": float(sales_value) if pd.notna(sales_value) else 0
                })
            except (ValueError, KeyError) as e:
                logger.warning(f"Não foi possível processar a coluna de data '{col_name}': {e}")
                continue
        
        if not sales_timeseries:
            return {"error": "Não foi possível extrair dados de série temporal de vendas para o produto.", "type": "error"}

        # Ordenar por data
        sales_timeseries.sort(key=lambda x: x['date'])

        total_vendas = sum(item['vendas'] for item in sales_timeseries)

        return {
            "type": "evolucao_vendas_produto",
            "title": f"Evolução de Vendas - {produto_nome} ({produto_codigo})",
            "result": {
                "produto_codigo": produto_codigo,
                "produto_nome": produto_nome,
                "vendas_timeseries": sales_timeseries,
                "total_vendas": total_vendas
            },
            "summary": f"O produto '{produto_nome}' teve um total de {total_vendas:,.0f} vendas no período analisado.",
            "tokens_used": 0
        }

    def _query_produto_vendas_une_barras(self, df: pd.DataFrame, params: Dict[str, Any]) -> Dict[str, Any]:
        """Query: Gráfico de barras para produto específico em UNE específica."""
        produto_codigo = params.get('produto_codigo')
        une_codigo = params.get('une_codigo')

        try:
            produto_codigo = int(produto_codigo)
            une_codigo = int(une_codigo)
        except (ValueError, TypeError):
            return {"error": f"Código de produto ou UNE inválido: {produto_codigo}, {une_codigo}", "type": "error"}

        # Verificar se produto existe
        produto_data = df[df['codigo'] == produto_codigo]
        if produto_data.empty:
            return {"error": f"Produto {produto_codigo} não encontrado", "type": "error"}

        # Verificar se UNE existe
        une_data = df[df['une'] == une_codigo]
        if une_data.empty:
            unes_disponiveis = sorted(df['une'].unique())
            return {
                "error": f"UNE {une_codigo} não encontrada. UNEs disponíveis: {unes_disponiveis[:10]}...",
                "type": "error"
            }

        # Verificar se produto existe na UNE específica
        produto_une_data = df[(df['codigo'] == produto_codigo) & (df['une'] == une_codigo)]
        if produto_une_data.empty:
            produto_unes = produto_data['une'].unique()
            return {
                "error": f"Produto {produto_codigo} não está disponível na UNE {une_codigo}. Está disponível nas UNEs: {list(produto_unes)}",
                "type": "error"
            }

        produto_nome = produto_data.iloc[0]['nome_produto']
        une_nome = produto_une_data.iloc[0].get('une_nome', f'UNE {une_codigo}')

        # Extrair vendas por mês
        vendas_meses = [f'mes_{i:02d}' for i in range(1, 13)]
        vendas_data = produto_une_data[vendas_meses].iloc[0]

        # Criar dados para gráfico de barras
        chart_data = {
            "x": [f"Mês {i:02d}" for i in range(1, 13)],
            "y": [float(vendas_data[col]) if pd.notna(vendas_data[col]) else 0 for col in vendas_meses],
            "type": "bar"
        }

        total_vendas = sum(chart_data["y"])

        return {
            "type": "chart",
            "title": f"Vendas Mensais - {produto_nome} na {une_nome}",
            "result": {
                "chart_data": chart_data,
                "produto_codigo": produto_codigo,
                "produto_nome": produto_nome,
                "une_codigo": une_codigo,
                "une_nome": une_nome,
                "total_vendas": total_vendas
            },
            "summary": f"Gráfico de barras gerado para {produto_nome} (código {produto_codigo}) na {une_nome}. Total de vendas: {total_vendas:,.0f} unidades.",
            "tokens_used": 0
        }

    def _query_produto_vendas_todas_unes(self, df: pd.DataFrame, params: Dict[str, Any]) -> Dict[str, Any]:
        """Query: Gráfico de barras para produto específico em todas as UNEs."""
        produto_codigo = params.get('produto_codigo')

        try:
            produto_codigo = int(produto_codigo)
        except (ValueError, TypeError):
            return {"error": f"Código de produto inválido: {produto_codigo}", "type": "error"}

        # Verificar se produto existe
        produto_data = df[df['codigo'] == produto_codigo]
        if produto_data.empty:
            return {"error": f"Produto {produto_codigo} não encontrado", "type": "error"}

        produto_nome = produto_data.iloc[0]['nome_produto']

        # Agrupar por UNE e somar vendas
        vendas_meses = [f'mes_{i:02d}' for i in range(1, 13)]
        vendas_por_une = produto_data.groupby(['une', 'une_nome'])[vendas_meses].sum()
        vendas_por_une['vendas_total'] = vendas_por_une.sum(axis=1)

        # Ordenar por vendas totais (decrescente)
        vendas_por_une = vendas_por_une.sort_values('vendas_total', ascending=False)

        # Preparar dados para gráfico com melhorias visuais
        if len(vendas_por_une) > 20:
            # Se muitas UNEs, pegar apenas as top 20 para evitar gráfico muito largo
            vendas_por_une_top = vendas_por_une.head(20)
            titulo_extra = f" (Top 20 de {len(vendas_por_une)} UNEs)"
        else:
            vendas_por_une_top = vendas_por_une
            titulo_extra = ""

        # Criar labels melhorados
        x_labels = []
        y_values = []
        for (une_codigo, une_nome), row in vendas_por_une_top.iterrows():
            label = f"{une_nome}\\n(UNE {une_codigo})"
            x_labels.append(label)
            y_values.append(float(row['vendas_total']))

        # Cores baseadas na performance (verde para altas vendas, amarelo para médias, vermelho para baixas)
        max_vendas = max(y_values) if y_values else 1
        colors = []
        for valor in y_values:
            if valor >= max_vendas * 0.7:
                colors.append('#2E8B57')  # Verde escuro para top performers
            elif valor >= max_vendas * 0.3:
                colors.append('#FFD700')  # Dourado para performance média
            else:
                colors.append('#CD5C5C')  # Vermelho suave para baixa performance

        total_vendas = sum(y_values)

        # Criar dados otimizados para gráfico
        chart_data = {
            "x": x_labels,
            "y": y_values,
            "type": "bar",
            "colors": colors,
            "show_values": True,  # Mostrar valores nas barras
            "height": max(400, min(800, len(x_labels) * 40)),  # Altura responsiva
            "margin": {"l": 80, "r": 80, "t": 100, "b": 120}  # Margens maiores para labels
        }

        return {
            "type": "chart",
            "title": f"Vendas por UNE - {produto_nome}{titulo_extra}",
            "result": {
                "chart_data": chart_data,
                "produto_codigo": produto_codigo,
                "produto_nome": produto_nome,
                "total_unes": len(vendas_por_une),
                "unes_exibidas": len(vendas_por_une_top),
                "total_vendas": total_vendas,
                "maior_une": vendas_por_une.index[0] if len(vendas_por_une) > 0 else None,
                "maior_vendas": vendas_por_une.iloc[0]['vendas_total'] if len(vendas_por_une) > 0 else 0
            },
            "summary": f"Gráfico de barras gerado para {produto_nome} (código {produto_codigo}) em {len(vendas_por_une_top)} UNEs. Total de vendas: {total_vendas:,.0f} unidades.",
            "tokens_used": 0
        }

    def _query_fallback(self, df: pd.DataFrame, query_type: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback para queries não implementadas, sinalizando para usar o grafo principal."""
        logger.warning(f"Consulta não implementada ou não compreendida no DirectQueryEngine: {query_type}. Acionando fallback para o agent_graph.")
        return {
            "type": "fallback",
            "error": "Consulta não compreendida pelo motor de busca rápida. Usando IA avançada.",
            "summary": "Acionando fallback para processamento com IA.",
            "title": "Necessário Processamento Avançado"
        }

    def process_query(self, user_query: str) -> Dict[str, Any]:
        """Processa query completa: classifica + executa SEM usar LLM."""
        start_time = datetime.now()

        # Classificar intenção SEM LLM
        query_type, params = self.classify_intent_direct(user_query)

        # Executar consulta direta
        result = self.execute_direct_query(query_type, params)

        # Adicionar metadados
        result['query_original'] = user_query
        result['query_type'] = query_type
        result['processing_time'] = (datetime.now() - start_time).total_seconds()
        result['method'] = 'direct_query'  # Indica que NÃO usou LLM

        logger.info(f"Query processada em {result['processing_time']:.2f}s - ZERO tokens LLM")

        return result

    def get_available_queries(self) -> List[Dict[str, str]]:
        """Retorna lista de consultas disponíveis para sugestões."""
        return [
            {"keyword": keyword, "description": f"Executa consulta: {query_type}"}
            for keyword, query_type in list(self.keywords_map.items())[:20]
        ]