'''
Interface de Usuário (Frontend) para o Agent_BI.
Versão integrada que não depende de API externa.
'''
import streamlit as st
import uuid
import pandas as pd
import logging
from core.auth import login, sessao_expirada

# Importações do backend para integração direta - DIAGNÓSTICO DETALHADO
import_status = {}
BACKEND_AVAILABLE = True

# Testar cada import individualmente para diagnóstico
try:
    from core.config.settings import settings
    import_status["settings"] = "✅ OK"
except Exception as e:
    import_status["settings"] = f"❌ {str(e)}"
    BACKEND_AVAILABLE = False

try:
    from langchain_core.messages import HumanMessage
    import_status["langchain_core"] = "✅ OK"
except Exception as e:
    import_status["langchain_core"] = f"❌ {str(e)}"
    BACKEND_AVAILABLE = False

try:
    from core.llm_adapter import OpenAILLMAdapter
    import_status["llm_adapter"] = "✅ OK"
except Exception as e:
    import_status["llm_adapter"] = f"❌ {str(e)}"
    BACKEND_AVAILABLE = False

try:
    from core.connectivity.parquet_adapter import ParquetAdapter
    import_status["parquet_adapter"] = "✅ OK"
except Exception as e:
    import_status["parquet_adapter"] = f"❌ {str(e)}"
    BACKEND_AVAILABLE = False

try:
    from core.agents.code_gen_agent import CodeGenAgent
    import_status["code_gen_agent"] = "✅ OK"
except Exception as e:
    import_status["code_gen_agent"] = f"❌ {str(e)}"
    BACKEND_AVAILABLE = False

try:
    from core.graph.graph_builder import GraphBuilder
    import_status["graph_builder"] = "✅ OK"
except Exception as e:
    import_status["graph_builder"] = f"❌ {str(e)}"
    BACKEND_AVAILABLE = False

# Log detalhado apenas para debugging
if not BACKEND_AVAILABLE:
    logging.warning("DIAGNÓSTICO DE IMPORTS:")
    for component, status in import_status.items():
        logging.warning(f"  {component}: {status}")

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

        # Debug 1: Verificar imports com detalhes
        debug_info.append(f"BACKEND_AVAILABLE: {BACKEND_AVAILABLE}")
        if not BACKEND_AVAILABLE:
            user_role = st.session_state.get('role', '')
            if user_role == 'admin':
                with st.sidebar:
                    st.error("❌ Imports do backend falharam")
                    st.write("**Diagnóstico detalhado:**")
                    for component, status in import_status.items():
                        if "✅" in status:
                            st.success(f"{component}: {status}")
                        else:
                            st.error(f"{component}: {status}")
            else:
                with st.sidebar:
                    st.error("❌ Sistema temporariamente indisponível")
            return None

        try:
            # Debug 2: Verificar secrets
            api_key = None
            secrets_status = "❌ Falhou"
            try:
                debug_info.append("Tentando acessar st.secrets...")
                api_key = st.secrets.get("OPENAI_API_KEY")
                if api_key and api_key.startswith("sk-"):
                    secrets_status = "✅ OK"
                    debug_info.append(f"✅ Secrets OpenAI: OK ({api_key[:10]}...)")
                else:
                    debug_info.append(f"❌ Secrets OpenAI: Inválida ou vazia")
                    debug_info.append(f"❌ Valor recebido: {str(api_key)[:20] if api_key else 'None'}")
            except Exception as e:
                debug_info.append(f"❌ Secrets erro: {str(e)}")
                debug_info.append(f"❌ Tipo erro: {type(e).__name__}")

            # Debug 3: Fallback para settings
            if not api_key or not api_key.startswith("sk-"):
                try:
                    debug_info.append("Tentando carregar settings...")
                    api_key = settings.OPENAI_API_KEY.get_secret_value()
                    debug_info.append(f"Settings OpenAI: OK")
                except Exception as e:
                    debug_info.append(f"❌ Settings erro completo: {str(e)}")
                    debug_info.append(f"❌ Tipo do erro: {type(e).__name__}")
                    # Se settings falhar, pode ser problema com variáveis DB obrigatórias

            if not api_key or not api_key.startswith("sk-"):
                debug_info.append("❌ CRITICAL: OPENAI_API_KEY não encontrada")
                debug_info.append("💡 SOLUÇÃO: Configure OPENAI_API_KEY nos secrets do Streamlit Cloud")
                raise ValueError("OPENAI_API_KEY não encontrada em secrets nem settings")

            # Debug 4: Inicializar LLM
            debug_info.append("Inicializando LLM...")
            llm_adapter = OpenAILLMAdapter(api_key=api_key)
            debug_info.append("✅ LLM OK")

            # Debug 5: Inicializar Parquet
            debug_info.append("Inicializando Parquet...")
            import os
            parquet_path = os.path.join(os.getcwd(), "data", "parquet", "admatao.parquet")
            if not os.path.exists(parquet_path):
                # Criar dados mock para cloud se arquivo não existir
                import pandas as pd
                mock_data = pd.DataFrame({
                    'codigo': [59294, 12345, 67890],
                    'descricao': ['Produto Exemplo 1', 'Produto Exemplo 2', 'Produto Exemplo 3'],
                    'preco': [99.90, 149.50, 79.30],
                    'categoria': ['Categoria A', 'Categoria B', 'Categoria A']
                })
                os.makedirs(os.path.dirname(parquet_path), exist_ok=True)
                mock_data.to_parquet(parquet_path)
                debug_info.append("⚠️ Arquivo parquet não encontrado - criado dados mock")
            parquet_adapter = ParquetAdapter(file_path=parquet_path)
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
            debug_info.append(f"❌ ERRO CRÍTICO: {str(e)}")
            debug_info.append(f"❌ Tipo do erro: {type(e).__name__}")
            debug_info.append(f"❌ Linha do erro: {e.__traceback__.tb_lineno if e.__traceback__ else 'unknown'}")

            # Diagnóstico específico para erros comuns
            if "ValidationError" in str(type(e)):
                debug_info.append("💡 CAUSA PROVÁVEL: Variáveis obrigatórias faltando em settings")
            elif "ImportError" in str(type(e)) or "ModuleNotFoundError" in str(type(e)):
                debug_info.append("💡 CAUSA PROVÁVEL: Dependência faltando nos requirements")
            elif "FileNotFoundError" in str(type(e)):
                debug_info.append("💡 CAUSA PROVÁVEL: Arquivo parquet não encontrado")

            # Mostrar debug completo na sidebar APENAS para admins
            user_role = st.session_state.get('role', '')
            if user_role == 'admin':
                with st.sidebar:
                    st.error("🚨 Backend Error (Admin)")
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
            else:
                with st.sidebar:
                    st.error("❌ Sistema temporariamente indisponível")

            return None

    # Inicializar backend
    backend_components = initialize_backend()

    # Salvar no session_state para acesso em outras partes
    if backend_components:
        st.session_state.backend_components = backend_components
        user_role = st.session_state.get('role', '')
        if user_role == 'admin':
            with st.sidebar:
                st.success("✅ Backend inicializado!")
    else:
        st.session_state.backend_components = None
        user_role = st.session_state.get('role', '')
        if user_role == 'admin':
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
                        "content": f"⚠️ Sistema está sendo inicializado. Tente novamente em alguns segundos.\n\nSe o problema persistir, contate o administrador.",
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
