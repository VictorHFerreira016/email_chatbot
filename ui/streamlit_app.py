import streamlit as st
import requests

API_URL = "http://localhost:8000"

st.set_page_config(
    page_title="AI Email Intelligence",
    page_icon="📧",
    layout="wide"
)

def process_emails():
    try:
        response = requests.post(f"{API_URL}/emails/process/")
        return response.json()
    except Exception as e:
        return {"error": str(e)}

def get_all_emails():
    try:
        response = requests.get(f"{API_URL}/emails/")
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, dict) and "emails" in data:
                return data["emails"]
            return data
        else:
            error_data = response.json()
            return {"error": error_data.get("detail", f"Erro {response.status_code}")}
    except Exception as e:
        return {"error": str(e)}

def get_stats():
    try:
        response = requests.get(f"{API_URL}/emails/stats")
        return response.json()
    except Exception as e:
        return {"error": str(e)}

def get_by_category(category):
    try:
        response = requests.get(f"{API_URL}/emails/category/{category}")
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, dict) and "emails" in data:
                return data["emails"]
            return data
        else:
            error_data = response.json()
            return {"error": error_data.get("detail", f"Erro {response.status_code}")}
    except Exception as e:
        return {"error": str(e)}

def send_chat_message(message: str, history: list = []):
    """Send a message to the chatbot"""
    try:
        response = requests.post(
            f"{API_URL}/chat/",
            json={
                "message": message, 
                "history": history
            }
        )
        if response.status_code == 200:
            return response.json()["response"]
        else:
            return f"Error: {response.status_code}"
    except Exception as e:
        return f"Error to connect: {str(e)}"

st.title("📧 AI Email Intelligence Dashboard")
st.markdown("---")

with st.sidebar:
    st.header("⚙️ Controles")

    if st.button(
        "🔄 Processar E-mails", 
        use_container_width=True
    ):
        with st.spinner("Processando..."):
            result = process_emails()

            if "error" in result:
                st.error(result["error"])
            else:
                st.success(f"{result['processed']} e-mails processados!")

        st.rerun()

tab1, tab2, tab3 = st.tabs(["💬 Chat com IA", "📂 Todos E-mails", "🏷️ Por Categoria"])

with tab1:
    st.header("💬 Converse com seu Assistente de E-mails")
    
    st.markdown("""
    **Pergunte coisas como:**
    - "Tenho reuniões marcadas?"
    - "Mostre os boletos pendentes"
    - "E-mails importantes hoje"
    - "Marque uma reunião para amanhã às 14h sobre revisão do projeto"
    """)
    
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
    
    prompt = st.chat_input("Digite sua pergunta...")

    if prompt:
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)
        with st.chat_message("assistant"):
            with st.spinner("Pensando..."):
                response = send_chat_message(prompt, st.session_state.chat_history[:-1])
                st.write(response)
        
        st.session_state.chat_history.append({"role": "assistant", "content": response})

with tab2:
    data = get_all_emails()

    if isinstance(data, list):
        if len(data) == 0:
            st.info("Nenhum e-mail processado ainda.")
        else:
            for email in data:
                with st.expander(f"📧 {email.get('subject', 'Sem assunto')}"):
                    st.caption(f"**De:** {email.get('sender')} | **Data:** {email.get('date')}")
                    st.write(f"**Categoria:** {email.get('categoria')} | **Prioridade:** {email.get('prioridade')}")
                    st.write(f"**Resumo:** {email.get('resumo')}")
                    if email.get('data_reuniao'):
                        st.info(f"📅 Reunião: {email.get('data_reuniao')}")
                    if email.get('valor_boleto'):
                        st.warning(f"💰 Valor: {email.get('valor_boleto')}")

    elif isinstance(data, dict) and "error" in data:
        st.error(data["error"])

with tab3:
    category = st.selectbox("Selecione a categoria", ["reuniao", "boleto", "pessoal", "promocao"])
    data = get_by_category(category)

    if isinstance(data, dict) and "error" in data:
        st.error(data["error"])
    elif isinstance(data, list):
        if len(data) == 0:
            st.info(f"Nenhum e-mail na categoria '{category}'.")
        else:
            for email in data:
                with st.expander(f"📧 {email.get('subject', 'Sem assunto')}"):
                    st.caption(f"**De:** {email.get('sender')} | **Data:** {email.get('date')}")
                    st.write(f"**Prioridade:** {email.get('prioridade', 'N/A')}")
                    st.write(f"**Resumo:** {email.get('resumo', 'Sem resumo')}")
                    if email.get('data_reuniao'):
                        st.info(f"📅 {email.get('data_reuniao')}")
                    if email.get('valor_boleto'):
                        st.warning(f"💰 {email.get('valor_boleto')}")