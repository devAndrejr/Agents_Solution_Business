'''
Interface de Usuário (Frontend) para o Agent_BI.
Versão integrada que não depende de API externa.
'''
import streamlit as st
import uuid
import pandas as pd
import logging
from core.auth import login, sessao_expirada

# Importações do backend para integração direta - TESTE INDIVIDUAL
import_errors = []
BACKEND_AVAILABLE = True

# Teste cada import individualmente para melhor diagnóstico
try:
    from core.graph.graph_builder import GraphBuilder
except Exception as e:
    import_errors.append(f"GraphBuilder: {e}")
    BACKEND_AVAILABLE = False

try:
    from core.config.settings import settings
except Exception as e:
    import_errors.append(f"Settings: {e}")
    BACKEND_AVAILABLE = False

try:
    from core.llm_adapter import OpenAILLMAdapter
except Exception as e:
    import_errors.append(f"OpenAILLMAdapter: {e}")
    BACKEND_AVAILABLE = False

try:
    from core.connectivity.parquet_adapter import ParquetAdapter
except Exception as e:
    import_errors.append(f"ParquetAdapter: {e}")
    BACKEND_AVAILABLE = False

try:
    from core.agents.code_gen_agent import CodeGenAgent
except Exception as e:
    import_errors.append(f"CodeGenAgent: {e}")
    BACKEND_AVAILABLE = False

try:
    from langchain_core.messages import HumanMessage
except Exception as e:
    import_errors.append(f"LangChain: {e}")
    BACKEND_AVAILABLE = False

if import_errors:
    logging.warning(f"Erros de import detectados: {import_errors}")
else:
    logging.info("Todos os imports do backend foram bem-sucedidos")

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
                st.write("**Erros específicos:**")
                for error in import_errors:
                    st.code(error)
                st.write("**Possíveis soluções:**")
                st.info("1. Verificar requirements.txt\n2. Reinstalar dependências\n3. Verificar Python path")
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
            import os
            parquet_path = os.path.join(os.getcwd(), "data", "parquet", "admmat.parquet")
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
            debug_info.append(f"❌ ERRO: {str(e)}")

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
                    # DEBUG: Verificar estrutura de dados
                    st.write("DEBUG - Response data keys:", list(response_data.keys()))
                    st.write("DEBUG - Content type:", type(content))

                    # Para gráficos chart_data está em response_data['result']['chart_data']
                    if 'result' in response_data and 'chart_data' in response_data['result']:
                        chart_data = response_data['result']['chart_data']
                        st.write("DEBUG - Usando chart_data do result")
                    elif isinstance(content, str):
                        # Se content é string JSON, parse para objeto
                        chart_data = json.loads(content)
                        st.write("DEBUG - Parsed content as JSON")
                    else:
                        # Se content já é dict, usa diretamente
                        chart_data = content
                        st.write("DEBUG - Using content directly")

                    st.write("DEBUG - Chart data:", chart_data)

                    # Criar gráfico melhorado com cores e interatividade
                    chart_type = chart_data.get("type", "bar")
                    x_data = chart_data.get("x", [])
                    y_data = chart_data.get("y", [])
                    colors = chart_data.get("colors", None)

                    st.write(f"DEBUG - X data length: {len(x_data)}")
                    st.write(f"DEBUG - Y data length: {len(y_data)}")
                    st.write(f"DEBUG - X data: {x_data}")
                    st.write(f"DEBUG - Y data: {y_data}")

                    if chart_type == "bar":
                        # Gráfico de barras com melhorias visuais
                        fig = go.Figure()

                        # Adicionar barras com cores personalizadas
                        fig.add_trace(go.Bar(
                            x=x_data,
                            y=y_data,
                            marker_color=colors if colors else '#1f77b4',
                            text=[f'{int(val):,}' for val in y_data],  # Rótulos de dados formatados
                            textposition='outside',
                            name='Vendas',
                            hovertemplate='<b>%{x}</b><br>Vendas: %{y:,.0f}<extra></extra>'
                        ))

                        # Configurações de layout melhoradas
                        height = chart_data.get("height", 500)
                        margin = chart_data.get("margin", {"l": 60, "r": 60, "t": 80, "b": 100})

                        fig.update_layout(
                            title={
                                'text': response_data.get("title", "Gráfico"),
                                'x': 0.5,
                                'xanchor': 'center',
                                'font': {'size': 16, 'family': 'Arial Black'}
                            },
                            xaxis_title="UNE",
                            yaxis_title="Vendas",
                            height=height,
                            margin=margin,
                            showlegend=False,
                            plot_bgcolor='rgba(0,0,0,0)',
                            xaxis={'tickangle': -45, 'tickfont': {'size': 10}},
                            yaxis={'tickformat': ',.0f'}
                        )

                        # Adicionar interatividade personalizada
                        fig.update_traces(
                            hoverinfo='text+y',
                            hoverlabel=dict(bgcolor="white", font_size=12, font_family="Arial")
                        )

                    else:
                        # Fallback para outros tipos de gráfico
                        fig = go.Figure(chart_data)

                    # Renderizar gráfico
                    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': True})

                    # Mostrar informações adicionais
                    result_info = response_data.get("result", {})
                    if "total_unes" in result_info:
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Total de UNEs", result_info.get("total_unes", 0))
                        with col2:
                            st.metric("UNEs Exibidas", result_info.get("unes_exibidas", 0))
                        with col3:
                            st.metric("Total de Vendas", f"{result_info.get('total_vendas', 0):,.0f}")

                    # Interatividade: botões para drill-down por UNE (se aplicável)
                    if "produto_codigo" in result_info and result_info.get("total_unes", 0) > 1:
                        st.write("🔍 **Análise Detalhada por UNE:**")
                        st.info("💡 **Dica:** Para ver vendas mensais de uma UNE específica, pergunte: 'gráfico de barras do produto [código] na une [número]'")

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
