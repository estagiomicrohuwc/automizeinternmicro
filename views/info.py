import streamlit as st
import pandas as pd
import requests
import base64
from io import StringIO

# Variáveis
github_token = st.secrets["github"]["token"]
repo = "afonsolsj/LABMICRO"
paths = {"departments": "assets/files/departments.csv", "microorganisms_gnb": "assets/files/microorganisms_gnb.csv", "microorganisms_gpb": "assets/files/microorganisms_gpb.csv", "microorganisms_gpc": "assets/files/microorganisms_gpc.csv", "microorganisms_fy": "assets/files/microorganisms_fy.csv", "material_general": "assets/files/materials_general.csv", "material_vigilance": "assets/files/materials_vigilance.csv", "material_smear_microscopy": "assets/files/materials_smear_microscopy.csv", "blood_collection": "assets/files/blood_collection.csv", "microorganism_blood_contaminated": "assets/files/microorganism_blood_contaminated.csv", "microorganism_blood_positive": "assets/files/microorganism_blood_positive.csv"}

# Funções
def load_csv_from_github(file_path):
    url = f"https://api.github.com/repos/{repo}/contents/{file_path}"
    headers = {"Authorization": f"token {github_token}"}
    r = requests.get(url, headers=headers)
    if r.status_code != 200:
        st.error(f"Erro ao carregar {file_path}: {r.status_code}")
        return pd.DataFrame(), None
    data = r.json()
    csv_content = base64.b64decode(data["content"]).decode("utf-8")
    return pd.read_csv(StringIO(csv_content)), data["sha"]

def update_csv_on_github(df, file_path, sha):
    url = f"https://api.github.com/repos/{repo}/contents/{file_path}"
    headers = {"Authorization": f"token {github_token}"}
    payload = {
        "message": f"Atualização automática de {file_path} pelo Streamlit",
        "content": base64.b64encode(df.to_csv(index=False).encode()).decode(),
        "sha": sha,
    }
    return requests.put(url, headers=headers, json=payload).status_code == 200

def render_editor(title, path_key, color, key_suffix, icon_selected):
    st.badge(title, icon=icon_selected, color=color)
    df, sha = load_csv_from_github(paths[path_key])
    edited = st.data_editor(df, num_rows="dynamic", width='stretch', key=f"{key_suffix}_editor")
    if st.button(f"🔄 {title}", key=f"save_{key_suffix}"):
        if "Código" in edited.columns:
            edited = edited.sort_values("Código").reset_index(drop=True)
        if update_csv_on_github(edited, paths[path_key], sha):
            st.success("Base de dados atualizada com sucesso!")
        else:
            st.error("Erro ao atualizar base de dados.")

def render_legend_item(badge_text, icon, color, description):
    col1, col2 = st.columns([2, 8], vertical_alignment="center")
    with col1:
        st.badge(badge_text, icon=icon, color=color)
    with col2:
        st.markdown(f'<p style="font-size:14px;">{description}</p>', unsafe_allow_html=True)

# Código principal da página
st.title("Informações")
tab1, tab2, tab3, tab4, tab5 = st.tabs(["Setores", "Materiais", "Microrganismos", "Hemocultura", "Legendas"])
with tab1:
    render_editor("Completo Hospitalar", "departments", "yellow", "department", ":material/home_health:")
with tab2:
    render_editor("Materiais (Geral)", "material_general", "blue", "general", ":material/fluid_med:")
    render_editor("Materiais (Cultura de vigilância)", "material_vigilance", "red", "vigilance", ":material/medication_liquid:")
    render_editor("Materiais (Baciloscopia)", "material_smear_microscopy", "green", "smear",  ":material/hematology:")
with tab3:
    render_editor("Bacilos Gram Negativos", "microorganisms_gnb", "orange", "gnb", ":material/counter_1:")
    render_editor("Cocos Gram Positivos", "microorganisms_gpc", "violet", "gpc", ":material/counter_2:")
    render_editor("Bacilos Gram Positivos", "microorganisms_gpb", "grey", "gpb", ":material/counter_3:")
    render_editor("Levedura", "microorganisms_fy", "yellow", "fy", ":material/counter_4:")
with tab4:
    render_editor("Vias de coleta", "blood_collection", "orange", "blood", ":material/counter_1:")
    render_editor("Microorganismos p/ amostras positivas", "microorganism_blood_positive", "violet", "bloodpos", ":material/counter_2:")
    render_editor("Microorganismos p/ amostras contamidas", "microorganism_blood_contaminated", "grey", "bloodneg", ":material/counter_3:")
with tab5:
    with st.expander("Cores", icon=":material/colors:"):
        render_legend_item("Ambulatório", ":material/check_circle:", "green",
                           "Paciente em ambulatório. Não é necessário verificação.")
        render_legend_item("Vermelho", ":material/skull:", "red",
                           "Óbito do paciente. Não é necessário verificação.")
        render_legend_item("Amarelo", ":material/format_text_wrap:", "yellow",
                           "Valor dependente. É necessário verificação e preenchimento manual.")
        render_legend_item("Vazio", ":material/format_text_overflow:", "blue",
                           "Valor não encontrado. É necessário verificação e preenchimento manual.")
    with st.expander("Desfecho", icon=":material/health_cross:"):
        df1 = pd.DataFrame({"Situação": ["Internação", "Óbito", "Alta", "Transferência"], "Código": [1, 2, 3, 4]})
        st.table(df1.set_index("Situação"))
    with st.expander("Cultura de Vigilância", icon=":material/health_cross:"):
        st.badge("Se positivo", icon=":material/check:", color="green")
        df2 = pd.DataFrame({"Tipo": ["Carbapenêmico", "Vancomicina", "Carbapenêmico e Vancomicina"], "Código": [1, 2, 4]})
        st.table(df2.set_index("Tipo"))
        st.badge("Se negativo", icon=":material/block:", color="red")
        df3 = pd.DataFrame({"Tipo": ["Carbapenêmico", "Vancomicina", "Carbapenêmico e Vancomicina"], "Código": [1, 2, 3]})
        st.table(df3.set_index("Tipo"))
    with st.expander("Baciloscopia", icon=":material/health_cross:"):
        st.badge("Se positivo", icon=":material/check:", color="green")
        df4 = pd.DataFrame({"Tipo": ["(+++)", "(++)", "(+)", "Presença abaixo de..."], "Código": [4, 3, 2, 1]})
        st.table(df4.set_index("Tipo"))

