'''
Interface de Usuário (Frontend) para o Agent_BI.
Versão integrada que não depende de API externa.
'''
import streamlit as st
import uuid
import pandas as pd
import logging
from core.auth import login, sessao_expirada

# Importações do backend para integração direta
try:
    from core.graph.graph_builder import GraphBuilder
    from core.config.settings import settings
    from core.llm_adapter import OpenAILLMAdapter
    from core.connectivity.parquet_adapter import ParquetAdapter
    from core.agents.code_gen_agent import CodeGenAgent
    from langchain_core.messages import HumanMessage
    BACKEND_AVAILABLE = True
except Exception as e:
    logging.warning(f"Backend components não disponíveis: {e}")
    BACKEND_AVAILABLE = False

# --- Autenticação ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated or sessao_expirada():
    st.session_state.authenticated = False
    login()
else:
    # --- Configuração da Página ---
    st.set_page_config(page_title="Agent_BI", page_icon="📊", layout="wide")
    st.title("📊 Agent_BI - Assistente Inteligente")

    # --- Inicialização do Backend Integrado ---
    @st.cache_resource
    def initialize_backend():
        """Inicializa os componentes do backend uma única vez"""
        debug_info = []

        # Debug 1: Verificar imports
        debug_info.append(f"BACKEND_AVAILABLE: {BACKEND_AVAILABLE}")
        if not BACKEND_AVAILABLE:
            with st.sidebar:
                st.error("❌ Imports do backend falharam")
                st.write("Componentes não carregados:")
                st.code("LangGraph, OpenAI, ParquetAdapter, etc.")
            return None

        try:
            # Debug 2: Verificar secrets
            api_key = None
            secrets_status = "❌ Falhou"
            try:
                api_key = st.secrets.get("OPENAI_API_KEY")
                if api_key and api_key.startswith("sk-"):
                    secrets_status = "✅ OK"
                    debug_info.append(f"Secrets OpenAI: OK ({api_key[:10]}...)")
                else:
                    debug_info.append(f"Secrets OpenAI: Inválida")
            except Exception as e:
                debug_info.append(f"Secrets erro: {e}")

            # Debug 3: Fallback para settings
            if not api_key or not api_key.startswith("sk-"):
                try:
                    api_key = settings.OPENAI_API_KEY.get_secret_value()
                    debug_info.append(f"Settings OpenAI: OK")
                except Exception as e:
                    debug_info.append(f"Settings erro: {e}")

            if not api_key or not api_key.startswith("sk-"):
                raise ValueError("OPENAI_API_KEY não encontrada em secrets nem settings")

            # Debug 4: Inicializar LLM
            debug_info.append("Inicializando LLM...")
            llm_adapter = OpenAILLMAdapter(api_key=api_key)
            debug_info.append("✅ LLM OK")

            # Debug 5: Inicializar Parquet
            debug_info.append("Inicializando Parquet...")
            parquet_adapter = ParquetAdapter(file_path="data/parquet/admatao.parquet")
            debug_info.append("✅ Parquet OK")

            # Debug 6: Inicializar CodeGen
            debug_info.append("Inicializando CodeGen...")
            code_gen_agent = CodeGenAgent(llm_adapter=llm_adapter)
            debug_info.append("✅ CodeGen OK")

            # Debug 7: Construir Grafo
            debug_info.append("Construindo grafo...")
            graph_builder = GraphBuilder(
                llm_adapter=llm_adapter,
                parquet_adapter=parquet_adapter,
                code_gen_agent=code_gen_agent
            )
            agent_graph = graph_builder.build()
            debug_info.append("✅ Grafo OK")

            debug_info.append("🎉 Backend inicializado com sucesso!")

            return {
                "llm_adapter": llm_adapter,
                "parquet_adapter": parquet_adapter,
                "code_gen_agent": code_gen_agent,
                "agent_graph": agent_graph
            }

        except Exception as e:
            debug_info.append(f"❌ ERRO: {str(e)}")

            # Mostrar debug completo na sidebar
            with st.sidebar:
                st.error("🚨 Backend Error")
                st.write("**Debug Log:**")
                for info in debug_info:
                    if "✅" in info:
                        st.success(info)
                    elif "❌" in info:
                        st.error(info)
                    else:
                        st.info(info)

                st.write("**Erro Completo:**")
                st.code(str(e))

            return None

    # Inicializar backend
    backend_components = initialize_backend()

    # Salvar no session_state para acesso em outras partes
    if backend_components:
        st.session_state.backend_components = backend_components
        with st.sidebar:
            st.success("✅ Backend inicializado!")
    else:
        st.session_state.backend_components = None
        with st.sidebar:
            st.error("❌ Backend falhou")

    # --- Logout Button ---
    with st.sidebar:
        st.write(f"Bem-vindo, {st.session_state.get('username', '')}!")
        if st.button("Logout"):
            st.session_state.authenticated = False
            st.session_state.username = ""
            st.session_state.role = ""
            # Clear chat history on logout
            st.session_state.messages = [
                {
                    "role": "assistant",
                    "content": {
                        "type": "text",
                        "content": "Você foi desconectado. Faça login para continuar."
                    }
                }
            ]
            st.rerun()


    # --- Estado da Sessão ---

    if 'session_id' not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
    if 'messages' not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": {
                    "type": "text",
                    "content": "Olá! Como posso ajudar você com seus dados hoje?"
                }
            }
        ]

    # --- Funções de Interação ---
    def query_backend(user_input: str):
        '''Processa a query diretamente usando o backend integrado.'''
        # 📝 GARANTIR que a pergunta do usuário seja sempre preservada
        user_message = {"role": "user", "content": {"type": "text", "content": user_input}}
        st.session_state.messages.append(user_message)

        with st.spinner("O agente está a pensar..."):
            try:
                if not backend_components or not backend_components.get("agent_graph"):
                    # Fallback: resposta simples se backend não disponível
                    agent_response = {
                        "type": "text",
                        "content": f"⚠️ Backend não disponível. Pergunta recebida: '{user_input}'\n\nPor favor, configure a chave OPENAI_API_KEY nos secrets do Streamlit Cloud para ativar todas as funcionalidades.",
                        "user_query": user_input
                    }
                else:
                    # Usar backend integrado (similar ao main.py)
                    initial_state = {"messages": [HumanMessage(content=user_input)]}
                    final_state = backend_components["agent_graph"].invoke(initial_state)
                    agent_response = final_state.get("final_response", {})

                    # Garantir que a resposta inclui informações da pergunta
                    if "user_query" not in agent_response:
                        agent_response["user_query"] = user_input

                # ✅ GARANTIR estrutura correta da resposta
                assistant_message = {"role": "assistant", "content": agent_response}
                st.session_state.messages.append(assistant_message)

                # 🔍 LOG da resposta (removido print para evitar problemas de encoding)
                # print(f"AGENT RESPONSE ADDED: Type={agent_response.get('type', 'unknown')} - Total messages: {len(st.session_state.messages)}")

            except Exception as e:
                # Tratamento de erro local
                error_content = {
                    "type": "error",
                    "content": f"❌ Erro ao processar consulta: {str(e)}\n\nVerifique se a chave OPENAI_API_KEY está configurada corretamente nos secrets."
                }
                st.session_state.messages.append({"role": "assistant", "content": error_content})

        st.rerun()

    # --- Renderização da Interface ---
    # 🔍 DEBUG: Mostrar histórico de mensagens na sidebar (apenas para desenvolvimento)
    with st.sidebar:
        st.write(f"**Total de mensagens:** {len(st.session_state.messages)}")
        if st.checkbox("Mostrar histórico debug"):
            for i, msg in enumerate(st.session_state.messages):
                st.write(f"**{i+1}. {msg['role'].title()}:**")
                content_preview = str(msg.get('content', {}))[:100] + "..." if len(str(msg.get('content', {}))) > 100 else str(msg.get('content', {}))
                st.write(f"{content_preview}")

    # 💬 RENDERIZAR histórico de conversas
    for i, msg in enumerate(st.session_state.messages):
        try:
            with st.chat_message(msg["role"]):
                response_data = msg.get("content", {})

                # ✅ Garantir que response_data seja um dicionário
                if not isinstance(response_data, dict):
                    response_data = {"type": "text", "content": str(response_data)}

                response_type = response_data.get("type", "text")
                content = response_data.get("content", "Conteúdo não disponível")

            # 🔍 DEBUG: Log de renderização (removido print para evitar problemas)
            # if msg["role"] == "user":
            #     print(f"RENDERING USER MSG {i+1}: '{content}'")
            # else:
            #     print(f"RENDERING ASSISTANT MSG {i+1}: Type={response_type}")
            
            # 📈 RENDERIZAR GRÁFICOS
            if response_type == "chart":
                import json
                import plotly.graph_objects as go

                # 📝 Mostrar contexto da pergunta que gerou o gráfico
                user_query = response_data.get("user_query")
                if user_query:
                    st.caption(f"📝 Pergunta: {user_query}")

                try:
                    if isinstance(content, str):
                        # Se content é string JSON, parse para objeto
                        chart_data = json.loads(content)
                    else:
                        # Se content já é dict, usa diretamente
                        chart_data = content

                    # Cria figura Plotly a partir do JSON
                    fig = go.Figure(chart_data)
                    st.plotly_chart(fig, use_container_width=True)
                    st.success("✅ Gráfico gerado com sucesso!")
                except Exception as e:
                    st.error(f"Erro ao renderizar gráfico: {e}")
                    st.write("Dados do gráfico:", content)
            elif response_type == "data" and isinstance(content, list):
                # 📝 Mostrar contexto da pergunta que gerou os dados
                user_query = response_data.get("user_query")
                if user_query:
                    st.caption(f"📝 Pergunta: {user_query}")

                if content:
                    st.dataframe(pd.DataFrame(content))
                    st.info(f"📊 {len(content)} registros encontrados")
                else:
                    st.warning("⚠️ Nenhum dado encontrado para a consulta.")
            elif response_type == "clarification":
                st.markdown(content.get("message"))
                choices = content.get("choices", {})
                for choice_category, choice_list in choices.items():
                    for choice in choice_list:
                        if st.button(choice, key=f"btn_{choice}_{uuid.uuid4()}"):
                            query_backend(choice)
            else:
                # 📝 Para respostas de texto, também mostrar contexto se disponível
                user_query = response_data.get("user_query")
                if user_query and msg["role"] == "assistant":
                    st.caption(f"📝 Pergunta: {user_query}")

                st.write(content)

        except Exception as e:
            # ❌ Tratamento de erro na renderização
            st.error(f"Erro ao renderizar mensagem {i+1}: {str(e)}")
            st.write(f"Dados da mensagem: {msg}")

    if prompt := st.chat_input("Faça sua pergunta..."):
        query_backend(prompt)
