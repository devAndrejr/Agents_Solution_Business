"""
Versão simplificada da autenticação para funcionar no Streamlit Cloud
sem dependência de SQL Server local.
"""
import streamlit as st
import time
import logging
import hashlib

logger = logging.getLogger(__name__)

# Usuários hardcoded para funcionar na nuvem
USERS_DB = {
    "admin": {
        "password_hash": "8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918",  # "admin"
        "role": "admin"
    },
    "user": {
        "password_hash": "04f8996da763b7a969b1028ee3007569eaf3a635486ddab211d512c85b9df8fb",  # "user123"
        "role": "user"
    }
}

def hash_password(password: str) -> str:
    """Gera hash SHA256 da senha"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_credentials(username: str, password: str) -> tuple[bool, str]:
    """Verifica credenciais do usuário"""
    if username in USERS_DB:
        password_hash = hash_password(password)
        if USERS_DB[username]["password_hash"] == password_hash:
            return True, USERS_DB[username]["role"]
    return False, ""

def sessao_expirada() -> bool:
    """Verifica se a sessão expirou (4 horas)"""
    if "login_time" in st.session_state:
        return time.time() - st.session_state.login_time > 14400  # 4 horas
    return True

def login():
    """Interface de login simplificada"""
    _, col2, _ = st.columns([1, 2, 1])
    with col2:
        st.markdown(
            """
            <div style='text-align:center;'>
                <h2>🤖 Agent BI</h2>
                <p style='color:#666;'>Acesse com seu usuário e senha para continuar.</p>
            </div>
            """,
            unsafe_allow_html=True
        )

        with st.form("login_form"):
            username = st.text_input("👤 Usuário")
            password = st.text_input("🔒 Senha", type="password")
            submit = st.form_submit_button("🚀 Entrar")

            if submit:
                if username and password:
                    is_valid, role = verify_credentials(username, password)
                    if is_valid:
                        st.session_state.authenticated = True
                        st.session_state.username = username
                        st.session_state.role = role
                        st.session_state.login_time = time.time()
                        logger.info(f"Login bem-sucedido: {username}")
                        st.rerun()
                    else:
                        st.error("❌ Usuário ou senha inválidos!")
                        logger.warning(f"Tentativa de login inválida: {username}")
                else:
                    st.error("⚠️ Preencha todos os campos!")

        st.markdown("---")
        st.info("👤 **Usuários de teste:**\n\n"
                "- admin / admin\n"
                "- user / user123")