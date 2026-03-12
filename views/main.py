import streamlit as st
from datetime import datetime
import requests
import base64
import pytz
import json
from streamlit_quill import st_quill

GITHUB_TOKEN = st.secrets["github"]["token"]
REPO_OWNER = "afonsolsj"
REPO_NAME = "LABMICRO"
FILE_PATH = "assets/files/notice_board.json" 
API_URL = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{FILE_PATH}"

def get_post_it_content():
    response = requests.get(API_URL, headers={"Authorization": f"token {GITHUB_TOKEN}"})
    if response.status_code == 200:
        content = response.json()
        decoded = base64.b64decode(content['content']).decode('utf-8')
        try:
            return json.loads(decoded), content['sha']
        except:
            return [], content['sha']
    return [], None
def update_github(data_list, sha):
    json_string = json.dumps(data_list, indent=4, ensure_ascii=False)
    content_encoded = base64.b64encode(json_string.encode('utf-8')).decode('utf-8')
    payload = {
        "message": "Atualizando mural",
        "content": content_encoded,
        "sha": sha
    }
    response = requests.put(API_URL, json=payload, headers={"Authorization": f"token {GITHUB_TOKEN}"})
    return response.status_code in [200, 201]
def get_fortaleza_time():
    fuso = pytz.timezone('America/Fortaleza')
    return datetime.now(fuso).strftime("%d/%m/%Y %H:%M")

st.title("Estagiários Lab Microbiologia")
col1, col2 = st.columns([1, 2.5])
with col1:
    st.markdown(f"Bem-vindo, **{st.session_state.username}** 👋")
    if st.button("Compilação de amostras", use_container_width=True):
        st.switch_page("views/process_samples.py")
    if st.button("Remoção de duplicatas", use_container_width=True):
        st.switch_page("views/remove_duplicate.py")
with col2:
    if "adding_new" not in st.session_state:
        st.session_state.adding_new = False
    c_titulo, c_acoes = st.columns([1.5, 10]) 
    with c_titulo:
        st.markdown('📌 **Mural de avisos**')
    avisos, sha = get_post_it_content()
    btn_save = False
    btn_cancel = False
    btn_add = False
    with c_acoes:
        if not st.session_state.adding_new:
            if st.button("➕", use_container_width=True):
                st.session_state.adding_new = True
                st.rerun()
        else:
            c_save_col, c_cancel_col = st.columns(2)
            with c_save_col:
                btn_save = st.button("💾", use_container_width=True)
            with c_cancel_col:
                btn_cancel = st.button("❌", use_container_width=True)
    if st.session_state.adding_new:
        with st.spinner("Carregando editor..."):
            new_entry = st_quill(placeholder="Escreva o aviso aqui...", html=True, key="quill_editor")
        if btn_save:
            if new_entry and new_entry.replace("<p>", "").replace("</p>", "").replace("<br>", "").strip():
                novo_aviso = {"user": st.session_state.username, "date": get_fortaleza_time(), "text": new_entry}
                avisos.insert(0, novo_aviso)
                if update_github(avisos, sha):
                    st.session_state.adding_new = False
                    st.rerun()
            else:
                st.warning("O aviso não pode estar vazio.")
        if btn_cancel:
            st.session_state.adding_new = False
            st.rerun()
    else:
        with st.container(height=300, border=True):
            if not avisos:
                st.caption("Nenhum aviso no momento.")
            else:
                for i, item in enumerate(avisos):
                    c_text, c_del = st.columns([0.88, 0.12])
                    with c_text:
                        st.markdown(f"**{item['user']}** — *{item['date']}*")
                        st.markdown(item['text'], unsafe_allow_html=True) 
                    with c_del:
                        if st.button("🗑️", key=f"del_{i}"):
                            avisos.pop(i)
                            if update_github(avisos, sha):
                                st.rerun()
                    st.divider()