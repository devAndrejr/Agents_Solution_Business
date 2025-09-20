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
    page_title="AGENT SOLUTIONS BUSINESS",
    page_icon="🤖",
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
from core.auth import login as render_login_screen, sessao_expirada

logger = get_logger('agent_bi.streamlit')

# --- Funções de Autenticação e Layout ---

def check_user_login():
    """Verifica se o usuário está logado e se a sessão não expirou."""
    if sessao_expirada():
        st.session_state.authenticated = False
        st.session_state.username = None
        st.session_state.role = None
        return False
    return st.session_state.get('authenticated', False)

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
            <h2>AGENT SOLUTIONS BUSINESS</h2>
            <p style="font-size: 0.9rem; color: #888;">Menu Principal</p>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("---")

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

    admin_panel(cache, query_engine, parquet_adapter)

# --- Funções do Painel de Administração e Display ---

def admin_panel(cache, query_engine, parquet_adapter):
    """Painel administrativo com informações detalhadas."""
    st.markdown("---")
    st.header("🛠️ Painel Administrativo")
    # ... (código do admin_panel)

def display_result(result: Dict[str, Any]):
    """Exibe resultado da consulta com gráficos."""
    # ... (código do display_result)

def create_simple_chart(result: Dict[str, Any]):
    """Cria gráfico melhorado baseado no tipo de resultado."""
    # ... (código do create_simple_chart)

# --- Inicialização e Controle de Fluxo ---

@st.cache_resource
def init_system():
    """Inicializa sistema com cache."""
    # ... (código do init_system)

def main():
    """Função principal que controla o fluxo de login e a aplicação."""
    if 'admin_logged_in' not in st.session_state:
        st.session_state.admin_logged_in = False

    if check_admin_login():
        main_app()
    else:
        login_screen()

if __name__ == "__main__":
    main()y ---

def admin_panel(cache, query_engine, parquet_adapter):
    """Painel administrativo com informações detalhadas."""
    st.markdown("---")
    st.header("🛠️ Painel Administrativo")
    # ... (código do admin_panel)

def display_result(result: Dict[str, Any]):
    """Exibe resultado da consulta com gráficos."""
    # ... (código do display_result)

def create_simple_chart(result: Dict[str, Any]):
    """Cria gráfico melhorado baseado no tipo de resultado."""
    # ... (código do create_simple_chart)

# --- Inicialização e Controle de Fluxo ---

@st.cache_resource
def init_system():
    """Inicializa sistema com cache."""
    # ... (código do init_system)

def main():
    """Função principal que controla o fluxo de login e a aplicação."""
    if check_user_login():
        main_app()
    else:
        render_login_screen()

if __name__ == "__main__":
    main()