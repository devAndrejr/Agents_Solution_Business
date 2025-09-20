'''
Interface Otimizada para Economia Máxima de LLM
Sistema que prioriza consultas diretas e usa cache agressivo.
'''
import streamlit as st
import uuid
import pandas as pd
import logging
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, Any
import hashlib

# Configuração da página DEVE vir primeiro
st.set_page_config(
    page_title="Agent_BI - Otimizado",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Importações do sistema otimizado
try:
    from core.connectivity.parquet_adapter import ParquetAdapter
    from core.business_intelligence.direct_query_engine import DirectQueryEngine
    from core.business_intelligence.smart_cache import SmartCache
    SYSTEM_AVAILABLE = True
except Exception as e:
    st.error(f"Erro ao carregar sistema: {e}")
    SYSTEM_AVAILABLE = False

# Configuração de logging avançado
from core.utils.logger_config import get_logger, log_query_attempt, log_critical_error

logger = get_logger('agent_bi.streamlit')

# Sistema de autenticação admin
def check_admin_login():
    """Verifica se o usuário está logado como admin."""
    return st.session_state.get('admin_logged_in', False)

def login_screen():
    """Exibe a tela de login centralizada."""
    st.markdown("<style>div[data-testid='stVerticalBlock'] {gap: 0.5rem;}</style>", unsafe_allow_html=True)

    st.markdown("""
    <div class="main-header">
        <h1>📊 Agent_BI</h1>
        <p>Sistema de Business Intelligence</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        with st.form("login_form"):
            st.subheader("🔐 Acesso Restrito")
            admin_password = st.text_input("Senha de Acesso:", type="password", key="admin_pass")
            submitted = st.form_submit_button("Entrar", use_container_width=True)

            if submitted:
                correct_hash = "e99a18c428cb38d5f260853678922e03"  # Hash de "admin123"
                if admin_password:
                    password_hash = hashlib.md5(admin_password.encode()).hexdigest()
                    if password_hash == correct_hash:
                        st.session_state.admin_logged_in = True
                        st.rerun()
                    else:
                        st.error("❌ Senha incorreta")
                else:
                    st.warning("❌ Por favor, digite a senha")

def main_app():
    """Renderiza a aplicação principal após o login."""
    parquet_adapter, query_engine, cache = init_system()

    if not all([parquet_adapter, query_engine, cache]):
        st.error("O sistema não está disponível. Verifique a configuração e o arquivo de dados.")
        if st.button("Tentar Novamente"):
            st.rerun()
        return

    # --- BARRA LATERAL ---
    with st.sidebar:
        st.markdown("""
        <div style="padding: 1rem; text-align: center;">
            <h2>📊 Agent_BI</h2>
            <p style="font-size: 0.9rem; color: #888;">Menu Principal</p>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("---")

        # Botão de logout
        if st.button("🔒 Sair (Logout)", use_container_width=True):
            st.session_state.admin_logged_in = False
            st.rerun()

        st.markdown("---")
        cache_stats = cache.get_stats()
        st.markdown("### 📈 Estatísticas do Cache")
        st.markdown(f"""
        <div class="cache-stats">
            <strong>💰 Economia de Tokens:</strong> {cache_stats['tokens_saved']:,}<br>
            <strong>🎯 Taxa de Acerto:</strong> {cache_stats['hit_rate_percent']}%<br>
            <strong>📁 Arquivos em Cache:</strong> {cache_stats['cache_files']}<br>
            <strong>⚡ Cache em Memória:</strong> {cache_stats['memory_cache_size']}
        </div>
        """, unsafe_allow_html=True)

        if st.button("🗑️ Limpar Cache", use_container_width=True):
            cache.clear_all()
            st.success("Cache limpo!")
            st.rerun()

    # --- CONTEÚDO PRINCIPAL ---
    st.markdown("""
    <div class="main-header">
        <h1>AGENT SOLUTIONS BUSINESS</h1>
        <p>Business Intelligence com Economia Máxima de LLM</p>
    </div>
    """, unsafe_allow_html=True)

    st.header("💬 Faça sua Consulta")
    query_input = st.text_input(
        "Digite sua pergunta sobre os dados:",
        value=st.session_state.get('selected_query', ''),
        placeholder="Ex: gere um gráfico de vendas do produto 59294"
    )

    if query_input:
        spinner_text = "🔍 Processando consulta..."
        with st.spinner(spinner_text):
            try:
                logger.info(f"PROCESSANDO CONSULTA USUÁRIO: '{query_input}'")
                query_type, params = query_engine.classify_intent_direct(query_input)
                logger.info(f"CLASSIFICADO COMO: {query_type} | Params: {params}")

                cached_result = cache.get(query_type, params)
                if cached_result:
                    logger.info(f"RESULTADO DO CACHE: {query_type}")
                    st.success("⚡ Resultado obtido do cache (0 tokens LLM)")
                    result = cached_result
                    log_query_attempt(query_input, query_type, params, True, None)
                else:
                    logger.info(f"EXECUTANDO CONSULTA NOVA: {query_type}")
                    result = query_engine.process_query(query_input)
                    if result.get('type') != 'error':
                        cache.set(query_type, params, result, tokens_would_use=150)
                        logger.info(f"RESULTADO SALVO NO CACHE: {query_type}")
                
                logger.info(f"EXIBINDO RESULTADO: {result.get('type', 'N/A')} - {result.get('title', 'N/A')}")
                display_result(result)

            except Exception as e:
                error_msg = str(e)
                logger.error(f"ERRO CRÍTICO NO STREAMLIT: {error_msg}")
                log_critical_error(e, "streamlit_query_processing", {"user_query": query_input})
                st.error(f"Erro ao processar consulta: {error_msg}")
                logger.error(f"TRACEBACK COMPLETO: {traceback.format_exc()}")

    # Painel Admin (sempre visível para o admin logado)
    admin_panel(cache, query_engine, parquet_adapter)

def main():
    """Função principal que controla o fluxo de login e a aplicação."""
    if 'admin_logged_in' not in st.session_state:
        st.session_state.admin_logged_in = False

    if check_admin_login():
        main_app()
    else:
        login_screen()

def admin_panel(cache, query_engine, parquet_adapter):
    """Painel administrativo com informações detalhadas."""
    st.markdown("---")
    st.header("🛠️ Painel Administrativo")

    admin_tabs = st.tabs(["📊 Estatísticas Detalhadas", "🔧 Configurações", "🐛 Debug", "💾 Cache Management", "📋 Logs do Sistema"])

    with admin_tabs[0]:  # Estatísticas Detalhadas
        st.subheader("📈 Estatísticas Completas do Sistema")

        col1, col2, col3 = st.columns(3)

        with col1:
            cache_stats = cache.get_stats()
            st.metric("Total Cache Hits", cache_stats['hits'])
            st.metric("Total Cache Misses", cache_stats['misses'])
            st.metric("Taxa de Acerto", f"{cache_stats['hit_rate_percent']}%")

        with col2:
            st.metric("Tokens Economizados", f"{cache_stats['tokens_saved']:,}")
            st.metric("Arquivos em Cache", cache_stats['cache_files'])
            st.metric("Economia Estimada", f"${cache_stats['tokens_saved'] * 0.002 / 1000:.4f}")

        with col3:
            st.metric("Memória Cache", cache_stats['memory_cache_size'])
            st.metric("Consultas Disponíveis", len(query_engine.get_available_queries()))
            st.metric("Status Sistema", "🟢 Online")

    with admin_tabs[1]:  # Configurações
        st.subheader("⚙️ Configurações do Sistema")

        st.markdown("**Configurações de Cache:**")
        max_cache_size = st.slider("Tamanho Máximo Cache (MB)", 10, 200, 50)

        st.markdown("**Configurações de LLM:**")
        enable_llm = st.checkbox("Habilitar LLM Fallback", value=False)
        daily_token_limit = st.number_input("Limite Diário de Tokens", 1000, 50000, 5000)

        if st.button("Aplicar Configurações"):
            st.success("✅ Configurações aplicadas (funcionalidade em desenvolvimento)")

    with admin_tabs[2]:  # Debug
        st.subheader("🐛 Informações de Debug")

        # Info do sistema
        st.markdown("**Informações do Sistema:**")
        debug_info = {
            "Diretório de Cache": str(cache.cache_dir),
            "Sistema Disponível": str(SYSTEM_AVAILABLE),
            "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Versão Interface": "Otimizada v2.0",
            "Modo Economia": "Máxima"
        }

        for key, value in debug_info.items():
            st.text(f"{key}: {value}")

        # Logs recentes
        st.markdown("**Consultas Disponíveis (Debug):**")
        available_queries = query_engine.get_available_queries()[:10]
        for i, query in enumerate(available_queries, 1):
            st.text(f"{i}. {query['keyword']} - {query['description']}")

    with admin_tabs[3]:  # Cache Management
        st.subheader("💾 Gerenciamento de Cache")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("🗑️ Limpar Cache Completo"):
                cache.clear_all()
                st.success("Cache limpo com sucesso!")
                st.rerun()

            if st.button("🔄 Recarregar Cache Frequente"):
                cache.preload_frequent_queries(parquet_adapter)
                st.success("Cache recarregado!")

        with col2:
            if st.button("📊 Aquecer Cache com Consultas Teste"):
                test_queries = ["produto mais vendido", "filial mais vendeu", "segmento mais vendeu"]
                results = cache.warm_up_cache(test_queries, parquet_adapter)
                st.success(f"Cache aquecido: {results}")

            if st.button("📋 Exportar Estatísticas"):
                stats = cache.get_stats()
                st.json(stats)

    with admin_tabs[4]:  # Logs do Sistema
        st.subheader("📋 Logs do Sistema")

        # Seletor de tipo de log
        log_type = st.selectbox(
            "Tipo de Log",
            ["Consultas (queries.log)", "Erros (errors.log)", "Performance (performance.log)", "Principal (agent_bi_main.log)"]
        )

        # Número de linhas para exibir
        num_lines = st.slider("Últimas N linhas", 10, 500, 100)

        if st.button("🔍 Carregar Logs"):
            try:
                import os
                from pathlib import Path

                log_files = {
                    "Consultas (queries.log)": "logs/queries.log",
                    "Erros (errors.log)": "logs/errors.log",
                    "Performance (performance.log)": "logs/performance.log",
                    "Principal (agent_bi_main.log)": "logs/agent_bi_main.log"
                }

                log_file = log_files[log_type]

                if os.path.exists(log_file):
                    with open(log_file, 'r', encoding='utf-8') as f:
                        lines = f.readlines()

                    # Últimas N linhas
                    recent_lines = lines[-num_lines:]

                    st.text_area(
                        f"📋 {log_type} - Últimas {len(recent_lines)} linhas:",
                        ''.join(recent_lines),
                        height=400
                    )

                    # Estatísticas do arquivo
                    st.info(f"📊 Total de linhas no arquivo: {len(lines)} | Arquivo: {log_file}")

                else:
                    st.warning(f"⚠️ Arquivo de log não encontrado: {log_file}")

            except Exception as e:
                st.error(f"❌ Erro ao carregar logs: {e}")

        # Botão para limpar logs
        if st.button("🗑️ Limpar Todos os Logs"):
            try:
                import glob
                import os

                log_files = glob.glob("logs/*.log")
                for log_file in log_files:
                    if os.path.exists(log_file):
                        open(log_file, 'w').close()  # Limpar arquivo

                st.success(f"✅ {len(log_files)} arquivos de log limpos!")

            except Exception as e:
                st.error(f"❌ Erro ao limpar logs: {e}")

        # Info sobre logs
        st.markdown("""
        **📋 Tipos de Logs Disponíveis:**
        - **Consultas:** Todas as consultas dos usuários com sucesso/falha
        - **Erros:** Erros críticos e tracebacks completos
        - **Performance:** Métricas de tempo de execução
        - **Principal:** Log geral do sistema
        """)

        st.markdown("**📁 Localização dos logs:** `logs/` (criados automaticamente)")

        # Atualização automática
        if st.checkbox("🔄 Atualização Automática (30s)"):
            import time
            time.sleep(30)
            st.rerun()

# CSS customizado para interface moderna
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #1e3a8a 0%, #3b82f6 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: #f8fafc;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #3b82f6;
        margin: 0.5rem 0;
    }
    .query-suggestion {
        background: #eff6ff;
        padding: 0.5rem;
        border-radius: 5px;
        margin: 0.25rem 0;
        cursor: pointer;
        border: 1px solid #dbeafe;
    }
    .query-suggestion:hover {
        background: #dbeafe;
    }
    .cache-stats {
        background: #f0f9ff;
        padding: 1rem;
        border-radius: 5px;
        border: 1px solid #0ea5e9;
        font-size: 0.9rem;
    }
</style>
""", unsafe_allow_html=True)

# Inicialização do sistema
@st.cache_resource
def init_system():
    """Inicializa sistema com cache."""
    if not SYSTEM_AVAILABLE:
        return None, None, None

    try:
        # Buscar arquivo parquet em múltiplos locais
        parquet_paths = [
            "data/parquet/admmat.parquet",
            "/mount/src/agents_solution_business/data/parquet/admmat.parquet",
            "./data/parquet/admmat.parquet"
        ]

        parquet_adapter = None
        for path in parquet_paths:
            try:
                parquet_adapter = ParquetAdapter(path)
                # Mostrar sucesso apenas para admin
                if check_admin_login():
                    st.success(f"✅ Dataset carregado: {path}")
                break
            except FileNotFoundError:
                continue

        if parquet_adapter is None:
            st.error("❌ Arquivo parquet não encontrado")
            return None, None, None

        # Inicializar componentes
        cache = SmartCache(cache_dir="cache", max_size_mb=50)
        query_engine = DirectQueryEngine(parquet_adapter)

        # Pre-carregar cache
        cache.preload_frequent_queries(parquet_adapter)

        return parquet_adapter, query_engine, cache

    except Exception as e:
        st.error(f"Erro na inicialização: {e}")
        return None, None, None

# Interface principal
def main():
    """Interface principal da aplicação."""

    # Header limpo
    if check_admin_login():
        st.markdown("""
        <div class="main-header">
            <h1>📊 Agent_BI - Sistema Otimizado</h1>
            <p>Business Intelligence com Economia Máxima de LLM</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="main-header">
            <h1>📊 Agent_BI</h1>
            <p>Sistema de Business Intelligence</p>
        </div>
        """, unsafe_allow_html=True)

    # Inicializar sistema
    parquet_adapter, query_engine, cache = init_system()

    if not all([parquet_adapter, query_engine, cache]):
        st.error("Sistema não disponível. Verifique a configuração.")
        return

    # Sidebar limpo
    with st.sidebar:
        # Sistema de login admin
        admin_login_form()

        # Informações básicas apenas se admin logado
        if check_admin_login():
            st.markdown("---")
            cache_stats = cache.get_stats()
            st.markdown("### 📈 Estatísticas do Cache")
            st.markdown(f"""
            <div class="cache-stats">
                <strong>💰 Economia de Tokens:</strong> {cache_stats['tokens_saved']:,}<br>
                <strong>🎯 Taxa de Acerto:</strong> {cache_stats['hit_rate_percent']}%<br>
                <strong>📁 Arquivos em Cache:</strong> {cache_stats['cache_files']}<br>
                <strong>⚡ Cache em Memória:</strong> {cache_stats['memory_cache_size']}
            </div>
            """, unsafe_allow_html=True)

            if st.button("🗑️ Limpar Cache"):
                cache.clear_all()
                st.success("Cache limpo!")
                st.rerun()

    # Área principal - Interface limpa
    st.header("💬 Faça sua Consulta")

    # Input de consulta limpo
    query_input = st.text_input(
        "Digite sua pergunta sobre os dados:",
        value=st.session_state.get('selected_query', ''),
        placeholder="Ex: quais são os 10 produtos mais vendidos no segmento tecidos?"
    )

    # Processar consulta
    if query_input:
        spinner_text = "🔍 Processando consulta (sem usar LLM)..." if check_admin_login() else "🔍 Processando consulta..."

        with st.spinner(spinner_text):
            try:
                logger.info(f"PROCESSANDO CONSULTA USUÁRIO: '{query_input}'")

                # Verificar cache primeiro
                query_type, params = query_engine.classify_intent_direct(query_input)
                logger.info(f"CLASSIFICADO COMO: {query_type} | Params: {params}")

                cached_result = cache.get(query_type, params)

                if cached_result:
                    logger.info(f"RESULTADO DO CACHE: {query_type}")
                    if check_admin_login():
                        st.success("⚡ Resultado obtido do cache (0 tokens LLM)")
                    result = cached_result
                    log_query_attempt(query_input, query_type, params, True, None)
                else:
                    # Executar consulta direta
                    logger.info(f"EXECUTANDO CONSULTA NOVA: {query_type}")
                    result = query_engine.process_query(query_input)

                    # Salvar no cache
                    if result.get('type') != 'error':
                        cache.set(query_type, params, result, tokens_would_use=150)
                        logger.info(f"RESULTADO SALVO NO CACHE: {query_type}")

                # Exibir resultado
                logger.info(f"EXIBINDO RESULTADO: {result.get('type', 'N/A')} - {result.get('title', 'N/A')}")
                display_result(result)

            except Exception as e:
                error_msg = str(e)
                logger.error(f"ERRO CRÍTICO NO STREAMLIT: {error_msg}")
                log_critical_error(e, "streamlit_query_processing", {"user_query": query_input})
                st.error(f"Erro ao processar consulta: {error_msg}")

                # Log adicional para debugging
                import traceback
                logger.error(f"TRACEBACK COMPLETO: {traceback.format_exc()}")

    # Painel Admin (apenas se logado)
    if check_admin_login():
        admin_panel(cache, query_engine, parquet_adapter)

def display_result(result: Dict[str, Any]):
    """Exibe resultado da consulta com gráficos."""

    if result.get('type') == 'error':
        st.error(f"❌ {result.get('error', 'Erro desconhecido')}")
        return

    # Header do resultado
    st.markdown("---")
    st.header(f"📊 {result.get('title', 'Resultado')}")

    # Métricas técnicas apenas para admin
    if check_admin_login():
        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <strong>Método:</strong> {result.get('method', 'N/A')}<br>
                <strong>Tokens LLM:</strong> {result.get('tokens_used', 0)}
            </div>
            """, unsafe_allow_html=True)

        with col2:
            st.markdown(f"""
            <div class="metric-card">
                <strong>Tempo:</strong> {result.get('processing_time', 0):.2f}s<br>
                <strong>Tipo:</strong> {result.get('type', 'N/A')}
            </div>
            """, unsafe_allow_html=True)

        with col3:
            st.markdown(f"""
            <div class="metric-card">
                <strong>Query:</strong> {result.get('query_type', 'N/A')}<br>
                <strong>Status:</strong> ✅ Sucesso
            </div>
            """, unsafe_allow_html=True)

    # Resultado principal
    st.markdown("### 📋 Resultado")
    st.success(result.get('summary', 'Consulta executada com sucesso'))

    # Dados detalhados
    if 'result' in result:
        st.markdown("### 📊 Dados Detalhados")

        result_data = result['result']

        if isinstance(result_data, dict):
            for key, value in result_data.items():
                if isinstance(value, (int, float)):
                    st.metric(key.replace('_', ' ').title(), f"{value:,.2f}" if isinstance(value, float) else f"{value:,}")
                else:
                    st.write(f"**{key.replace('_', ' ').title()}:** {value}")

    # Gráfico
    if 'chart' in result and result['chart'] is not None:
        st.markdown("### 📈 Visualização")
        st.plotly_chart(result['chart'], use_container_width=True)

    # Criar gráfico simples se não tiver um
    elif result.get('type') in ['produto_ranking', 'filial_ranking', 'segmento_ranking', 'produto_especifico', 'top_produtos_segmento', 'evolucao_vendas_produto']:
        st.markdown("### 📈 Visualização Rápida")
        create_simple_chart(result)

def create_simple_chart(result: Dict[str, Any]):
    """Cria gráfico melhorado baseado no tipo de resultado."""

    result_data = result.get('result', {})
    result_type = result.get('type')

    if result_type == 'produto_ranking':
        # Gráfico de barras com largura controlada
        produto_nome = result_data.get('produto', 'N/A')[:30] + "..." if len(result_data.get('produto', '')) > 30 else result_data.get('produto', 'N/A')

        fig = go.Figure(data=[
            go.Bar(
                x=[produto_nome],
                y=[result_data.get('vendas', 0)],
                marker_color='#3b82f6',
                width=0.4  # Controla largura da barra
            )
        ])
        fig.update_layout(
            title="🏆 Produto Mais Vendido",
            xaxis_title="Produto",
            yaxis_title="Vendas",
            height=400,
            showlegend=False
        )
        st.plotly_chart(fig, use_container_width=True)

    elif result_type == 'produto_especifico':
        # Para produto específico, mostrar gráfico indicador/gauge
        vendas = result_data.get('vendas_total', 0)
        nome = result_data.get('nome', 'N/A')[:25] + "..." if len(result_data.get('nome', '')) > 25 else result_data.get('nome', 'N/A')

        fig = go.Figure(go.Indicator(
            mode = "gauge+number+delta",
            value = vendas,
            title = {'text': f"📊 Vendas - {nome}"},
            gauge = {
                'axis': {'range': [None, vendas * 1.5]},
                'bar': {'color': "#3b82f6"},
                'steps': [
                    {'range': [0, vendas * 0.5], 'color': "lightgray"},
                    {'range': [vendas * 0.5, vendas], 'color': "lightblue"}],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': vendas * 0.9}
            }
        ))
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)

    elif result_type == 'top_produtos_segmento':
        # Para top produtos, criar gráfico de barras horizontais
        produtos = result_data.get('produtos', [])[:10]  # Máximo 10

        if len(produtos) > 1:
            nomes = [p['nome'][:25] + "..." if len(p['nome']) > 25 else p['nome'] for p in produtos]
            vendas = [p['vendas'] for p in produtos]

            fig = go.Figure(data=[
                go.Bar(
                    y=nomes[::-1],  # Reverter para mostrar maior no topo
                    x=vendas[::-1],
                    orientation='h',
                    marker_color='#10b981'
                )
            ])
            fig.update_layout(
                title=f"📈 Top {len(produtos)} Produtos",
                xaxis_title="Vendas",
                yaxis_title="Produtos",
                height=max(400, len(produtos) * 40),
                showlegend=False
            )
            st.plotly_chart(fig, use_container_width=True)

    elif result_type == 'filial_ranking':
        # Gráfico para filial com largura controlada
        filial_nome = result_data.get('filial', 'N/A')[:20] + "..." if len(result_data.get('filial', '')) > 20 else result_data.get('filial', 'N/A')

        fig = go.Figure(data=[
            go.Bar(
                x=[filial_nome],
                y=[result_data.get('vendas', 0)],
                marker_color='#10b981',
                width=0.4
            )
        ])
        fig.update_layout(
            title="🏪 Filial que Mais Vendeu",
            xaxis_title="Filial",
            yaxis_title="Vendas",
            height=400,
            showlegend=False
        )
        st.plotly_chart(fig, use_container_width=True)

    elif result_type == 'segmento_ranking':
        # Gráfico pizza para segmento
        fig = go.Figure(data=[
            go.Pie(
                labels=[result_data.get('segmento', 'N/A')],
                values=[result_data.get('vendas', 0)],
                hole=0.3,
                marker_colors=['#8b5cf6']
            )
        ])
        fig.update_layout(
            title="🎯 Segmento Campeão",
            height=400,
            showlegend=False
        )
        st.plotly_chart(fig, use_container_width=True)

# Controle de sessão
if 'selected_query' not in st.session_state:
    st.session_state.selected_query = ''

if 'admin_logged_in' not in st.session_state:
    st.session_state.admin_logged_in = False

# Footer limpo para clientes
if check_admin_login():
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #64748b; font-size: 0.9rem;">
        🚀 Agent_BI Otimizado - Economia Máxima de LLM |
        💰 Zero tokens para consultas básicas |
        ⚡ Cache inteligente ativo
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
  )
            fig.update_layout(height=450)
            st.plotly_chart(fig, use_container_width=True)

# Controle de sessão
if 'selected_query' not in st.session_state:
    st.session_state.selected_query = ''

if 'admin_logged_in' not in st.session_state:
    st.session_state.admin_logged_in = False

# Footer limpo para clientes
if check_admin_login():
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #64748b; font-size: 0.9rem;">
        🚀 Agent_BI Otimizado - Economia Máxima de LLM |
        💰 Zero tokens para consultas básicas |
        ⚡ Cache inteligente ativo
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
:
    main()
