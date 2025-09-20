"""
Módulo de Gráficos Avançados para Business Intelligence
Geração de visualizações sofisticadas baseadas nas 20 perguntas essenciais do negócio.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)

class AdvancedChartGenerator:
    """Gerador de gráficos avançados para análises de negócio."""

    def __init__(self):
        """Inicializa o gerador de gráficos."""
        self.color_palette = {
            'primary': '#1f77b4',
            'secondary': '#ff7f0e',
            'success': '#2ca02c',
            'warning': '#d62728',
            'info': '#9467bd',
            'light': '#8c564b',
            'dark': '#e377c2'
        }
        self.chart_configs = self._load_chart_configs()

    def _load_chart_configs(self) -> Dict[str, Any]:
        """Carrega configurações padrão para diferentes tipos de gráfico."""
        return {
            'ranking_products': {
                'type': 'horizontal_bar',
                'title_template': 'Top {limit} Produtos Mais Vendidos',
                'x_axis': 'Vendas Totais',
                'y_axis': 'Produtos',
                'color_scheme': 'viridis',
                'show_values': True
            },
            'ranking_filiais': {
                'type': 'bar',
                'title_template': 'Ranking de Vendas por Filial',
                'x_axis': 'Filiais',
                'y_axis': 'Vendas Totais',
                'color_scheme': 'blues',
                'show_values': True
            },
            'temporal_comparison': {
                'type': 'line_with_markers',
                'title_template': 'Evolução Temporal de Vendas',
                'x_axis': 'Período',
                'y_axis': 'Vendas',
                'color_scheme': 'plotly',
                'show_trend': True
            },
            'distribution_pie': {
                'type': 'pie',
                'title_template': 'Distribuição por {category}',
                'show_percentages': True,
                'hole_size': 0.3
            },
            'kpi_gauge': {
                'type': 'gauge',
                'title_template': '{metric} - {period}',
                'show_target': True,
                'color_zones': True
            }
        }

    def create_product_ranking_chart(self, df: pd.DataFrame, limit: int = 10,
                                   chart_type: str = 'horizontal_bar') -> go.Figure:
        """
        Cria gráfico de ranking de produtos mais vendidos.

        Args:
            df: DataFrame com colunas ['nome_produto', 'vendas_total']
            limit: Número de produtos no ranking
            chart_type: Tipo do gráfico ('horizontal_bar', 'bar', 'treemap')
        """
        try:
            # Preparar dados
            df_top = df.nlargest(limit, 'vendas_total')

            if chart_type == 'horizontal_bar':
                fig = px.bar(
                    df_top,
                    x='vendas_total',
                    y='nome_produto',
                    orientation='h',
                    title=f'Top {limit} Produtos Mais Vendidos',
                    labels={'vendas_total': 'Vendas Totais', 'nome_produto': 'Produtos'},
                    color='vendas_total',
                    color_continuous_scale='viridis'
                )
                fig.update_layout(yaxis={'categoryorder': 'total ascending'})

            elif chart_type == 'treemap':
                fig = px.treemap(
                    df_top,
                    values='vendas_total',
                    names='nome_produto',
                    title=f'Distribuição de Vendas - Top {limit} Produtos',
                    color='vendas_total',
                    color_continuous_scale='viridis'
                )

            else:  # bar padrão
                fig = px.bar(
                    df_top,
                    x='nome_produto',
                    y='vendas_total',
                    title=f'Top {limit} Produtos Mais Vendidos',
                    color='vendas_total',
                    color_continuous_scale='blues'
                )
                fig.update_xaxis(tickangle=45)

            # Configurações comuns
            fig.update_layout(
                font=dict(size=12),
                showlegend=False,
                height=600,
                margin=dict(l=20, r=20, t=60, b=20)
            )

            # Adicionar valores nas barras
            fig.update_traces(texttemplate='%{value:,.0f}', textposition='auto')

            return fig

        except Exception as e:
            logger.error(f"Erro ao criar gráfico de ranking de produtos: {e}")
            raise

    def create_filial_performance_chart(self, df: pd.DataFrame,
                                      chart_type: str = 'bar') -> go.Figure:
        """
        Cria gráfico de performance por filial.

        Args:
            df: DataFrame com colunas ['une_nome', 'vendas_total']
            chart_type: Tipo do gráfico ('bar', 'map', 'pie')
        """
        try:
            if chart_type == 'pie':
                fig = px.pie(
                    df,
                    values='vendas_total',
                    names='une_nome',
                    title='Distribuição de Vendas por Filial',
                    color_discrete_sequence=px.colors.qualitative.Set3
                )
                fig.update_traces(textposition='inside', textinfo='percent+label')

            elif chart_type == 'map':
                # Para um mapa real, seria necessário dados de localização
                # Por enquanto, criamos um gráfico de bolhas
                fig = px.scatter(
                    df,
                    x='une_nome',
                    y='vendas_total',
                    size='vendas_total',
                    title='Performance de Vendas por Filial',
                    labels={'vendas_total': 'Vendas Totais', 'une_nome': 'Filiais'}
                )

            else:  # bar padrão
                df_sorted = df.sort_values('vendas_total', ascending=False)
                fig = px.bar(
                    df_sorted,
                    x='une_nome',
                    y='vendas_total',
                    title='Ranking de Vendas por Filial',
                    color='vendas_total',
                    color_continuous_scale='blues'
                )
                fig.update_xaxis(tickangle=45)

            fig.update_layout(
                height=600,
                showlegend=False,
                margin=dict(l=20, r=20, t=60, b=100)
            )

            return fig

        except Exception as e:
            logger.error(f"Erro ao criar gráfico de performance de filiais: {e}")
            raise

    def create_temporal_comparison_chart(self, df: pd.DataFrame,
                                       period_columns: List[str],
                                       chart_type: str = 'line') -> go.Figure:
        """
        Cria gráfico de comparação temporal.

        Args:
            df: DataFrame com dados temporais
            period_columns: Lista de colunas de período (ex: ['mes_01', 'mes_02', ...])
            chart_type: Tipo do gráfico ('line', 'area', 'waterfall')
        """
        try:
            # Agregar dados por período
            period_data = []
            for col in period_columns:
                if col in df.columns:
                    total = df[col].sum()
                    period_data.append({
                        'periodo': col,
                        'vendas': total,
                        'mes_numero': int(col.split('_')[1])
                    })

            df_temporal = pd.DataFrame(period_data).sort_values('mes_numero')

            if chart_type == 'area':
                fig = px.area(
                    df_temporal,
                    x='periodo',
                    y='vendas',
                    title='Evolução de Vendas Mensais (Área)',
                    labels={'vendas': 'Vendas Totais', 'periodo': 'Período'}
                )

            elif chart_type == 'waterfall':
                # Calcular variações
                df_temporal['variacao'] = df_temporal['vendas'].diff()

                fig = go.Figure()
                fig.add_trace(go.Waterfall(
                    name="Evolução Mensal",
                    orientation="v",
                    measure=["absolute"] + ["relative"] * (len(df_temporal) - 1),
                    x=df_temporal['periodo'],
                    textposition="outside",
                    text=[f"{val:,.0f}" for val in df_temporal['vendas']],
                    y=df_temporal['vendas'].tolist(),
                    connector={"line": {"color": "rgb(63, 63, 63)"}},
                ))
                fig.update_layout(title="Evolução de Vendas - Análise Waterfall")

            else:  # line padrão
                fig = px.line(
                    df_temporal,
                    x='periodo',
                    y='vendas',
                    title='Evolução de Vendas Mensais',
                    markers=True,
                    labels={'vendas': 'Vendas Totais', 'periodo': 'Período'}
                )

                # Adicionar linha de tendência
                z = np.polyfit(df_temporal['mes_numero'], df_temporal['vendas'], 1)
                p = np.poly1d(z)
                fig.add_traces(go.Scatter(
                    x=df_temporal['periodo'],
                    y=p(df_temporal['mes_numero']),
                    mode='lines',
                    name='Tendência',
                    line=dict(dash='dash', color='red')
                ))

            fig.update_layout(
                height=500,
                margin=dict(l=20, r=20, t=60, b=20)
            )

            return fig

        except Exception as e:
            logger.error(f"Erro ao criar gráfico temporal: {e}")
            raise

    def create_segmentation_chart(self, df: pd.DataFrame, segment_column: str,
                                value_column: str, chart_type: str = 'pie') -> go.Figure:
        """
        Cria gráfico de segmentação (segmentos, categorias, fabricantes).

        Args:
            df: DataFrame com dados de segmentação
            segment_column: Coluna de segmentação
            value_column: Coluna de valores
            chart_type: Tipo do gráfico ('pie', 'donut', 'sunburst', 'treemap')
        """
        try:
            # Agregar por segmento
            df_segment = df.groupby(segment_column)[value_column].sum().reset_index()
            df_segment = df_segment.sort_values(value_column, ascending=False)

            if chart_type == 'donut':
                fig = px.pie(
                    df_segment,
                    values=value_column,
                    names=segment_column,
                    title=f'Distribuição por {segment_column.title()}',
                    hole=0.4  # Cria o efeito donut
                )

            elif chart_type == 'treemap':
                fig = px.treemap(
                    df_segment,
                    values=value_column,
                    names=segment_column,
                    title=f'Mapa de Árvore - {segment_column.title()}',
                    color=value_column,
                    color_continuous_scale='viridis'
                )

            elif chart_type == 'sunburst':
                # Para sunburst, precisaríamos de hierarquia
                # Por enquanto, fazemos um treemap
                fig = px.treemap(
                    df_segment,
                    values=value_column,
                    names=segment_column,
                    title=f'Distribuição Hierárquica - {segment_column.title()}'
                )

            else:  # pie padrão
                fig = px.pie(
                    df_segment,
                    values=value_column,
                    names=segment_column,
                    title=f'Distribuição por {segment_column.title()}'
                )

            fig.update_layout(height=600)
            return fig

        except Exception as e:
            logger.error(f"Erro ao criar gráfico de segmentação: {e}")
            raise

    def create_kpi_dashboard(self, kpis: Dict[str, Any]) -> go.Figure:
        """
        Cria dashboard com KPIs principais.

        Args:
            kpis: Dicionário com KPIs {'nome': {'value': X, 'target': Y, 'unit': 'R$'}}
        """
        try:
            # Calcular layout baseado no número de KPIs
            num_kpis = len(kpis)
            cols = min(3, num_kpis)
            rows = (num_kpis + cols - 1) // cols

            fig = make_subplots(
                rows=rows,
                cols=cols,
                subplot_titles=list(kpis.keys()),
                specs=[[{"type": "indicator"}] * cols for _ in range(rows)],
                vertical_spacing=0.4
            )

            for i, (kpi_name, kpi_data) in enumerate(kpis.items()):
                row = i // cols + 1
                col = i % cols + 1

                # Configurar gauge/indicator
                fig.add_trace(
                    go.Indicator(
                        mode="gauge+number+delta",
                        value=kpi_data['value'],
                        domain={'x': [0, 1], 'y': [0, 1]},
                        title={'text': kpi_name},
                        delta={'reference': kpi_data.get('target', kpi_data['value'])},
                        gauge={
                            'axis': {'range': [None, kpi_data.get('max', kpi_data['value'] * 1.5)]},
                            'bar': {'color': "darkblue"},
                            'steps': [
                                {'range': [0, kpi_data.get('target', kpi_data['value']) * 0.7], 'color': "lightgray"},
                                {'range': [kpi_data.get('target', kpi_data['value']) * 0.7, kpi_data.get('target', kpi_data['value'])], 'color': "gray"}
                            ],
                            'threshold': {
                                'line': {'color': "red", 'width': 4},
                                'thickness': 0.75,
                                'value': kpi_data.get('target', kpi_data['value'])
                            }
                        }
                    ),
                    row=row, col=col
                )

            fig.update_layout(
                height=200 * rows,
                title_text="Dashboard de KPIs Principais",
                title_x=0.5
            )

            return fig

        except Exception as e:
            logger.error(f"Erro ao criar dashboard de KPIs: {e}")
            raise

    def create_advanced_comparison_chart(self, df: pd.DataFrame,
                                       comparison_type: str = 'month_over_month') -> go.Figure:
        """
        Cria gráficos avançados de comparação.

        Args:
            df: DataFrame com dados para comparação
            comparison_type: Tipo de comparação ('month_over_month', 'year_over_year', 'product_comparison')
        """
        try:
            if comparison_type == 'month_over_month':
                # Comparar mês atual vs anterior
                df_comparison = df[['nome_produto', 'mes_01', 'mes_02']].copy()
                df_comparison['variacao'] = ((df_comparison['mes_01'] - df_comparison['mes_02']) / df_comparison['mes_02'] * 100).fillna(0)
                df_comparison = df_comparison[df_comparison['mes_02'] > 0]  # Evitar divisão por zero

                # Top 10 maiores variações (positivas e negativas)
                top_growth = df_comparison.nlargest(5, 'variacao')
                top_decline = df_comparison.nsmallest(5, 'variacao')
                df_plot = pd.concat([top_growth, top_decline])

                fig = px.bar(
                    df_plot,
                    x='nome_produto',
                    y='variacao',
                    title='Variação Mensal - Top Crescimento e Declínio',
                    color='variacao',
                    color_continuous_scale='RdYlGn',
                    labels={'variacao': 'Variação (%)', 'nome_produto': 'Produtos'}
                )

                fig.update_xaxis(tickangle=45)
                fig.add_hline(y=0, line_dash="dash", line_color="black")

            elif comparison_type == 'product_comparison':
                # Comparar vendas de produtos similares
                df_vendas = df[['nome_produto', 'mes_01', 'mes_02', 'mes_03']].copy()
                df_vendas['vendas_total'] = df_vendas[['mes_01', 'mes_02', 'mes_03']].sum(axis=1)
                top_products = df_vendas.nlargest(10, 'vendas_total')

                fig = go.Figure()

                months = ['mes_01', 'mes_02', 'mes_03']
                for month in months:
                    fig.add_trace(go.Bar(
                        name=month.replace('_', ' ').title(),
                        x=top_products['nome_produto'],
                        y=top_products[month],
                        text=top_products[month],
                        textposition='auto'
                    ))

                fig.update_layout(
                    title='Comparação de Vendas - Top 10 Produtos (Últimos 3 Meses)',
                    xaxis_title='Produtos',
                    yaxis_title='Vendas',
                    barmode='group',
                    height=600
                )
                fig.update_xaxis(tickangle=45)

            fig.update_layout(margin=dict(l=20, r=20, t=60, b=100))
            return fig

        except Exception as e:
            logger.error(f"Erro ao criar gráfico de comparação avançada: {e}")
            raise

    def export_chart_config(self, chart_type: str) -> Dict[str, Any]:
        """
        Exporta configuração de um tipo de gráfico para uso em templates.

        Args:
            chart_type: Tipo do gráfico

        Returns:
            Dicionário com configurações do gráfico
        """
        config = {
            'responsive': True,
            'displayModeBar': True,
            'displaylogo': False,
            'modeBarButtonsToRemove': [
                'pan2d', 'select2d', 'lasso2d', 'resetScale2d'
            ],
            'toImageButtonOptions': {
                'format': 'png',
                'filename': f'{chart_type}_chart',
                'height': 600,
                'width': 800,
                'scale': 1
            }
        }

        return config