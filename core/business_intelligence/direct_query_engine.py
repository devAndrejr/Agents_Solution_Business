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

            # CORREÇÃO: Detectar EVOLUÇÃO DE VENDAS para um produto específico (MAIOR PRIORIDADE)
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
            full_dataset_queries = ["consulta_produto_especifico", "consulta_une_especifica", "evolucao_vendas_produto"]
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
                    # Ignorar colunas 'mes_xx' pois não temos o ano
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

    def _query_fallback(self, df: pd.DataFrame, query_type: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback para queries não implementadas."""
        return {
            "type": "not_implemented",
            "title": "Consulta Não Implementada",
            "result": {"message": f"Query tipo '{query_type}' ainda não implementada"},
            "summary": f"Esta consulta específica ainda não foi implementada. Use uma das consultas básicas disponíveis.",
            "tokens_used": 0,
            "available_queries": list(self.keywords_map.keys())[:10]
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