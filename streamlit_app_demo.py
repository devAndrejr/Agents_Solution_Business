"""
Interface de Usuário (Frontend) para o Agent_BI - Versão Cloud
Simplificada para funcionar no Streamlit Cloud sem dependências locais.
"""
import streamlit as st
import uuid
import pandas as pd
import os

# Usar autenticação simplificada para a nuvem
try:
    from core.auth_cloud import login, sessao_expirada
    USE_CLOUD_AUTH = True
except ImportError:
    USE_CLOUD_AUTH = False

# --- Configuração da Página ---
st.set_page_config(page_title="Agent_BI", page_icon="📊", layout="wide")

# --- Autenticação ---
if USE_CLOUD_AUTH:
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if not st.session_state.authenticated or sessao_expirada():
        st.session_state.authenticated = False
        login()
        st.stop()

# Se chegou aqui, está autenticado ou autenticação está desabilitada
st.title("📊 Agent_BI - Assistente Inteligente")

# --- Sidebar ---
with st.sidebar:
    if USE_CLOUD_AUTH and "username" in st.session_state:
        st.write(f"👤 Bem-vindo, {st.session_state.username}!")
        if st.button("🚪 Logout"):
            st.session_state.authenticated = False
            st.session_state.clear()
            st.rerun()

    st.markdown("---")
    st.info("🌤️ **Versão Cloud**\n\nEsta é uma versão simplificada que funciona na nuvem sem dependências locais.")

# --- Inicialização da Sessão ---
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": {
                "type": "text",
                "content": "🌤️ Olá! Bem-vindo ao Agent_BI Cloud! Esta é uma versão demonstrativa que funciona na nuvem. Como posso ajudar você hoje?"
            }
        }
    ]

# --- Interface de Chat ---
st.markdown("### 💬 Chat com o Agente")

# Exibir mensagens
for message in st.session_state.messages:
    if message["role"] == "user":
        with st.chat_message("user", avatar="👤"):
            st.write(message["content"]["content"])
    else:
        with st.chat_message("assistant", avatar="🤖"):
            content = message["content"]
            if isinstance(content, dict):
                if content.get("type") == "text":
                    st.write(content["content"])
                elif content.get("type") == "chart":
                    st.write(content.get("description", "Gráfico gerado"))
                    if "chart_data" in content:
                        try:
                            df = pd.DataFrame(content["chart_data"])
                            st.dataframe(df)
                        except:
                            st.write("Dados do gráfico não puderam ser exibidos")
            else:
                st.write(str(content))

# Input do usuário
if prompt := st.chat_input("Digite sua pergunta..."):
    # Adicionar mensagem do usuário
    user_message = {
        "role": "user",
        "content": {
            "type": "text",
            "content": prompt
        }
    }
    st.session_state.messages.append(user_message)

    # Exibir mensagem do usuário
    with st.chat_message("user", avatar="👤"):
        st.write(prompt)

    # Resposta simulada do agente
    with st.chat_message("assistant", avatar="🤖"):
        with st.spinner("Processando..."):
            # Resposta demonstrativa
            if "dados" in prompt.lower() or "tabela" in prompt.lower():
                response_content = {
                    "type": "text",
                    "content": f"🔍 Análise da pergunta: '{prompt}'\n\n"
                             "📊 Esta é uma versão demonstrativa do Agent_BI Cloud.\n\n"
                             "🎯 Funcionalidades disponíveis na versão completa:\n"
                             "- Conexão com bases de dados\n"
                             "- Geração de gráficos interativos\n"
                             "- Análises de BI avançadas\n"
                             "- Relatórios personalizados\n\n"
                             "💡 Para ativar todas as funcionalidades, configure as variáveis de ambiente no Streamlit Cloud."
                }
            elif "gráfico" in prompt.lower() or "chart" in prompt.lower():
                # Gerar dados de exemplo
                sample_data = {
                    "Mês": ["Jan", "Feb", "Mar", "Apr", "May"],
                    "Vendas": [100, 150, 130, 200, 180]
                }
                response_content = {
                    "type": "chart",
                    "content": "📈 Gráfico de exemplo gerado!",
                    "description": "Exemplo de dados de vendas mensais",
                    "chart_data": sample_data
                }
            else:
                response_content = {
                    "type": "text",
                    "content": f"🤖 Recebi sua pergunta: '{prompt}'\n\n"
                             "Esta é uma versão demonstrativa do Agent_BI que está funcionando na nuvem! 🌤️\n\n"
                             "💡 Posso ajudar com:\n"
                             "- Análises de dados\n"
                             "- Geração de gráficos\n"
                             "- Relatórios de BI\n"
                             "- Consultas em linguagem natural\n\n"
                             "Para uma demonstração, tente perguntar sobre 'dados' ou 'gráficos'!"
                }

            st.write(response_content.get("content", "Resposta processada"))

            # Se for um gráfico, mostrar os dados
            if response_content.get("type") == "chart" and "chart_data" in response_content:
                df = pd.DataFrame(response_content["chart_data"])
                st.dataframe(df)
                st.bar_chart(df.set_index("Mês"))

    # Adicionar resposta do assistente
    assistant_message = {
        "role": "assistant",
        "content": response_content
    }
    st.session_state.messages.append(assistant_message)

# --- Status da Aplicação ---
st.markdown("---")
col1, col2, col3 = st.columns(3)

with col1:
    st.metric("🌤️ Status", "Online", delta="Cloud")

with col2:
    st.metric("📝 Mensagens", len(st.session_state.messages))

with col3:
    st.metric("🔑 Sessão", st.session_state.session_id[:8] + "...")

# --- Informações da Versão ---
with st.expander("ℹ️ Informações da Versão"):
    st.markdown("""
    **Agent_BI Cloud Version 1.0**

    🌤️ **Versão Cloud:** Otimizada para Streamlit Cloud
    🔐 **Autenticação:** Sistema simplificado integrado
    📊 **Dados:** Modo demonstrativo ativo
    🤖 **IA:** Respostas simuladas para demonstração

    **Para ativar funcionalidades completas:**
    1. Configure OPENAI_API_KEY nos Secrets
    2. Configure variáveis de banco de dados
    3. A aplicação detectará automaticamente e ativará as funcionalidades

    **Usuários de teste:**
    - admin / admin
    - user / user123
    """)