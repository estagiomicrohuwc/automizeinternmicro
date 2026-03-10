import streamlit as st
import pandas as pd
import re
import io
import os
import zipfile
import pdfplumber
import tempfile
import fitz
from pypdf import PdfReader, PdfWriter
from datetime import datetime, timedelta
from xlsxwriter.utility import xl_rowcol_to_cell

# Planilhas auxiliares GitHub
departments_df = pd.read_csv("assets/files/departments.csv")
substitution_departments = dict(zip(departments_df["Unidade/Ambulatório"].str.upper(), departments_df["Código"]))
materials_general_df = pd.read_csv("assets/files/materials_general.csv")
materials_general = dict(zip(materials_general_df["Material"].str.lower(), materials_general_df["Código"]))
materials_vigilance_df = pd.read_csv("assets/files/materials_vigilance.csv")
materials_vigilance = dict(zip(materials_vigilance_df["Material"].str.lower(), materials_vigilance_df["Código"]))
materials_smear_df = pd.read_csv("assets/files/materials_smear_microscopy.csv")
materials_smear_microscopy = dict(zip(materials_smear_df["Material"].str.lower(), materials_smear_df["Código"]))
microorganisms_gnb_df = pd.read_csv("assets/files/microorganisms_gnb.csv")
microorganisms_gnb = dict(zip(microorganisms_gnb_df["Microrganismo"].str.lower(), microorganisms_gnb_df["Código"]))
microorganisms_gpc_df = pd.read_csv("assets/files/microorganisms_gpc.csv")
microorganisms_gpc = dict(zip(microorganisms_gpc_df["Microrganismo"].str.lower(), microorganisms_gpc_df["Código"]))
microorganisms_gpb_df = pd.read_csv("assets/files/microorganisms_gpb.csv")
microorganisms_gpb = dict(zip(microorganisms_gpb_df["Microrganismo"].str.lower(), microorganisms_gpb_df["Código"]))
microorganisms_fy_df = pd.read_csv("assets/files/microorganisms_fy.csv")
microorganisms_fy = dict(zip(microorganisms_fy_df["Microrganismo"].str.lower(), microorganisms_fy_df["Código"]))
microorganism_blood_contaminated_df = pd.read_csv("assets/files/microorganism_blood_contaminated.csv")
microorganism_blood_contaminated = dict(zip(microorganism_blood_contaminated_df["Microrganismo"].str.lower(), microorganism_blood_contaminated_df["Código"]))
microorganism_blood_positive_df = pd.read_csv("assets/files/microorganism_blood_positive.csv")
microorganism_blood_positive = dict(zip(microorganism_blood_positive_df["Microrganismo"].str.lower(), microorganism_blood_positive_df["Código"]))
blood_collection_df = pd.read_csv("assets/files/blood_collection.csv")
blood_collection = dict(zip(blood_collection_df["Sitio"].str.lower(), blood_collection_df["Código"]))

# Destacar pedidos encontrados/não encontrados
def paint_request_pdf(uploaded_file, found_ids, all_ids):
    found_ids_set = set(str(x) for x in found_ids)
    all_ids_set = set(str(x) for x in all_ids)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_input:
        tmp_input.write(uploaded_file.getbuffer())
        tmp_input_path = tmp_input.name
    output_path = tmp_input_path.replace(".pdf", "_out.pdf")
    try:
        doc = fitz.open(tmp_input_path)
        for page in doc:
            page_width = page.rect.width
            words = page.get_text("words") 
            for w in words:
                word_text = w[4].strip()
                if word_text in all_ids_set:
                    inst_rect = fitz.Rect(w[0], w[1], w[2], w[3])
                    line_rect = fitz.Rect(0, inst_rect.y0, page_width, inst_rect.y1)  
                    color = (0.7, 1, 0.7) if word_text in found_ids_set else (1, 0.7, 0.7)  
                    annot = page.add_highlight_annot(line_rect)
                    annot.set_colors(stroke=color)
                    annot.update()
        doc.save(output_path, garbage=4, deflate=True)
        doc.close()
        with open(output_path, "rb") as f:
            final_bytes = f.read()
        return final_bytes
    finally:
        if os.path.exists(tmp_input_path): os.remove(tmp_input_path)
        if os.path.exists(output_path): os.remove(output_path)

# Planilhas para download
df_general = pd.DataFrame(columns=st.secrets["columns"]["general"]); df_general.name = "general"
df_vigilance = pd.DataFrame(columns=st.secrets["columns"]["vigilance"]); df_vigilance.name = "vigilance"
df_smear = pd.DataFrame(columns=st.secrets["columns"]["smear_microscopy"]); df_smear.name = "smear"

# Função de estilização/download
def style_download(df_geral, df_vigilancia, df_baciloscopia, df_blood, pdf_report=None, nome_arquivo_zip="relatorios_processados.zip"):
    try:
        zip_buffer = io.BytesIO()
        dfs_para_exportar = {"Geral.xlsx": df_geral, "Vigilancia.xlsx": df_vigilancia, "Baciloscopia.xlsx": df_baciloscopia, "Hemocultura.xlsx": df_blood}
        cols_required = ["record_id", "id","hospital", "hospital_de_origem", "n_mero_do_pedido", "n_mero_do_prontu_rio", "sexo", "idade", "idade_anos", "data_da_entrada", "setor_de_origem", "tipo_de_material", "qual_tipo_de_material", "data_da_libera_o", "resultado", "data_agora", "formulrio_complete"]
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for nome_arquivo_excel, df in dfs_para_exportar.items():
                if df is None or df.empty:
                    continue
                excel_buffer = io.BytesIO()
                with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
                    nome_aba = "Dados"
                    df.to_excel(writer, sheet_name=nome_aba, index=False)
                    workbook = writer.book
                    worksheet = writer.sheets[nome_aba]
                    blue_format = workbook.add_format({'bg_color': '#DDEBF7'})
                    green_format = workbook.add_format({'bg_color': '#C6EFCE'})
                    red_format = workbook.add_format({'bg_color': '#FFC7CE'})
                    yellow_format = workbook.add_format({'bg_color': '#FFEB9C'})
                    max_row = len(df)
                    if max_row == 0:
                        continue
                    for col in cols_required:
                        if col in df.columns:
                            col_idx = df.columns.get_loc(col)
                            worksheet.conditional_format(1, col_idx, max_row, col_idx, {'type': 'blanks', 'format': blue_format})
                    if "desfecho_do_paciente" in df.columns:
                        col_idx = df.columns.get_loc("desfecho_do_paciente")
                        cell_range = (1, col_idx, max_row, col_idx)
                        worksheet.conditional_format(*cell_range, {'type': 'cell', 'criteria': '==', 'value': "2", 'format': red_format})
                        worksheet.conditional_format(*cell_range, {'type': 'cell', 'criteria': '==', 'value': "3", 'format': green_format})
                        worksheet.conditional_format(*cell_range, {'type': 'blanks', 'format': blue_format})
                        worksheet.conditional_format(*cell_range, {'type': 'no_blanks', 'format': yellow_format})
                    if "qual_o_tipo_de_microorganismo" in df.columns and "qual_microorganismo" in df.columns:
                        col_target = df.columns.get_loc("qual_o_tipo_de_microorganismo")
                        col_check = df.columns.get_loc("qual_microorganismo")
                        cell_range = (1, col_target, max_row, col_target)
                        ref_target = xl_rowcol_to_cell(1, col_target, row_abs=False, col_abs=False)
                        ref_check = xl_rowcol_to_cell(1, col_check, row_abs=False, col_abs=True)
                        formula = f'=AND({ref_check}=29, ISBLANK({ref_target}))'
                        worksheet.conditional_format(*cell_range, {'type': 'formula', 'criteria': formula, 'format': blue_format})
                    if "qual_microorganismo" in df.columns:
                        col_idx = df.columns.get_loc("qual_microorganismo")
                        cell_range = (1, col_idx, max_row, col_idx)
                        worksheet.conditional_format(*cell_range, {'type': 'cell', 'criteria': '==', 'value': '29', 'format': yellow_format})
                    if "setor_de_origem" in df.columns:
                        col_idx = df.columns.get_loc("setor_de_origem")
                        cell_range = (1, col_idx, max_row, col_idx)
                        first_cell = xl_rowcol_to_cell(1, col_idx)
                        worksheet.conditional_format(*cell_range, {'type': 'formula', 'criteria': f'=ISTEXT({first_cell})', 'format': yellow_format})
                    if "setor_origem" in df.columns:
                        col_idx = df.columns.get_loc("setor_origem")
                        cell_range = (1, col_idx, max_row, col_idx)
                        first_cell = xl_rowcol_to_cell(1, col_idx)
                        worksheet.conditional_format(*cell_range, {'type': 'formula', 'criteria': f'=ISTEXT({first_cell})', 'format': yellow_format})
                    if "tipo_de_material" in df.columns:
                        col_idx = df.columns.get_loc("tipo_de_material")
                        cell_range = (1, col_idx, max_row, col_idx)
                        worksheet.conditional_format(*cell_range, {'type': 'cell', 'criteria': '==', 'value': '15', 'format': yellow_format})
                    if "qual_tipo_de_material" in df.columns:
                        col_idx = df.columns.get_loc("qual_tipo_de_material")
                        cell_range = (1, col_idx, max_row, col_idx)
                        worksheet.conditional_format(*cell_range, {'type': 'cell', 'criteria': '==', 'value': '10', 'format': yellow_format})
                    tem_agente = "se_positivo_para_qual_agente" in df.columns
                    tem_marque = "se_positivo_marque" in df.columns
                    if "resultado" in df.columns and (tem_agente or tem_marque):
                        col_res = df.columns.get_loc("resultado")
                        nome_col_agente = "se_positivo_para_qual_agente" if tem_agente else "se_positivo_marque"
                        col_agente = df.columns.get_loc(nome_col_agente)
                        cell_range = (1, col_agente, max_row, col_agente) 
                        ref_resultado = xl_rowcol_to_cell(1, col_res, row_abs=False, col_abs=True)
                        ref_agente = xl_rowcol_to_cell(1, col_agente, row_abs=False, col_abs=False)
                        formula = f'=AND({ref_resultado}=1, ISBLANK({ref_agente}))'
                        worksheet.conditional_format(*cell_range, {'type': 'formula', 'criteria': formula, 'format': blue_format})
                excel_buffer.seek(0)
                zip_file.writestr(nome_arquivo_excel, excel_buffer.getvalue())
            if pdf_report:
                zip_file.writestr("Relatório de pedidos.pdf", pdf_report)
        zip_buffer.seek(0)
        st.download_button(label="Baixar (.zip)", data=zip_buffer,
                           file_name=nome_arquivo_zip, mime="application/zip")
    except Exception as e:
        st.error(f"Ocorreu um erro inesperado ao gerar o arquivo .zip: {e}")
        st.exception(e)

# Função de comparação
def compare_data(dfs, substitution_dict, materials_dicts, setor_col="setor_de_origem", microorganisms_gnb=microorganisms_gnb, microorganisms_gpc=microorganisms_gpc, microorganisms_fy=microorganisms_fy, microorganisms_gpb=microorganisms_gpb):
    all_microorganisms = {}
    all_microorganisms.update(microorganisms_gnb)
    all_microorganisms.update(microorganisms_gpc)
    all_microorganisms.update(microorganisms_fy)
    all_microorganisms.update(microorganisms_gpb)
    for df in dfs:
        if setor_col in df.columns:
            df[setor_col] = df[setor_col].str.upper().map(substitution_dict).fillna(df[setor_col])
        if df is df_general and "qual_tipo_de_material" in df.columns:
            mat_col = "qual_tipo_de_material"
            outro_col = "outro_tipo_de_material"
            default_val = 10
            for idx, val in df[mat_col].items():
                val_norm = str(val).strip().upper()
                mapped = {k.strip().upper(): v for k, v in materials_dicts["df_general"].items()}.get(val_norm)
                if mapped is not None:
                    df.at[idx, mat_col] = mapped
                else:
                    if pd.notna(val) and str(val).strip() != "":
                        df.at[idx, outro_col] = val
                        df.at[idx, mat_col] = default_val
        elif df is df_vigilance and "qual_tipo_de_material" in df.columns:
            mat_col = "qual_tipo_de_material"
            outro_col = "outro_tipo_de_material"
            default_val = 2
            for idx, val in df[mat_col].items():
                val_norm = str(val).strip().upper()
                mapped = {k.strip().upper(): v for k, v in materials_dicts["df_vigilance"].items()}.get(val_norm)
                if mapped is not None:
                    df.at[idx, mat_col] = mapped
                else:
                    if pd.notna(val) and str(val).strip() != "":
                        df.at[idx, outro_col] = val
                        df.at[idx, mat_col] = default_val
        elif df is df_smear and "tipo_de_material" in df.columns:
            mat_col = "tipo_de_material"
            outro_col = "se_outro_material"
            default_val = 15
            for idx, val in df[mat_col].items():
                val_norm = str(val).strip().upper()
                mapped = {k.strip().upper(): v for k, v in materials_dicts["df_smear"].items()}.get(val_norm)
                if mapped is not None:
                    df.at[idx, mat_col] = mapped
                else:
                    if pd.notna(val) and str(val).strip() != "":
                        df.at[idx, outro_col] = val
                        df.at[idx, mat_col] = default_val
        if "qual_microorganismo" in df.columns:
                    micro_col = "qual_microorganismo"
                    for idx, val in df[micro_col].items():
                        val_norm = str(val).strip().lower()
                        if not val_norm:
                            continue
                        if val_norm in all_microorganisms:
                            code = all_microorganisms[val_norm]
                            df.at[idx, micro_col] = code
        if "qual_microorganismo" in df.columns:
            df["qual_microorganismo"] = df["qual_microorganismo"].astype(str).str.strip()
            df.loc[df["qual_microorganismo"] == "Outro", "qual_microorganismo"] = 29
            convertido = pd.to_numeric(df["qual_microorganismo"], errors='coerce')
            mascara_texto = (convertido.isna() & df["qual_microorganismo"].notna() & (df["qual_microorganismo"] != "") & (df["qual_microorganismo"] != "nan"))
            df.loc[mascara_texto, "outro_microorganismo"] = df.loc[mascara_texto, "qual_microorganismo"]
            df.loc[mascara_texto, "qual_microorganismo"] = 29
            df["qual_microorganismo"] = pd.to_numeric(df["qual_microorganismo"], errors='coerce')
            df["qual_microorganismo"] = df["qual_microorganismo"].astype("Int64")
    return dfs

# Função de desfecho
def fill_outcome(pdf_file, dfs, column_name_search="column_aux1", col_date1="column_aux2", col_date2="column_aux3", col_outcome="desfecho_do_paciente", col_setor="setor_de_origem"):
    text = extract_text_pdf(pdf_file)
    if not text:
        return dfs
    lines = text.splitlines()
    for df in dfs:
        if col_outcome not in df.columns:
            df[col_outcome] = ""
        df[col_outcome] = 3
        for idx, row in df.iterrows():
            patient_name = str(row[column_name_search]).strip()
            if patient_name:
                for line in lines:
                    if re.search(r"\bO\s+" + re.escape(patient_name) + r"\b", line):
                        df.at[idx, col_outcome] = 2
                        break
        for col in [column_name_search, col_date1, col_date2]:
            if col in df.columns:
                df.drop(columns=[col], inplace=True)
    return dfs

# Funções de preenchimento
def get_next_id(df, start_id, column_name):
    if df.empty or df[column_name].dropna().empty:
        return start_id
    max_val = df[column_name].max()
    if pd.isna(max_val):
        return start_id
    return int(max_val) + 1
def extract_fields_positive(report_text, df_name):
    report_lower = report_text.lower()
    if df_name == "vigilance":
        def if_positive(report_lower):
            has_carbapenemicos = "carbapenêmico" in report_lower
            has_vancomicina = "vancomicina" in report_lower
            if has_carbapenemicos and has_vancomicina:
                return 4
            elif has_carbapenemicos:
                return 1
            elif has_vancomicina:
                return 2
            else:
                return ""
        return {"resultado": 1,
                "se_positivo_para_qual_agente": if_positive(report_lower),
                "se_negativo_para_qual_agente": ""}
    elif df_name == "smear":
        def if_positive(report_lower):
            if "+++" in report_lower:
                return 4
            elif "++" in report_lower:
                return 3
            elif "+" in report_lower:
                return 2
            elif "em 100 campos examinados" in report_lower:
                return 1
            elif "positivo" in report_lower:
                return 1
            else:
                ""
        return {"resultado": 1,
                "se_positivo_marque": if_positive(report_lower)}
    elif df_name == "general":
        def get_value(label):
            idx = report_lower.find(label.lower())
            if idx != -1:
                end = report_lower.find("\n", idx)
                if end == -1:
                    end = len(report_lower)
                line = report_text[idx:end]
                value = line.split(":", 1)[-1].strip()
                return value
            return ""
        def classify_microorganism(value):
            if not value:
                return ""
            first_word_input = value.strip().split()[0].lower()
            groups = [(microorganisms_gpc, 0), (microorganisms_gnb, 1), (microorganisms_fy, 2), (microorganisms_gpb, 3)]
            for dic, code in groups:
                for item in dic:
                    if not item: continue
                    first_word_dict = item.strip().split()[0].lower()
                    if first_word_input == first_word_dict:
                        return code     
            return ""
        def get_mechanism(oxacilina, meropenem, imipenem, ertapenem, vancomicina, micro_final):
            if "(pos)" in get_value("esbl"):
                return 1, ""
            elif "Staphylococcus aureus" in micro_final and oxacilina == 2:
                return 3, ""
            elif "Acinetobacter baumanni" in micro_final and (meropenem == 2 or imipenem == 2):
                return 10, ""
            elif "Enterococcus faecalis" in micro_final and vancomicina == 2:
                return 4, ""
            elif "Enterococcus faecium" in micro_final and vancomicina == 2:
                return 7, ""
            elif "Pseudomonas aeruginosa" in micro_final and (meropenem == 2 or ertapenem == 2):
                return 6, ""
            elif "Pseudomonas" in micro_final and "aeruginosa" not in micro_final and (meropenem == 2 or ertapenem == 2):
                return 8, ""
            elif any(x in micro_final for x in ["Escherichia", "Klebsiella", "Enterobacter", "Proteus", "Serratia", "Citrobacter", "Morganella", "Providencia", "Hafnia", "Raoultella"]) and (meropenem == 2 or imipenem == 2):
                return 2, ""
            elif any(x in report_lower for x in ["enzimas", "triagem", "intrinseca", "spm-1"]):
                termos = [x for x in ["enzimas", "triagem", "intrinseca", "spm-1"] if x in report_lower]
                return 5, termos
            elif not any(x in micro_final for x in ["Escherichia", "Klebsiella", "Enterobacter", "Proteus", "Serratia", "Citrobacter", "Morganella", "Providencia", "Hafnia", "Raoultella"]) and (meropenem == 2 or imipenem == 2):
                return 9, ""
            else:
                return "", ""
        def apresenta_gene_resistencia(report_lower):
            if "kpc" in text and "ndm" in report_lower:
                return 10
            elif "kpc" in text and "imp" in report_lower:
                return 9
            elif "ndm" in text and "imp" in report_lower:
                return 11
            elif "kpc" in text and "vim" in report_lower:
                return 13
            elif "ndm" in text and "vim" in report_lower:
                return 14
            elif "imp" in text and "vim" in report_lower:
                return 15
            elif "kpc" in text and "oxa" in report_lower:
                return 16
            elif "oxa" in text and "imp" in report_lower:
                return 17
            elif "oxa" in text and "vim" in report_lower:
                return 18
            elif "ndm" in text and "oxa" in report_lower:
                return 19
            elif "enzimático não detectado" in report_lower:
                return 8
            elif "ndm" in report_lower:
                return 6
            elif "vim" in report_lower:
                return 5
            elif "imp" in report_lower:
                return 4
            elif "oxa" in report_lower:
                return 3
            elif "kpc" in report_lower:
                return 2
            elif "não enzimático" in report_lower:
                return 1
            else:
                return ""
        def get_cim_result(report_lower, micro_final):
            text = report_lower.lower().replace("\n", " ")
            mcim = ""
            ecim = ""
            tem_mcim = "mcim" in text
            if re.search(r'\bmcim\b.*?positivo', text):
                mcim = 1
            elif re.search(r'\bmcim\b.*?negativo', text):
                mcim = 2
            if tem_mcim and "pseudomonas aeruginosa" in micro_final.lower():
                ecim = 3
            else:
                if re.search(r'\becim\b.*?positivo', text):
                    ecim = 1
                elif re.search(r'\becim\b.*?negativo', text):
                    ecim = 2
            return mcim, ecim
        def result_ast(value):
            if not value:
                return 4, ""
            texto = value.lower()
            status_code = 4
            parts = texto.split()
            if "s" in parts:
                status_code = 1
            elif "r" in parts:
                status_code = 2
            elif "i" in parts:
                status_code = 3
            padrao_mic = r"([<>]?=?\s*\d+([.,]\d+)?)"
            match = re.search(padrao_mic, value)
            if match:
                mic_value = match.group(0).strip()
            else:
                mic_value = ""
            return status_code, mic_value
        def get_gn_hospitalar_values(get_value, result_ast, report_lower, type_micro):
            campos = ["amoxicilina", "aztreonam", "cefiderocol", "ceftalozano/tazobactam", "ceftazidima/avibactam", "ampicilina", "ampicilina/sulbactam", "piperacilina/tazobactam", "cefoxitina", "cefuroxima", "ceftazidima", "cefepima", "ertapenem", "imipenem", "imipenem/relebactam", "levofloxacina", "meropenem", "meropenem/vaborbactam", "amicacina", "gentamicina", "ciprofloxacina", "tigeciclina", "trimetoprim/sulfametozol", "polimixina b", "ceftriaxona"]
            tem_medicamento_hospitalar = "ceftazidima/avibactam" in report_lower
            proc_val = get_value("Procedência.:")
            nao_e_ambulatorio = "AMB" not in (proc_val if proc_val else "")
            eh_hospitalar = (type_micro == 1) and (tem_medicamento_hospitalar or nao_e_ambulatorio)
            if eh_hospitalar:
                valores = [result_ast(get_value(c)) for c in campos]
                if all(v[0] == 4 for v in valores):
                    valores = [("", "")] * len(campos)
                    gram_negativo_gn_hospitala = 2
                else:
                    gram_negativo_gn_hospitala = 1
                return (*valores, gram_negativo_gn_hospitala)
            else:
                valores = [("", "")] * len(campos)
                gram_negativo_gn_hospitala = 2
                return (*valores, gram_negativo_gn_hospitala)
        def get_gn_ambulatorial_values(get_value, result_ast, report_lower, type_micro):
            campos = ["ampicilina", "amoxicilina/ácido clavulânico (urine)", "piperacilina/tazobactam", "cefalexina", "cefalotina", "cefuroxima", "cefuroxima axetil", "ceftriaxona", "cefepima", "ertapenem", "meropenem", "amicacina", "gentamicina", "ácido nalidíxico", "ciprofloxacino", "norfloxacino", "nitrofurantoina", "trimetoprim/sulfametoxazol", "levofloxacina",]
            tem_medicamento_hospitalar = "ceftazidima/avibactam" in report_lower
            proc_val = get_value("Procedência.:")
            eh_local_amb = "AMB" in (proc_val if proc_val else "")
            eh_ambulatorial = (type_micro == 1) and (not tem_medicamento_hospitalar and eh_local_amb)
            if eh_ambulatorial:
                valores = [result_ast(get_value(c)) for c in campos]
                if all(v[0] == 4 for v in valores):
                    valores = [("", "")] * len(campos)
                    gram_negativo_gn_ambulatorio = 2
                else:
                    gram_negativo_gn_ambulatorio = 1 
                return (*valores, gram_negativo_gn_ambulatorio)
            else:
                valores = [("", "")] * len(campos)
                gram_negativo_gn_ambulatorio = 2
                return (*valores, gram_negativo_gn_ambulatorio)
        def get_leveduras_values(get_value, result_ast, report_lower, type_micro):
            campos = ["fluconazol", "voriconazol", "caspofungina", "micafungina", "anfotericina b", "fluocitosina"]
            if any(x in report_text.lower() for x in campos) and type_micro == 2:
                valores = [result_ast(get_value(c)) for c in campos]
                para_leveduras = 1
                return (*valores, para_leveduras)
            else:
                valores = [("", "")] * len(campos)
                para_leveduras = 2
                return (*valores, para_leveduras)
        def get_gram_positivo_values(get_value, result_ast, report_lower, type_micro):
            campos = ["benzilpenicilina", "ampicilina (iv)", "oxacilina", "ceftarolina", "ESTE_E_FIXO_4", "estreptomicina", "gentamicina", "levofloxacina", "eritromicina", "clindamicina", "linezolid", "daptomicina", "teicoplanina", "vancomicina", "tigeciclina", "rifampicina", "trimetoprim/sulfametoxazol", "nitrofurantoina"]
            filtros = ["benzilpenicilina", "ampicilina", "oxacilina", "ceftarolina", "estreptomicina", "gentamicina", "levofloxacina", "eritromicina", "clindamicina", "linezolid", "daptomicina", "teicoplanina", "vancomicina", "tigeciclina", "rifampicina", "trimetoprim/sulfametoxazol", "nitrofurantoina"]
            if any(x in report_text.lower() for x in filtros) and type_micro == 0:
                valores = []
                for c in campos:
                    if c == "ESTE_E_FIXO_4":
                        valores.append((4, "")) 
                    else:
                        valores.append(result_ast(get_value(c)))
                gram_positivo = 1
                return (*valores, gram_positivo)
            else:
                valores = [("", "")] * len(campos)    
                gram_positivo = 2
                return (*valores, gram_positivo)
        def get_imunocromat(report_lower):
            if "imunocromatografia" in report_lower or "imunocromatográfico" in report_lower:
                return 1
            else:
                return 2
        def get_carbapenase(report_lower):
            if "dupla carbapenemase" in report_lower:
                return 6
            if re.search(r'\bmetalo\b', report_lower):
                return 3
            if re.search(r'\bserino\b', report_lower):
                return 2
            if "(bluecarba) - não reagente" in report_lower or "(bluecarba) - nao reagente" in report_lower:
                return 0
            if "enzimático não detectável" in report_lower or "enzimatico nao detectavel" in report_lower:
                return 1
            return ""
        isolate_micro = get_value("ISOLADO1 :") or get_value("ISOLADO2 :") 
        type_micro = classify_microorganism(get_value("ISOLADO1 :") or get_value("ISOLADO2 :")) 
        micro_final = "Outro" if type_micro == "" and isolate_micro else isolate_micro 
        other_micro = isolate_micro if type_micro == "" and isolate_micro else ""
        (fluconazol, voriconazol, caspofungina, micafungina, anfotericina_b, fluocitosina, para_leveduras) = get_leveduras_values(get_value, result_ast, report_lower, type_micro)
        (benzilpenicilina, ampicilina_gram_positivo, oxacilina, ceftarolina_pneumonia, ceftarolina_outra, estreptomicina, gentamicina_gram_positivo, levofloxacina_gram_positivo, eritromicina, clindamicina, linezolid, daptomicina, teicoplanina, vancomicina, tigeciclina_gram_positivo, rifampicina, trimetoprima_sulfametaxazol_gram_positivo, nitrofurantoina_gram_positivo, gram_positivo) = get_gram_positivo_values(get_value, result_ast, report_lower, type_micro)
        (amoxicilina, aztreonam, cefiderocol, ceftalozone_tazobactam, ceftazidime_avibactam, ampicilina, ampicilina_sulbactam, piperacilina_tazobactam, cefoxitina, cefuroxima, ceftazidima, cefepima, ertapenem, imipenem, imipenem_relebactam, gn_levofloxacina, meropenem, meropenem_vaborbactam, amicacina, gentamicina, ciprofloxacina, tigeciclina, trimetoprim_sulfametozol, colistina, ceftriaxona, gram_negativo_gn_hospitala) = get_gn_hospitalar_values(get_value, result_ast, report_lower, type_micro)
        (ampicilina_ambul, amoxicilina_cido_clavul_nico, piperacilina_tazobactam_ambul, cefalexina, cefalotina, cefuroxima_ambul, cefuroxima_axetil, ceftriaxona_ambul, cefepima_ambul, ertapenem_ambul, meropenem_ambul, amicacina_ambul, gentamicina_ambul, cido_nalidixico, ciprofloxacino, norfloxacino, nitrofurantoina, trimetoprima_sulfametoxazol, levofloxacina, gram_negativo_gn_ambulat_rio) = get_gn_ambulatorial_values(get_value, result_ast, report_lower, type_micro)
        if gram_negativo_gn_ambulat_rio == 2 and gram_negativo_gn_hospitala == 2 and gram_positivo == 2 and para_leveduras == 2:
            gram_negativo_gn_ambulat_rio = "" 
            gram_negativo_gn_hospitala = "" 
            gram_positivo = "" 
            para_leveduras = ""
            antibiograma_realizado = 2
        else:
            antibiograma_realizado = 1
        mechanism, other_mechanism = get_mechanism(oxacilina[0], meropenem[0], imipenem[0], ertapenem[0], vancomicina[0], micro_final)
        tem_mecanismo_resist_ncia = 1 if mechanism != "" else 2
        code_mcim, code_ecim = get_cim_result(report_lower, micro_final)
        realizou_teste_imunogromat = get_imunocromat(report_lower) if mechanism in (2, 6) else ""
        return {
            "resultado": 1,
            "qual_microorganismo": micro_final,
            "qual_o_tipo_de_microorganismo": type_micro,
            "outro_microorganismo": other_micro,
            "apresenta_mcim": code_mcim,
            "apresenta_ecim": code_ecim,
            "fluconazol": fluconazol[0],
            "mic_fluconazol": fluconazol[1],
            "voriconazol": voriconazol[0],
            "mic_voriconazol": voriconazol[1],
            "caspofungina": caspofungina[0],
            "mic_caspofungina": caspofungina[1],
            "micafungina": micafungina[0],
            "mic_micafungina": micafungina[1],
            "anfotericina_b": anfotericina_b[0],
            "mic_anfotericina": anfotericina_b[1],
            "fluocitosina": fluocitosina[0],
            "mic_fluocitosina": fluocitosina[1],
            "para_leveduras": para_leveduras,
            "benzilpenicilina": benzilpenicilina[0],
            "mic_benzilpenicilina": benzilpenicilina[1],
            "ampicilina_gram_positivo": ampicilina_gram_positivo[0],
            "mic_ampicilinagp": ampicilina_gram_positivo[1],
            "oxacilina": oxacilina[0],
            "mic_oxacilina": oxacilina[1],
            "ceftarolina_pneumonia": ceftarolina_pneumonia[0],
            "mic_ceftarolina": ceftarolina_pneumonia[1],
            "ceftarolina_outra": ceftarolina_outra[0],
            "mic_ceftarolina_outra": ceftarolina_outra[1],
            "estreptomicina": estreptomicina[0],
            "mic_estreptomicina": estreptomicina[1],
            "gentamicina_gram_positivo": gentamicina_gram_positivo[0],
            "mic_gentamicinagp": gentamicina_gram_positivo[1],
            "levofloxacina_gram_positivo": levofloxacina_gram_positivo[0],
            "mic_levofloxacina_gram_positivo": levofloxacina_gram_positivo[1],
            "eritromicina": eritromicina[0],
            "mic_eritromicina": eritromicina[1],
            "clindamicina": clindamicina[0],
            "mic_clindamicina": clindamicina[1],
            "linezolid": linezolid[0],
            "mic_linezolid": linezolid[1],
            "daptomicina": daptomicina[0],
            "mic_daptomicina": daptomicina[1],
            "teicoplanina": teicoplanina[0],
            "mic_teicoplanina": teicoplanina[1],
            "vancomicina": vancomicina[0],
            "mic_vancomicina": vancomicina[1],
            "tigeciclina_gram_positivo": tigeciclina_gram_positivo[0],
            "mic_tigeciclinagp": tigeciclina_gram_positivo[1],
            "rifampicina": rifampicina[0],
            "mic_rifampicina": rifampicina[1],
            "trimetoprima_sulfametaxazol_gram_positivo": trimetoprima_sulfametaxazol_gram_positivo[0],
            "mic_trimetoprima_gram_posi": trimetoprima_sulfametaxazol_gram_positivo[1],
            "nitrofurantoina_gram_positivo": nitrofurantoina_gram_positivo[0],
            "mic_nitrofurantoinagp": nitrofurantoina_gram_positivo[1],
            "gram_positivo": gram_positivo,
            "amoxicilina": amoxicilina[0],
            "mic_amoxicilina": amoxicilina[1],
            "aztreonam": aztreonam[0],
            "mic_aztreonam": aztreonam[1],
            "cefiderocol": cefiderocol[0],
            "mic_cefiderocol": cefiderocol[1],
            "ceftalozone_tazobactam": ceftalozone_tazobactam[0],
            "mic_ceftalozone_tazobactam": ceftalozone_tazobactam[1],
            "ceftazidime_avibactam": ceftazidime_avibactam[0],
            "mic_ceftazidime_avibactam": ceftazidime_avibactam[1],
            "ampicilina": ampicilina[0],
            "mic_ampicilina": ampicilina[1],
            "ampicilina_sulbactam": ampicilina_sulbactam[0],
            "mic_ampicilina_sulbactam": ampicilina_sulbactam[1],
            "piperacilina_tazobactam": piperacilina_tazobactam[0],
            "mic_piperacilina_tazobacta": piperacilina_tazobactam[1],
            "cefoxitina": cefoxitina[0],
            "mic_cefoxitina": cefoxitina[1],
            "cefuroxima": cefuroxima[0],
            "mic_cefuroxima": cefuroxima[1],
            "ceftazidima": ceftazidima[0],
            "mic_ceftazidima": ceftazidima[1],
            "cefepima": cefepima[0],
            "mic_cefepima": cefepima[1],
            "ertapenem": ertapenem[0],
            "mic_ertapenem": ertapenem[1],
            "imipenem": imipenem[0],
            "mic_imipenem": imipenem[1],
            "imipenem_relebactam": imipenem_relebactam[0],
            "mic_imipenem_relebactam": imipenem_relebactam[1],
            "gn_levofloxacina": gn_levofloxacina[0],
            "mic_levofloxacina": gn_levofloxacina[1],
            "meropenem": meropenem[0],
            "mic_meropenem": meropenem[1],
            "meropenem_vaborbactam": meropenem_vaborbactam[0],
            "mic_meropenem_vaborbactam": meropenem_vaborbactam[1],
            "amicacina": amicacina[0],
            "mic_amicacina": amicacina[1],
            "gentamicina": gentamicina[0],
            "mic_gentamicina": gentamicina[1],
            "ciprofloxacina": ciprofloxacina[0],
            "mic_ciprofloxacina": ciprofloxacina[1],
            "tigeciclina": tigeciclina[0],
            "mic_tigeciclina": tigeciclina[1],
            "trimetoprim_sulfametozol": trimetoprim_sulfametozol[0],
            "mic_trimetoprim_sulfametox": trimetoprim_sulfametozol[1],
            "colistina": colistina[0],
            "mic_colistina": colistina[1],
            "ceftriaxona": ceftriaxona[0],
            "mic_ceftriaxona": ceftriaxona[1],
            "gram_negativo_gn_hospitala": gram_negativo_gn_hospitala,
            "ampicilina_ambul": ampicilina_ambul[0],
            "mic_ampicilina_am": ampicilina_ambul[1],
            "amoxicilina_cido_clavul_nico": amoxicilina_cido_clavul_nico[0],
            "mic_amoxicilina_cido_clavu": amoxicilina_cido_clavul_nico[1],
            "piperacilina_tazobactam_ambul": piperacilina_tazobactam_ambul[0],
            "mic_piperacilina_tazo": piperacilina_tazobactam_ambul[1],
            "cefalexina": cefalexina[0],
            "mic_cefalexina": cefalexina[1],
            "cefalotina": cefalotina[0],
            "mic_cefalotina": cefalotina[1],
            "cefuroxima_ambul": cefuroxima_ambul[0],
            "mic_cefuroxima_gn": cefuroxima_ambul[1],
            "cefuroxima_axetil": cefuroxima_axetil[0],
            "mic_cefuroxima_axetil": cefuroxima_axetil[1],
            "ceftriaxona_ambul": ceftriaxona_ambul[0],
            "mic_ceftriaxonagn": ceftriaxona_ambul[1],
            "cefepima_ambul": cefepima_ambul[0],
            "mic_cefepimagn": cefepima_ambul[1],
            "ertapenem_ambul": ertapenem_ambul[0],
            "mic_ertapenemgn": ertapenem_ambul[1],
            "meropenem_ambul": meropenem_ambul[0],
            "mic_meropenemgn": meropenem_ambul[1],
            "amicacina_ambul": amicacina_ambul[0],
            "mic_amicacinagn": amicacina_ambul[1],
            "gentamicina_ambul": gentamicina_ambul[0],
            "mic_gentamicinagn": gentamicina_ambul[1],
            "cido_nalidixico": cido_nalidixico[0],
            "mic_cido_nalidixico": cido_nalidixico[1],
            "ciprofloxacino": ciprofloxacino[0],
            "mic_ciprofloxaxacino": ciprofloxacino[1],
            "norfloxacino": norfloxacino[0],
            "mic_norfloxacino": norfloxacino[1],
            "nitrofurantoina": nitrofurantoina[0],
            "mic_nitrofurantoina": nitrofurantoina[1],
            "trimetoprima_sulfametoxazol": trimetoprima_sulfametoxazol[0],
            "mic_trimetoprima_sulfameto": trimetoprima_sulfametoxazol[1],
            "levofloxacina": levofloxacina[0],
            "mic_levofloxacina": levofloxacina[1],
            "gram_negativo_gn_ambulat_rio": gram_negativo_gn_ambulat_rio,
            "antibiograma_realizado": antibiograma_realizado,
            "qual_gene_de_mecanismo_res": mechanism,
            "qual_outro_mecanismo_de_re": other_mechanism,
            "tem_mecanismo_resist_ncia": tem_mecanismo_resist_ncia,
            "realizou_teste_imunogromat": realizou_teste_imunogromat,
            "apresenta_gene_resistencia": apresenta_gene_resistencia(report_lower),
            "apresenta_carbapenase": get_carbapenase(report_lower)
        }
def extract_fields(report_text, df_name):
    report_lower = report_text.lower()
    def get_value(label):
        idx = report_lower.find(label.lower())
        if idx != -1:
            end = report_lower.find("\n", idx)
            if end == -1:
                end = len(report_lower)
            line = report_text[idx:end]
            value = line.split(":", 1)[-1].strip()
            if value == "" and "dt.liberação" in label.lower():
                next_line_start = end + 1
                next_line_end = report_lower.find("\n", next_line_start)
                if next_line_end == -1:
                    next_line_end = len(report_lower)
                value = report_text[next_line_start:next_line_end].strip()
            return value
        return ""
    def get_sample_number():
        pattern = r"Amostra:\s*(.*)"
        match = re.search(pattern, report_text, re.IGNORECASE | re.DOTALL)
        if not match:
            return ""
        value = match.group(1).strip()
        if "\n" in value:
            value = value.split("\n")[0].strip()
        return value
    def format_time(raw_text, df_name, column_name=""):
        match = re.search(r"(\d{2}/\d{2}/\d{4})(?:\s+(\d{2}:\d{2}))?", raw_text)
        if not match:
            return ""
        date_str = match.group(1)
        time_str = match.group(2) or "00:00"
        try:
            date_obj = datetime.strptime(f"{date_str} {time_str}", "%d/%m/%Y %H:%M")
        except ValueError:
            return ""
        if df_name in ("general", "vigilance"):
            return date_obj.strftime("%Y-%m-%d %H:%M")
        elif df_name == "smear":
            if column_name == "data_da_libera_o":
                date_obj += timedelta(days=1)
            return date_obj.strftime("%Y-%m-%d")
        else:
            return date_obj.strftime("%Y-%m-%d %H:%M")
    def get_result(report_text, df_name):
        text_lower = report_text.lower()
        if df_name in ("vigilance", "smear"):
            return 2
        if "sugestivo de contaminação" in text_lower:
            if "urina" in text_lower:
                return 2
            else:
                return 3
        else:
            return 0
    def process_material(raw_material, df_name, report_text):
        if not raw_material:
            report_clean = str(report_text).lower() if report_text else ""
            if "sangue" in report_clean:
                return {"tipo": "SANGUE", "outro": ""}
            else:
                return {"tipo": "ESCARRO", "outro": ""}
        material_clean = raw_material.strip().lower()        
        if "sangue" in material_clean:
            return {"tipo": "SANGUE", "outro": ""}
        if df_name == "smear":
            if material_clean not in materials_smear_microscopy:
                return {"tipo": raw_material, "outro": raw_material}
            return {"tipo": raw_material, "outro": ""}
        elif df_name == "general":
            if material_clean not in materials_general:
                return {"tipo": "Outro", "outro": raw_material}
            return {"tipo": raw_material, "outro": ""}
        elif df_name == "vigilance":
            if material_clean not in materials_vigilance:
                return {"tipo": "Outro", "outro": raw_material}
            return {"tipo": raw_material, "outro": ""}
        else:
            return {"tipo": raw_material, "outro": ""}
    def get_negative_agent(report_text):
        text_lower = report_text.lower()
        has_carbapenemicos = "carbapenêmico" in text_lower
        has_vancomicina = "vancomicina" in text_lower
        if has_carbapenemicos and has_vancomicina:
            return 3
        elif has_carbapenemicos:
            return 1
        elif has_vancomicina:
            return 2
        else:
            return ""
    def get_material_value(labels):
        for label in labels:
            value = get_value(label)
            if value:
                return value
        return ""
    def format_sex(raw_sexo_value, df_name):
        sexo_clean = raw_sexo_value.split("|")[0].strip().lower()
        if df_name in ("smear", "vigilance"):
            if "masculino" in sexo_clean:
                return 2
            elif "feminino" in sexo_clean:
                return 1
        elif df_name == "general":
            if "masculino" in sexo_clean:
                return 1
            elif "feminino" in sexo_clean:
                return 0
        return ""  
    def check_see_result(report_lower):
        if "ver resultado do antibiograma no" in report_lower.lower():
            return "sim"
        else:
            return "não"
    def check_hospital(get_value):
        valor = get_value("Procedência.:")
        if not valor or not valor.strip():
            return ""
        procedencia = valor.split("|")[0].strip().lower()
        if "meac" in procedencia or "maternidade" in procedencia:
            return 2
        else:
            return 1
    return {
        "hospital": check_hospital(get_value),
        "hospital_de_origem": check_hospital(get_value),
        "faz_parte_projeto_cdc_rfa": 2,
        "faz_parte_projeto_cdc_rfa_ck21_2104": 2,
        "n_mero_do_pedido": get_sample_number(),
        "n_mero_do_prontu_rio": "".join(re.findall(r"\d+", get_value("Prontuário..:"))),
        "sexo": format_sex(get_value("Sexo........:"), df_name),
        "idade": get_value("Idade:").split("A")[0].strip(),
        "idade_anos": get_value("Idade:").split("A")[0].strip(),
        "setor_de_origem": get_value("Procedência.:").split("|")[0].strip(),
        "data_de_entrada": format_time(get_value("Dt.Recebimento:"), df_name, "data_de_entrada"),
        "data_da_entrada": format_time(get_value("Dt.Recebimento:"), df_name, "data_da_entrada"),
        "data_da_libera_o": format_time(get_value("Dt.Liberação:"), df_name, "data_da_libera_o"),
        "qual_tipo_de_material": process_material(get_material_value(["material:", "material : "]), df_name, report_lower)["tipo"] if df_name in ["general", "vigilance"] else get_material_value(["material:", "material : "]),
        "tipo_de_material": process_material(get_material_value(["material examinado:", "material examinado : "]), df_name, report_lower)["tipo"] if df_name == "smear" else get_material_value(["material examinado:", "material examinado : "]),
        "se_outro_material": process_material(get_material_value(["material:", "material : "]), df_name, report_lower)["outro"] if df_name == "smear" else "",
        "outro_tipo_de_material": process_material(get_material_value(["material:", "material : "]), df_name, report_lower)["outro"] if df_name in ["general", "vigilance"] else "",
        "resultado": get_result(report_lower, df_name),
        "se_negativo_para_qual_agente": get_negative_agent(report_lower),
        "formulrio_complete": 2,
        "dados_microbiologia_complete": 2,
        "data_agora": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "column_aux1": "".join(re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ\s]+", get_value("Prontuário..:"))).strip(),
        "check_ver_resultado_em": check_see_result(report_lower),
        "ver_resultado_em_pedido": get_value("ver resultado do antibiograma no"),
        "via_coleta": (get_value("Sítio da coleta:") or get_value("SITIO DA COLETA:") or "").split('|')[0].strip()
    }

# Funções de processamento
def process_general(report_text, row_idx=None):
    global df_general
    fields = extract_fields(report_text, "general")
    if any(x in report_text.lower() for x in ["positivo", "interpretação dos antibióticos é expressa"]):    
        fields_positive = extract_fields_positive(report_text, "general")
        if fields_positive:
            fields.update(fields_positive)
    if not fields.get("n_mero_do_prontu_rio"):
        return
    if row_idx is None:
        new_row = {col: "" for col in st.secrets["columns"]["general"]}
        for key, val in fields.items():
            if key in new_row:
                new_row[key] = val
        new_row["id"] = None
        df_general = pd.concat([df_general, pd.DataFrame([new_row])], ignore_index=True)
    else:
        for key, val in fields.items():
            if key in df_general.columns:
                if df_general.at[row_idx, key] == "" or pd.isna(df_general.at[row_idx, key]):
                    df_general.at[row_idx, key] = val
def process_vigilance(report_text, row_idx=None):
    global df_vigilance
    fields = extract_fields(report_text, "vigilance")
    if any(x in report_text.lower() for x in ["positivo", "interpretação dos antibióticos é expressa"]):    
        fields_positive = extract_fields_positive(report_text, "vigilance")
        if fields_positive:
            fields.update(fields_positive)
    if not fields.get("n_mero_do_prontu_rio"):
        return
    if row_idx is None:
        new_row = {col: "" for col in st.secrets["columns"]["vigilance"]}
        for key, val in fields.items():
            if key in new_row:
                new_row[key] = val
        new_row["record_id"] = None
        df_vigilance = pd.concat([df_vigilance, pd.DataFrame([new_row])], ignore_index=True)
    else:
        for key, val in fields.items():
            if key in df_vigilance.columns:
                if df_vigilance.at[row_idx, key] == "" or pd.isna(df_vigilance.at[row_idx, key]):
                    df_vigilance.at[row_idx, key] = val
def process_smear(report_text, row_idx=None):
    global df_smear
    fields = extract_fields(report_text, "smear")
    if any(x in report_text.lower() for x in ["positivo", "interpretação dos antibióticos é expressa"]):    
        fields_positive = extract_fields_positive(report_text, "smear")
        if fields_positive:
            fields.update(fields_positive)
    if not fields.get("n_mero_do_prontu_rio"):
        return
    if row_idx is None:
        new_row = {col: "" for col in st.secrets["columns"]["smear_microscopy"]}
        for key, val in fields.items():
            if key in new_row:
                new_row[key] = val
        new_row["record_id"] = None
        df_smear = pd.concat([df_smear, pd.DataFrame([new_row])], ignore_index=True)
    else:
        for key, val in fields.items():
            if key in df_smear.columns:
                if df_smear.at[row_idx, key] == "" or pd.isna(df_smear.at[row_idx, key]):
                    df_smear.at[row_idx, key] = val

# Função para filtrar pedidos
def filter_general(df_general):
    df_general["pedido_inicial"] = df_general["n_mero_do_pedido"].astype(str).str[:-2]
    resultados = []
    df_vazio = df_general[df_general["n_mero_do_pedido"].astype(str) == ""]
    df_sangue = df_general[df_general["qual_tipo_de_material"].astype(str).str.contains("5") & (df_general["n_mero_do_pedido"].astype(str) != "")]
    df_outros = df_general[~df_general["qual_tipo_de_material"].astype(str).str.contains("5") & (df_general["n_mero_do_pedido"].astype(str) != "")]
    for pedido, grupo in df_sangue.groupby("pedido_inicial"):
        positivas = grupo[grupo["qual_microorganismo"].notna() & (grupo["qual_microorganismo"] != "")]
        negativas = grupo[grupo["qual_microorganismo"].isna() | (grupo["qual_microorganismo"] == "")]
        if len(grupo) == 1:
            resultados.append(grupo.iloc[0].to_dict())
            continue
        adicionados = set()
        for _, row in positivas.iterrows():
            micro = row["qual_microorganismo"]
            ver_res = str(row.get("check_ver_resultado_em", "")).strip().lower()
            if micro not in adicionados and ver_res == "não":
                resultados.append(row.to_dict())
                adicionados.add(micro)
        for _, row in positivas.iterrows():
            micro = row["qual_microorganismo"]
            ver_res = str(row.get("check_ver_resultado_em", "")).strip().lower()
            if micro not in adicionados and ver_res == "sim":
                resultados.append(row.to_dict())
                adicionados.add(micro)
        if len(adicionados) == 0 and len(negativas) > 0:
            resultados.append(negativas.iloc[0].to_dict())
    df_final = pd.DataFrame(resultados)
    if len(df_outros) > 0:
        df_final = pd.concat([df_final, df_outros], ignore_index=True)
    if len(df_vazio) > 0:
        df_final = pd.concat([df_final, df_vazio], ignore_index=True)
    if "ver_resultado_em_pedido" in df_final.columns:
        col_inicio = df_final.columns.get_loc("resultado")
        for idx, row in df_final.iterrows():
            valor_ref = str(row.get("ver_resultado_em_pedido", "")).strip()
            if valor_ref == "":
                continue
            pedido_ref = valor_ref[:-2]
            pedido_atual = str(row["pedido_inicial"])
            if pedido_ref != pedido_atual:
                linha_origem = df_final[df_final["pedido_inicial"] == pedido_ref]
                if len(linha_origem) > 0:
                    linha_origem = linha_origem.iloc[0]
                    df_final.loc[idx, df_final.columns[col_inicio:]] = linha_origem[col_inicio:]
    df_final.drop(columns=["pedido_inicial", "check_ver_resultado_em", "ver_resultado_em_pedido", "laudo_unico", "via_coleta"], inplace=True, errors="ignore")
    return df_final
def filter_blood(df, substitution_departments=substitution_departments, blood_collection=blood_collection, microorganism_blood_positive=microorganism_blood_positive, microorganism_blood_contaminated=microorganism_blood_contaminated):
    df_filter_blood = df[df['qual_tipo_de_material'].str.contains(r"sangue", case=False, na=False)].copy()
    df_filter_blood['micro_contaminado'] = None
    if "via_coleta" in df_filter_blood.columns and blood_collection:
        for idx, val in df_filter_blood["via_coleta"].items():
            if pd.isna(val): 
                continue
            val_str = str(val).upper()
            for trecho_chave, codigo in blood_collection.items():
                if trecho_chave.upper() in val_str:
                    df_filter_blood.at[idx, "via_coleta"] = codigo
                    break
    colunas_para_remover = """
    tem_mecanismo_resist_ncia qual_gene_de_mecanismo_res qual_outro_mecanismo_de_re 
    apresenta_mcim apresenta_ecim apresenta_carbapenase realizou_teste_imunogromat 
    data_do_teste_imunogromato tempo_de_realiza_o_do_test apresenta_gene_resistencia 
    antibiograma_realizado gram_negativo_gn_hospitala amoxicilina mic_amoxicilna_cido_clavul 
    aztreonam mic_aztreonam cefiderocol mic_cefiderocol ceftalozone_tazobactam 
    mic_ceftalozone_tazobactam ceftazidime_avibactam mic_ceftazidime_avibactam 
    ampicilina mic_ampicilina ampicilina_sulbactam mic_ampicilina_sulbactam 
    piperacilina_tazobactam mic_piperacilina_tazobacta cefoxitina mic_cefoxitina 
    cefuroxima mic_cefuroxima ceftazidima mic_ceftazidima cefepima mic_cefepima 
    ertapenem mic_ertapenem imipenem mic_imipenem imipenem_relebactam 
    mic_imipenem_relebactam gn_levofloxacina mic_levofloxacina meropenem 
    mic_meropenem meropenem_vaborbactam mic_meropenem_vaborbactam amicacina 
    mic_amicacina gentamicina mic_gentamicina ciprofloxacina mic_ciprofloxacina 
    tigeciclina mic_tigeciclina trimetoprim_sulfametozol mic_trimetoprim_sulfametox 
    colistina mic_colistina ceftriaxona mic_ceftriaxona gram_negativo_gn_ambulat_rio 
    ampicilina_ambul mic_ampicilina_am amoxicilina_cido_clavul_nico 
    mic_amoxicilina_cido_clavu piperacilina_tazobactam_ambul 
    mic_piperacilina_tazo cefalexina mic_cefalexina cefalotina 
    mic_cefalotina cefuroxima_ambul mic_cefuroxima_gn cefuroxima_axetil 
    mic_cefuroxima_axetil ceftriaxona_ambul mic_ceftriaxonagn cefepima_ambul 
    mic_cefepimagn ertapenem_ambul mic_ertapenemgn meropenem_ambul 
    mic_meropenemgn amicacina_ambul mic_amicacinagn gentamicina_ambul 
    mic_gentamicinagn cido_nalidixico mic_cido_nalidixico ciprofloxacino 
    mic_ciprofloxaxacino norfloxacino mic_norfloxacino nitrofurantoina 
    mic_nitrofurantoina trimetoprima_sulfametoxazol mic_trimetoprima_sulfameto 
    levofloxacina mic_levofloxacina gram_positivo benzilpenicilina 
    mic_benzilpenicilina ampicilina_gram_positivo mic_ampicilinagp 
    oxacilina mic_oxacilina ceftarolina_pneumonia mic_ceftarolina 
    ceftarolina_outra mic_ceftarolina_outra estreptomicina mic_estreptomicina 
    gentamicina_gram_positivo mic_gentamicinagp 
    levofloxacina_gram_positivo mic_levofloxacina_gram_positivo eritromicina 
    mic_eritromicina clindamicina mic_clindamicina linezolid mic_linezolid 
    daptomicina mic_daptomicina teicoplanina mic_teicoplanina vancomicina 
    mic_vancomicina tigeciclina_gram_positivo mic_tigeciclinagp 
    rifampicina mic_rifampicina trimetoprima_sulfametaxazol_gram_positivo 
    mic_trimetoprima_gram_posi nitrofurantoina_gram_positivo 
    mic_nitrofurantoinagp para_leveduras fluconazol mic_fluconazol 
    voriconazol mic_voriconazol caspofungina mic_caspofungina micafungina 
    mic_micafungina anfotericina_b mic_anfotericina fluocitosina mic_fluocitosina 
    qual_tipo_de_material outro_tipo_de_material desfecho_do_paciente observa_es 
    check_ver_resultado_em ver_resultado_em_pedido laudo_unico outro_microorganismo 
    qual_o_tipo_de_microorganismo faz_parte_projeto_cdc_rfa
    """.split()
    df_filter_blood = df_filter_blood.drop(columns=colunas_para_remover, errors='ignore')  
    novos_nomes = {
        "id": "record_id",
        "n_mero_do_pedido": "numero_pedido",
        "n_mero_do_prontu_rio": "prontuario",
        "setor_de_origem": "setor_origem",
        "data_de_entrada": "data_entrada",
        "data_da_libera_o": "data_liberacao",
        "tempo_de_libera_o_dias": "prazo_entrega",
        "cat_tempo_de_libera_o_dias": "categ_entrega",
        "dados_microbiologia_complete": "form_1_complete",
        "qual_microorganismo": "micro_positivo"
    }
    df_filter_blood = df_filter_blood.rename(columns=novos_nomes)
    if "setor_origem" in df_filter_blood.columns and substitution_departments:
        for idx, val in df_filter_blood["setor_origem"].items():
            if pd.isna(val):
                continue
            val_str = str(val).upper()
            for trecho_chave, novo_valor in substitution_departments.items():
                if trecho_chave.upper() in val_str:
                    df_filter_blood.at[idx, "setor_origem"] = novo_valor
                    break
    if "micro_positivo" in df_filter_blood.columns and "resultado" in df_filter_blood.columns and "numero_pedido" in df_filter_blood.columns:
        temp_classification = {}
        for idx, val in df_filter_blood["micro_positivo"].items():
            if pd.isna(val): continue
            val_str = str(val).upper()
            found_classification = False
            if microorganism_blood_contaminated:
                for trecho, codigo in microorganism_blood_contaminated.items():
                    if trecho.upper() in val_str:
                        temp_classification[idx] = {'code': codigo, 'type': 'contaminant', 'matched_key': trecho}
                        found_classification = True
                        break
            if not found_classification and microorganism_blood_positive:
                for trecho, codigo in microorganism_blood_positive.items():
                    if trecho.upper() in val_str:
                        temp_classification[idx] = {'code': codigo, 'type': 'pathogen', 'matched_key': trecho}
                        found_classification = True
                        break
        df_filter_blood['temp_group_id'] = df_filter_blood['numero_pedido'].astype(str).apply(lambda x: x[:-2] if len(x) > 2 else x)
        grupos = df_filter_blood.groupby('temp_group_id')
        for group_id, group_df in grupos:
            contaminants_in_group = []
            for idx in group_df.index:
                if idx in temp_classification and temp_classification[idx]['type'] == 'contaminant':
                    contaminants_in_group.append(temp_classification[idx]['code'])
            total_samples = len(group_df)
            for idx in group_df.index:
                if idx not in temp_classification:
                    continue 
                info = temp_classification[idx]
                matched_key = info['matched_key']
                if info['type'] == 'pathogen':
                    df_filter_blood.at[idx, "resultado"] = 1
                    df_filter_blood.at[idx, "micro_positivo"] = info['code']
                elif info['type'] == 'contaminant':
                    if total_samples == 1:
                        if matched_key in microorganism_blood_positive:
                            final_code = microorganism_blood_positive[matched_key]
                        else:
                            final_code = info['code']
                        df_filter_blood.at[idx, "resultado"] = 1
                        df_filter_blood.at[idx, "micro_positivo"] = final_code
                    else:
                        count_match = contaminants_in_group.count(info['code'])
                        if count_match == 1:
                            df_filter_blood.at[idx, "resultado"] = 3
                            df_filter_blood.at[idx, "micro_contaminado"] = info['code']
                            df_filter_blood.at[idx, "micro_positivo"] = None
                        else:
                            df_filter_blood.at[idx, "resultado"] = 1
                            final_code = info['code']
                            if matched_key in microorganism_blood_positive:
                                final_code = microorganism_blood_positive[matched_key]
                            df_filter_blood.at[idx, "micro_positivo"] = final_code
        df_filter_blood = df_filter_blood.drop(columns=['temp_group_id'])
    if 'resultado' in df_filter_blood.columns:
         df_filter_blood['resultado'] = df_filter_blood['resultado'].replace(0, 2)
    ordem_final = [
        "record_id", "hospital", "numero_pedido", "prontuario", "setor_origem", 
        "via_coleta", "resultado", "micro_positivo", "micro_contaminado", 
        "data_entrada", "data_liberacao", "prazo_entrega", "categ_entrega", 
        "data_agora", "form_1_complete"
    ]
    df_filter_blood = df_filter_blood.reindex(columns=ordem_final)
    return df_filter_blood
def apply_filter_hospital(df, choice):
    if choice == "Todos" or df is None or df.empty:
        return df
    if choice == "MEAC":
        valores_aceitos = [2, ""]
    elif choice == "HUWC":
        valores_aceitos = [1, ""]
    else:
        return df
    mask = pd.Series(False, index=df.index)
    colunas_encontradas = False
    if "hospital" in df.columns:
        mask = mask | (df["hospital"].isin(valores_aceitos))
        colunas_encontradas = True
    if "hospital_de_origem" in df.columns:
        mask = mask | (df["hospital_de_origem"].isin(valores_aceitos))
        colunas_encontradas = True
    if not colunas_encontradas:
        return df
    return df[mask]

# Funções para tratamento de PDFs
def split_pdf_in_chunks(pdf_file, max_pages=400):
    reader = PdfReader(pdf_file)
    total_pages = len(reader.pages)
    chunks = []
    current_start = 0
    while current_start < total_pages:
        writer = PdfWriter()
        end = min(current_start + max_pages, total_pages)
        for i in range(current_start, end):
            writer.add_page(reader.pages[i])
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        with open(temp_file.name, "wb") as f:
            writer.write(f)
        chunks.append(temp_file.name)
        current_start = end
    return chunks
def extract_text_pdf(pdf_file):
    full_text = ""
    try:
        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text(x_tolerance=2, y_tolerance=3)
                if page_text:
                    full_text += page_text + "\n"
        return full_text
    except Exception as e:
        st.error(f"Erro ao ler o PDF com pdfplumber: {e}")
        return None

def process_singular_report(report_text, valid_ids, tracker, filter_choice):
    report_text_clean = report_text.strip()
    report_text_lower = report_text_clean.lower()
    match = re.search(r"Amostra\s*[\.]*:\s*(\d+)", report_text, re.IGNORECASE)
    if not match: return
    full_id_str = match.group(1)
    sample_match = int(full_id_str[:-2]) if len(full_id_str) > 2 else 0
    if sample_match not in valid_ids: return
    procedencia_index = report_text_lower.find("procedência.:")
    hospital_detectado = ""
    if procedencia_index != -1:
        end_of_line = report_text_lower.find("\n", procedencia_index)
        procedencia_line = report_text_lower[procedencia_index:end_of_line]
        hospital_detectado = "MEAC" if any(x in procedencia_line for x in ["meac", "maternidade"]) else "HUWC"
    if filter_choice != "Todos" and hospital_detectado != filter_choice:
        return
    tracker.add(sample_match)
    if any(x in report_text_lower for x in ["cpdhr", "paciente teste", "bacterioscopia"]): return
    is_vigilancia = re.search(r"(material:\s*|material examinado:\s*)(" + "|".join(re.escape(term) for term in materials_vigilance.keys()) + r")", report_text_lower)
    is_smear = "baar" in report_text_lower
    if is_vigilancia:
        if st.session_state.run_vig and "faltando reagente" not in report_text_lower:
            process_vigilance(report_text)
    elif is_smear:
        if st.session_state.run_smear:
            process_smear(report_text)
    else:
        if st.session_state.run_gen or st.session_state.run_blood:
            process_general(report_text)

def process_text_pdf(text_pdf, valid_ids, tracker, filter_choice):
    if not text_pdf:
        return
    delimiter_pattern = r"(?=COMPLEXO HOSPITALAR DA UFC/EBSERH)"
    reports = re.split(delimiter_pattern, text_pdf)
    for report_chunk in reports:
        if report_chunk.strip() and "COMPLEXO HOSPITALAR" in report_chunk:
            process_singular_report(report_chunk, valid_ids, tracker, filter_choice)

def reset_session():
    st.session_state.dfs_processados = {
        "geral": pd.DataFrame(),
        "vigilancia": pd.DataFrame(),
        "smear": pd.DataFrame(),
        "blood": pd.DataFrame(),
        "pdf_report": None,
        "concluido": False
    }
    st.cache_data.clear()

if "dfs_processados" not in st.session_state:
    reset_session()

# Código principal da página
st.title("Compilação de amostras")
uploaded_files = st.file_uploader("1️⃣ Envie os arquivos PDF para processar", type="pdf", accept_multiple_files=True)
uploaded_reports_discharge = st.file_uploader("2️⃣ Envie o relatório de alta por período", type=["pdf"], accept_multiple_files=False)
uploaded_reports_request = st.file_uploader("3️⃣ Envie o relatório de solicitação", type=["pdf"], accept_multiple_files=False)
st.markdown('<p style="font-size: 14px;">4️⃣ Defina os IDs iniciais para cada formulário</p>', unsafe_allow_html=True)

col1, col2, col3, col4 = st.columns(4)
with col1:
    start_id_general = st.number_input("Geral", value=None, step=1)
with col2:
    start_id_vigilance = st.number_input("Cultura de vigilância", value=None, step=1)
with col3:
    start_id_smear = st.number_input("Baciloscopia", value=None, step=1)
with col4:
    start_id_blood = st.number_input("Hemocultura", value=None, step=1)

st.markdown('<p style="font-size: 14px; margin-bottom: 5px;">5️⃣ Configurações de Processamento</p>', unsafe_allow_html=True)
col_resumo, col_botao = st.columns([0.85, 0.15])

for key, val in {"run_gen": True, "run_vig": True, "run_smear": True, "run_blood": True, "master_filter": "Todos"}.items():
    if key not in st.session_state: st.session_state[key] = val

with col_resumo:
    loc = st.session_state.master_filter
    procs = [name for key, name in [("run_gen", "Geral"), ("run_vig", "Vigilância"), ("run_smear", "Baciloscopia"), ("run_blood", "Hemocultura")] if st.session_state[key]]
    st.markdown(f"""<p style="margin-top: 10px; font-size: 0.8rem; color: #555;">
        <strong>Hospital:</strong> {loc} | <strong>Formulários:</strong> {', '.join(procs) if procs else 'Nenhum'}
    </p>""", unsafe_allow_html=True)

with col_botao:
    with st.popover("Editar"):
        master_filter = st.radio("Selecione o hospital:", ["Todos", "HUWC", "MEAC"], key="master_filter", horizontal=True)
        st.markdown('<p style="font-size: 14px; margin-bottom: 5px;">Selecione quais formulários processar:</p>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            st.checkbox("Geral", key="run_gen")
            st.checkbox("Vigilância", key="run_vig")
        with c2:
            st.checkbox("Baciloscopia", key="run_smear")
            st.checkbox("Hemocultura", key="run_blood")

conditions_met = uploaded_files and uploaded_reports_discharge and uploaded_reports_request
is_disabled = not conditions_met
if not st.session_state.dfs_processados["concluido"]:
    placeholder_botao = st.empty()
    if placeholder_botao.button("Iniciar processamento", disabled=is_disabled, use_container_width=False):
        placeholder_botao.empty()
        reset_session()
        ids_found_report = set()         
        filtro_mestre = st.session_state.master_filter 
        st.markdown('<p style="font-size: 14px;">🔄 Realizando processamento</p>', unsafe_allow_html=True) 
        with st.status("Extraindo dados...", expanded=True) as status:
            if uploaded_reports_request:
                with st.spinner("Processando relatório de solicitação..."):
                    text_request = extract_text_pdf(uploaded_reports_request)
                    if not text_request:
                        st.error("Não foi possível extrair texto do relatório de solicitação.")
                        st.stop()
                    matches = re.findall(r"Pedido\s*[\.:]?\s*[\r\n]*(\d+)", text_request, re.IGNORECASE)
                    if not matches:
                        st.warning("Nenhum número de pedido encontrado.")
                        valid_ids = set()
                    else:
                        valid_ids = {int(i) for i in matches}
                        st.markdown(f"✅ {len(valid_ids)} pedidos identificados.")
            if uploaded_files:
                for pdf_file in uploaded_files:
                    with st.spinner("Dividindo PDF..."):
                        pdf_parts = split_pdf_in_chunks(pdf_file, max_pages=400)
                    for idx, part in enumerate(pdf_parts, start=1):
                        with st.spinner(f"Processando parte {idx}..."):
                            text = extract_text_pdf(part)
                            process_text_pdf(text, valid_ids, ids_found_report, filtro_mestre)
                st.markdown("✅ Extração de dados concluída!")
            if st.session_state.run_blood:
                df_blood = df_general.copy()
            else:
                df_blood = pd.DataFrame()
            if uploaded_reports_discharge:
                df_list = [df_general, df_vigilance, df_smear]
                df_general, df_vigilance, df_smear = fill_outcome(uploaded_reports_discharge, df_list)
            with st.spinner("Codificando termos e aplicando filtros..."):
                df_general, df_vigilance, df_smear = compare_data(
                    [df_general, df_vigilance, df_smear], 
                    substitution_departments, 
                    {"df_general": materials_general, "df_vigilance": materials_vigilance, "df_smear": materials_smear_microscopy}
                )
                if st.session_state.run_gen or st.session_state.run_blood:
                    df_general = filter_general(df_general)
                if st.session_state.run_blood and not df_blood.empty:
                    df_blood = filter_blood(df_blood)
                if not st.session_state.run_gen: df_general = pd.DataFrame()
                if not st.session_state.run_vig: df_vigilance = pd.DataFrame()
                if not st.session_state.run_smear: df_smear = pd.DataFrame()
                st_gen = int(start_id_general) if start_id_general is not None else 1
                st_vig = int(start_id_vigilance) if start_id_vigilance is not None else 1
                st_smear = int(start_id_smear) if start_id_smear is not None else 1
                st_blood = int(start_id_blood) if start_id_blood is not None else 1
                if not df_general.empty: 
                    df_general['id'] = range(st_gen, st_gen + len(df_general))
                if not df_vigilance.empty: 
                    df_vigilance['record_id'] = range(st_vig, st_vig + len(df_vigilance))
                if not df_smear.empty: 
                    df_smear['record_id'] = range(st_smear, st_smear + len(df_smear))
                if not df_blood.empty: 
                    df_blood['record_id'] = range(st_blood, st_blood + len(df_blood))
                st.markdown("✅ Codificação e filtragem concluídas!")
            pdf_solicitacao_colorido = None
            if uploaded_reports_request:
                with st.spinner("Criando destaques no relatório de pedidos..."):
                    pdf_solicitacao_colorido = paint_request_pdf(uploaded_reports_request, ids_found_report, valid_ids)
            st.session_state.dfs_processados["geral"] = df_general
            st.session_state.dfs_processados["vigilancia"] = df_vigilance
            st.session_state.dfs_processados["smear"] = df_smear
            st.session_state.dfs_processados["blood"] = df_blood
            st.session_state.dfs_processados["pdf_report"] = pdf_solicitacao_colorido
            st.session_state.dfs_processados["concluido"] = True 
            status.update(label="Processamento Concluído!", state="complete", expanded=False)
        st.rerun()

else:
    st.markdown('<p style="font-size: 14px;">⬇️ Processamento finalizado</p>', unsafe_allow_html=True)
    col1, col2, _ = st.columns([0.22, 0.17, 0.61])
    with col1:
        style_download(
            st.session_state.dfs_processados["geral"],
            st.session_state.dfs_processados["vigilancia"],
            st.session_state.dfs_processados["smear"],
            st.session_state.dfs_processados["blood"],
            pdf_report=st.session_state.dfs_processados["pdf_report"]
        )
    with col2:
        if st.button("Reiniciar", use_container_width=True):
            reset_session()
            st.rerun()
