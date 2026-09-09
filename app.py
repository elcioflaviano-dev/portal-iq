import streamlit as st
import pandas as pd
from PIL import Image
import os
import urllib.parse
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# --- 1. Configuração Inicial ---
st.set_page_config(page_title="Portal IQ - Totale", layout="wide", initial_sidebar_state="expanded")

if 'logado' not in st.session_state: st.session_state['logado'] = False
if 'pagina_atual' not in st.session_state: st.session_state['pagina_atual'] = "Dashboard"
if 'email_pronto' not in st.session_state: st.session_state['email_pronto'] = None

# --- Estilização CSS para Cards Coloridos Inteiros (Estilo TV) ---
st.markdown("""
    <style>
    .metric-card-blue, .metric-card-green, .metric-card-orange {
        padding: 20px;
        border-radius: 12px;
        color: white !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.15);
        margin-bottom: 10px;
    }
    .metric-card-blue { background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); }
    .metric-card-green { background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); }
    .metric-card-orange { background: linear-gradient(135deg, #f2994a 0%, #f2c94c 100%); }
    
    .metric-card * { color: white !important; }
    .metric-title { font-size: 14px; font-weight: 600; text-transform: uppercase; margin-bottom: 8px; opacity: 0.9; }
    .metric-value { font-size: 28px; font-weight: 700; margin-bottom: 5px; }
    .metric-sub { font-size: 12px; opacity: 0.85; }
    </style>
""", unsafe_allow_html=True)

# --- 2. Conexão com Google Sheets ---
def conectar_planilha():
    try:
        creds_dict = json.loads(st.secrets["gcp_service_account"])
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        return client.open("PORTAL IQ")
    except Exception as e:
        st.error(f"Erro ao conectar com o Google Sheets. Detalhe: {e}")
        st.stop()

# Sem TTL estrito para garantir sincronia imediata com o Sheets
def carregar_dados():
    planilha = conectar_planilha()
    
    def ler_aba(nome_aba):
        try:
            ws = planilha.worksheet(nome_aba)
            registros = ws.get_all_records()
            return pd.DataFrame(registros) if registros else pd.DataFrame()
        except:
            return pd.DataFrame()
            
    dados_iqs = ler_aba("Base_IQ")
    dados_tecnicos = ler_aba("Base_Tecnicos")
    
    if dados_iqs.empty or dados_tecnicos.empty:
        st.error("Planilha do Google está vazia ou faltando as abas Base_IQ / Base_Tecnicos.")
        st.stop()
    
    dados_iqs['re_iq'] = dados_iqs['re_iq'].astype(str).str.strip().str.replace(r'\.0$', '', regex=True)
    dados_iqs['senha'] = dados_iqs.get('senha', '').astype(str).str.strip()
    dados_iqs['PERFIL'] = dados_iqs.get('PERFIL', 'IQ').astype(str).str.strip().str.upper()
    
    dados_tecnicos['login'] = dados_tecnicos.get('login', '').astype(str).str.strip().str.replace(r'\.0$', '', regex=True)
    dados_tecnicos['re_iq_responsavel'] = dados_tecnicos.get('re_iq_responsavel', '').astype(str).str.strip().str.replace(r'\.0$', '', regex=True)
    
    colunas_remover = ['status_certificacao', 'Acompanhamento', 'Contrato', 'Data_Monitoramento', 'Observacao']
    dados_tecnicos = dados_tecnicos.drop(columns=[c for c in colunas_remover if c in dados_tecnicos.columns], errors='ignore')

    dados_completos = dados_tecnicos.copy()
    
    todas_abas = [ws.title for ws in planilha.worksheets()]
    abas_meses = [aba for aba in todas_abas if aba not in ['Base_IQ', 'Base_Tecnicos', 'Controle_IQ']]
    
    meses_info = []

    for aba in abas_meses:
        df_mes = ler_aba(aba)
        if not df_mes.empty:
            mes_nome = aba.upper().replace('CERTIFICADO', '').replace('_', ' ').strip()
            if not mes_nome: mes_nome = aba.upper()
            
            colunas_novas = {}
            for c in df_mes.columns:
                c_up = str(c).strip().upper()
                if 'LOGIN' in c_up: colunas_novas[c] = 'LOGIN'
                elif 'RE' in c_up and 'IQ' in c_up: colunas_novas[c] = f'RE_IQ_{mes_nome}'
                elif 'ACOMPANHAMENTO' in c_up: colunas_novas[c] = f'ACOMPANHAMENTO_{mes_nome}'
                elif c_up in ['MONIT_1', 'M1']: colunas_novas[c] = f'MONIT_1_{mes_nome}'
                elif c_up in ['MONIT_2', 'M2']: colunas_novas[c] = f'MONIT_2_{mes_nome}'
                elif c_up in ['MONIT_3', 'M3']: colunas_novas[c] = f'MONIT_3_{mes_nome}'
                else:
                    if mes_nome in c_up or c_up in mes_nome:
                        colunas_novas[c] = mes_nome
            
            df_mes = df_mes.rename(columns=colunas_novas)
            
            if 'LOGIN' in df_mes.columns:
                df_mes['LOGIN'] = df_mes['LOGIN'].astype(str).str.strip().str.replace(r'\.0$', '', regex=True)
                
                if f'RE_IQ_{mes_nome}' in df_mes.columns:
                    df_mes[f'RE_IQ_{mes_nome}'] = df_mes[f'RE_IQ_{mes_nome}'].astype(str).str.strip().str.replace(r'\.0$', '', regex=True)
                
                if mes_nome not in df_mes.columns: df_mes[mes_nome] = 'NÃO'
                if f'ACOMPANHAMENTO_{mes_nome}' not in df_mes.columns: df_mes[f'ACOMPANHAMENTO_{mes_nome}'] = 'NÃO'
                if f'MONIT_1_{mes_nome}' not in df_mes.columns: df_mes[f'MONIT_1_{mes_nome}'] = 'NÃO'
                if f'MONIT_2_{mes_nome}' not in df_mes.columns: df_mes[f'MONIT_2_{mes_nome}'] = 'NÃO'
                if f'MONIT_3_{mes_nome}' not in df_mes.columns: df_mes[f'MONIT_3_{mes_nome}'] = 'NÃO'
                
                df_mes[mes_nome] = df_mes[mes_nome].fillna('NÃO').astype(str).str.strip().str.upper()
                df_mes[f'ACOMPANHAMENTO_{mes_nome}'] = df_mes[f'ACOMPANHAMENTO_{mes_nome}'].fillna('NÃO').astype(str).str.strip().str.upper()
                df_mes[f'MONIT_1_{mes_nome}'] = df_mes[f'MONIT_1_{mes_nome}'].fillna('NÃO').astype(str).str.strip().str.upper()
                df_mes[f'MONIT_2_{mes_nome}'] = df_mes[f'MONIT_2_{mes_nome}'].fillna('NÃO').astype(str).str.strip().str.upper()
                df_mes[f'MONIT_3_{mes_nome}'] = df_mes[f'MONIT_3_{mes_nome}'].fillna('NÃO').astype(str).str.strip().str.upper()
                
                dados_completos = pd.merge(dados_completos, df_mes, left_on='login', right_on='LOGIN', how='left')
                
                if 'LOGIN' in dados_completos.columns:
                    dados_completos = dados_completos.drop(columns=['LOGIN'])
                    
                meses_info.append({'nome_aba': aba, 'mes_nome': mes_nome})

    dados_completos = dados_completos.fillna('')
    dados_completos = dados_completos.replace(['nan', 'None', 'NaN'], '')

    return dados_iqs, dados_completos, meses_info

def carregar_controle_iq():
    try:
        ws = conectar_planilha().worksheet("Controle_IQ")
        registros = ws.get_all_records()
        return pd.DataFrame(registros) if registros else pd.DataFrame()
    except:
        return pd.DataFrame()

def salvar_horas_no_sheets(re_iq, meta, realizado):
    try:
        planilha = conectar_planilha()
        try:
            ws = planilha.worksheet("Controle_IQ")
        except:
            ws = planilha.add_worksheet(title="Controle_IQ", rows=100, cols=10)
            ws.append_row(["RE_IQ", "META_HORAS", "REALIZADO_HORAS", "AGENDA_TECNICO", "AGENDA_DATA", "AGENDA_IQ_NOME"])
            
        registros = ws.get_all_records()
        encontrou = False
        for idx, row in enumerate(registros):
            if str(row.get('RE_IQ', '')).strip().replace('.0', '') == str(re_iq):
                ws.update_cell(idx + 2, 2, meta)
                ws.update_cell(idx + 2, 3, realizado)
                encontrou = True
                break
        if not encontrou:
            ws.append_row([str(re_iq), meta, realizado, "", "", ""])
        st.cache_data.clear()
    except Exception as e:
        st.error(f"Erro ao salvar horas: {e}")

def salvar_agenda_no_sheets(agenda_dict):
    try:
        planilha = conectar_planilha()
        ws = planilha.worksheet("Controle_IQ")
        registros = ws.get_all_records()
        
        for idx, row in enumerate(registros):
            ws.update_cell(idx + 2, 4, "")
            ws.update_cell(idx + 2, 5, "")
            ws.update_cell(idx + 2, 6, "")
            
        linha_atual = 2
        for tec, info in agenda_dict.items():
            ws.update_cell(linha_atual, 4, tec)
            ws.update_cell(linha_atual, 5, info['data'])
            ws.update_cell(linha_atual, 6, info['iq_nome'])
            linha_atual += 1
        st.cache_data.clear()
    except Exception as e:
        print(f"Erro ao salvar agenda: {e}")

def atualizar_celula_especifica(nome_aba, login_tecnico, coluna_alvo, valor):
    try:
        ws = conectar_planilha().worksheet(nome_aba)
        cabecalhos = [str(c).strip().upper() for c in ws.row_values(1)]
        col_idx = -1
        
        for i, c in enumerate(cabecalhos):
            if coluna_alvo.upper() in c:
                col_idx = i + 1
                break
                
        if col_idx == -1: return 
        
        col_login_idx = -1
        for i, c in enumerate(cabecalhos):
            if 'LOGIN' in c:
                col_login_idx = i + 1
                break
                
        if col_login_idx == -1: return
        
        coluna_logins = ws.col_values(col_login_idx)
        for row_idx, val in enumerate(coluna_logins):
            if str(val).strip().replace('.0', '') == str(login_tecnico).strip().replace('.0', ''):
                ws.update_cell(row_idx + 1, col_idx, valor)
                break
        st.cache_data.clear() # Limpa o cache para forçar a leitura nova do Sheets
    except Exception as e:
        st.error(f"Erro ao atualizar planilha: {e}")

def colorir_sim_nao(val):
    texto = str(val).strip().upper()
    if texto == 'SIM': return 'background-color: #d4edda; color: #155724; font-weight: bold;'
    elif texto == 'NÃO' or texto == 'NAO': return 'background-color: #f8d7da; color: #721c24; font-weight: bold;'
    return ''

dados_iqs, dados_completos, meses_info = carregar_dados()

# --- Definição dos Meses Vigente e de Acompanhamento ---
if meses_info:
    mes_vigente_info = meses_info[-1]
    mes_vigente = mes_vigente_info['mes_nome']
    
    if len(meses_info) >= 2:
        mes_acompanhamento_info = meses_info[-2]
        mes_acompanhamento = mes_acompanhamento_info['mes_nome']
        aba_acompanhamento = mes_acompanhamento_info['nome_aba']
    else:
        mes_acompanhamento = mes_vigente
        aba_acompanhamento = mes_vigente_info['nome_aba']
else:
    mes_vigente, aba_acompanhamento, mes_acompanhamento = None, None, None

# --- Carrega Agenda e Horas do Sheets para a Sessão ---
df_ctrl = carregar_controle_iq()
if 'agenda_matinal' not in st.session_state:
    st.session_state['agenda_matinal'] = {}
    if not df_ctrl.empty:
        for _, row in df_ctrl.iterrows():
            tec = str(row.get('AGENDA_TECNICO', '')).strip()
            data = str(row.get('AGENDA_DATA', '')).strip()
            iq_nome = str(row.get('AGENDA_IQ_NOME', '')).strip()
            if tec and tec != '':
                st.session_state['agenda_matinal'][tec] = {'data': data, 'iq_nome': iq_nome}

# --- 3. Telas ---
if not st.session_state['logado']:
    col_logo, _ = st.columns([1, 2])
    with col_logo:
        if os.path.exists("novo-logo-totale.png"): st.image(Image.open("novo-logo-totale.png"), use_container_width=True)
            
    st.title("Acesso Operacional - Totale")
    
    with st.form("form_login"):
        re_input = st.text_input("RE (Login)")
        senha_input = st.text_input("Senha", type="password")
        btn_entrar = st.form_submit_button("Entrar", type="primary")

    if btn_entrar:
        iq_valido = dados_iqs[(dados_iqs['re_iq'] == re_input.strip()) & (dados_iqs['senha'] == senha_input.strip())]
        if not iq_valido.empty:
            st.session_state['logado'] = True
            st.session_state['re_usuario'] = re_input.strip()
            st.session_state['nome_iq'] = iq_valido.iloc[0]['nome_iq']
            st.session_state['perfil'] = iq_valido.iloc[0]['PERFIL']
            st.rerun()
        else:
            st.error("RE ou Senha incorretos.")

else:
    re_logado = st.session_state['re_usuario']
    re_logado_str = str(re_logado).strip().replace('.0', '')
    perfil_usuario = st.session_state.get('perfil', 'IQ')

    meta_atual, realizado_atual = 40, 0
    if not df_ctrl.empty:
        filtro_h = df_ctrl[df_ctrl['RE_IQ'].astype(str).str.strip().str.replace('.0','') == re_logado_str]
        if not filtro_h.empty:
            try: meta_atual = int(filtro_h.iloc[0]['META_HORAS'])
            except: pass
            try: realizado_atual = int(filtro_h.iloc[0]['REALIZADO_HORAS'])
            except: pass

    if re_logado_str not in st.session_state.get('horas_por_iq', {}):
        if 'horas_por_iq' not in st.session_state: st.session_state['horas_por_iq'] = {}
        st.session_state['horas_por_iq'][re_logado_str] = {'meta': meta_atual, 'realizadas': realizado_atual}

    if perfil_usuario == 'GESTÃO':
        st.sidebar.divider()
        st.sidebar.subheader("🎛️ Filtro de Gestão")
        lista_iqs = dados_iqs[dados_iqs['PERFIL'] != 'GESTÃO'][['re_iq', 'nome_iq']].drop_duplicates()
        opcoes_iq = ["Visão Geral (Todos)"] + [f"{row['re_iq']} - {row['nome_iq']}" for _, row in lista_iqs.iterrows()]
        
        iq_selecionado = st.sidebar.selectbox("Visualizar painel do IQ:", opcoes_iq)
        
        if "Visão Geral" in iq_selecionado:
            equipe_vigente = dados_completos
            re_alvo_str = None
        else:
            re_alvo_str = iq_selecionado.split(" - ")[0].strip()
            equipe_vigente = dados_completos[dados_completos['re_iq_responsavel'] == re_alvo_str]
    else:
        equipe_vigente = dados_completos[dados_completos['re_iq_responsavel'] == re_logado_str]
        re_alvo_str = re_logado_str

    with st.sidebar:
        if os.path.exists("novo-logo-totale.png"): st.image(Image.open("novo-logo-totale.png"), use_container_width=True)
        st.write(f"**Usuário:** {st.session_state['nome_iq']}")
        st.write(f"**Perfil:** {perfil_usuario}")
        st.divider()
        
        if st.button("📊 Dashboard Inicial", use_container_width=True): 
            st.session_state['pagina_atual'] = "Dashboard"
            st.rerun()
        if st.button("🏆 Histórico de Certificados", use_container_width=True): 
            st.session_state['pagina_atual'] = "Historico"
            st.rerun()
        if st.button("📋 Agendamento de Matinal", use_container_width=True): 
            st.session_state['pagina_atual'] = "Matinal"
            st.rerun()
            
        st.divider()
        if st.button("Sair", use_container_width=True):
            st.session_state['logado'] = False
            st.rerun()

    # --- PÁGINA 1: DASHBOARD ---
    if st.session_state['pagina_atual'] == "Dashboard":
        titulo_painel = f"Painel Operacional - {st.session_state['nome_iq']}"
        if perfil_usuario == 'GESTÃO' and 're_alvo_str' in locals() and re_alvo_str:
            nome_iq_filtro = dados_iqs[dados_iqs['re_iq'] == re_alvo_str]['nome_iq'].values
            if nome_iq_filtro: titulo_painel = f"Painel Operacional (Visão: {nome_iq_filtro[0]})"
        
        st.title(titulo_painel)
        st.write("")

        re_alvo_horas = re_alvo_str if (perfil_usuario == 'GESTÃO' and re_alvo_str) else re_logado_str
        if re_alvo_horas not in st.session_state['horas_por_iq']:
            st.session_state['horas_por_iq'][re_alvo_horas] = {'meta': meta_atual, 'realizadas': realizado_atual}

        col1, col2, col3 = st.columns(3)
        
        # CARD 1: % CERTIFICADOS (Azul)
        with col1:
            st.markdown('<div class="metric-card-blue">', unsafe_allow_html=True)
            st.markdown('<div class="metric-title">🏆 % Certificados</div>', unsafe_allow_html=True)
            
            if meses_info:
                lista_meses = [m['mes_nome'] for m in meses_info]
                mes_selecionado = st.selectbox("Selecione o Mês:", lista_meses, index=len(lista_meses)-1, key="sel_mes_card")
                
                col_re_mes = f"RE_IQ_{mes_selecionado}"
                if perfil_usuario == 'GESTÃO' and (not locals().get('re_alvo_str') or re_alvo_str is None):
                    base_calc_mes = dados_completos
                else:
                    target_re = re_alvo_str if perfil_usuario == 'GESTÃO' else re_logado_str
                    if col_re_mes in dados_completos.columns:
                        base_calc_mes = dados_completos[dados_completos[col_re_mes].astype(str) == target_re]
                    else:
                        base_calc_mes = pd.DataFrame()
                
                if not base_calc_mes.empty and mes_selecionado in base_calc_mes.columns:
                    filtro_validos = (base_calc_mes[mes_selecionado] != '')
                    base_mes_valida = base_calc_mes[filtro_validos]
                    total_mes = len(base_mes_valida)
                    sim_mes = len(base_mes_valida[base_mes_valida[mes_selecionado].astype(str).str.upper() == 'SIM'])
                    pct_mes = round((sim_mes / total_mes * 100), 1) if total_mes > 0 else 0
                    
                    st.markdown(f'<div class="metric-value">{pct_mes}% SIM</div>', unsafe_allow_html=True)
                    st.markdown(f'<div class="metric-sub">Base: {total_mes} Técnicos ({mes_selecionado})</div>', unsafe_allow_html=True)
                else:
                    st.markdown('<div class="metric-value">0% SIM</div>', unsafe_allow_html=True)
                    st.markdown('<div class="metric-sub">Sem técnicos vinculados</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="metric-value">N/A</div>', unsafe_allow_html=True)
                st.markdown('<div class="metric-sub">Sem abas mensais</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

        # CARD 2: HORAS DE MONITORIA (Verde)
        with col2:
            st.markdown('<div class="metric-card-green">', unsafe_allow_html=True)
            st.markdown('<div class="metric-title">⏱️ Horas de Monitoria</div>', unsafe_allow_html=True)
            
            if perfil_usuario == 'GESTÃO':
                meta_input = st.number_input("Meta de Horas:", value=st.session_state['horas_por_iq'][re_alvo_horas]['meta'], step=1, key=f"meta_{re_alvo_horas}")
                real_input = st.number_input("Horas Realizadas:", value=st.session_state['horas_por_iq'][re_alvo_horas]['realizadas'], step=1, key=f"real_{re_alvo_horas}")
                
                if meta_input != st.session_state['horas_por_iq'][re_alvo_horas]['meta'] or real_input != st.session_state['horas_por_iq'][re_alvo_horas]['realizadas']:
                    st.session_state['horas_por_iq'][re_alvo_horas]['meta'] = meta_input
                    st.session_state['horas_por_iq'][re_alvo_horas]['realizadas'] = real_input
                    salvar_horas_no_sheets(re_alvo_horas, meta_input, real_input)
            else:
                st.markdown(f'<div class="metric-value">Meta: {st.session_state["horas_por_iq"][re_alvo_horas]["meta"]}h</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="metric-value" style="font-size:20px; margin-top:5px;">Realizado: {st.session_state["horas_por_iq"][re_alvo_horas]["realizadas"]}h</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="metric-sub">Controle individual de horas</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

        # CARD 3: PENDENTES DE MONITORAMENTO (Laranja)
        with col3:
            st.markdown('<div class="metric-card-orange">', unsafe_allow_html=True)
            st.markdown('<div class="metric-title">⚠️ Monitoramento Pendente</div>', unsafe_allow_html=True)
            
            if mes_acompanhamento:
                pendentes_hoje = len(equipe_vigente[(equipe_vigente[mes_acompanhamento] == 'NÃO') & (equipe_vigente[f'ACOMPANHAMENTO_{mes_acompanhamento}'] != 'SIM')])
                st.markdown(f'<div class="metric-value">{pendentes_hoje} Técnicos</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="metric-sub">Referência: {mes_acompanhamento}</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="metric-value">N/A</div>', unsafe_allow_html=True)
                st.markdown('<div class="metric-sub">Sem base mensal</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

        st.divider()
        
        # --- AGENDA DE MATINAIS ---
        st.subheader("📅 Agendamento de Matinais")
        if not st.session_state['agenda_matinal']:
            st.info("Nenhuma matinal agendada.")
        else:
            for tec, info in list(st.session_state['agenda_matinal'].items()):
                st.write(f"📌 **Data:** {info['data']} | **Técnico:** {tec} | **IQ Responsável:** {info['iq_nome']}")

        st.divider()
        
        # --- ACOMPANHAMENTO PENDENTE (MÍNIMO DE 3 MONITORIAS COM TICKETS) ---
        st.subheader(f"⚠️ Acompanhamento Pendente (Referência: {mes_acompanhamento or 'N/A'})")
        st.write(f"*Marque as caixas conforme realizar cada monitoria (1, 2 e 3). Ao completar as 3, o status mudará para SIM automaticamente.*")
        
        if mes_acompanhamento:
            tecnicos_nao_cert = equipe_vigente[(equipe_vigente[mes_acompanhamento] == 'NÃO') & (equipe_vigente[f'ACOMPANHAMENTO_{mes_acompanhamento}'] != 'SIM')]
            
            if tecnicos_nao_cert.empty:
                st.success(f"Todos os técnicos pendentes de {mes_acompanhamento} já concluíram as monitorias.")
            else:
                for index, row in tecnicos_nao_cert.iterrows():
                    tec_login = row['login']
                    tec_nome = row['nome']
                    iq_resp = row['re_iq_responsavel']
                    
                    nome_iq_resp = iq_resp
                    match_iq = dados_iqs[dados_iqs['re_iq'] == iq_resp]
                    if not match_iq.empty: nome_iq_resp = match_iq.iloc[0]['nome_iq']

                    # Lê o estado atual direto da base lida do Sheets
                    m1_val = str(row.get(f'MONIT_1_{mes_acompanhamento}', '')).upper() == 'SIM'
                    m2_val = str(row.get(f'MONIT_2_{mes_acompanhamento}', '')).upper() == 'SIM'
                    m3_val = str(row.get(f'MONIT_3_{mes_acompanhamento}', '')).upper() == 'SIM'
                    concluidas = sum([m1_val, m2_val, m3_val])

                    with st.container():
                        c_info, c_m1, c_m2, c_m3, c_status = st.columns([3, 1, 1, 1, 1])
                        c_info.write(f"👤 **{tec_nome}** (IQ: {nome_iq_resp})")
                        
                        novo_m1 = c_m1.checkbox("Monit. 1", value=m1_val, key=f"m1_{tec_login}")
                        novo_m2 = c_m2.checkbox("Monit. 2", value=m2_val, key=f"m2_{tec_login}")
                        novo_m3 = c_m3.checkbox("Monit. 3", value=m3_val, key=f"m3_{tec_login}")
                        
                        c_status.markdown(f"**{concluidas}/3**")
                        
                        if novo_m1 != m1_val:
                            atualizar_celula_especifica(aba_acompanhamento, tec_login, 'MONIT_1', 'SIM' if novo_m1 else 'NÃO')
                            if novo_m1 and novo_m2 and novo_m3:
                                atualizar_celula_especifica(aba_acompanhamento, tec_login, 'ACOMPANHAMENTO', 'SIM')
                            st.rerun()
                        if novo_m2 != m2_val:
                            atualizar_celula_especifica(aba_acompanhamento, tec_login, 'MONIT_2', 'SIM' if novo_m2 else 'NÃO')
                            if novo_m1 and novo_m2 and novo_m3:
                                atualizar_celula_especifica(aba_acompanhamento, tec_login, 'ACOMPANHAMENTO', 'SIM')
                            st.rerun()
                        if novo_m3 != m3_val:
                            atualizar_celula_especifica(aba_acompanhamento, tec_login, 'MONIT_3', 'SIM' if novo_m3 else 'NÃO')
                            if novo_m1 and novo_m2 and novo_m3:
                                atualizar_celula_especifica(aba_acompanhamento, tec_login, 'ACOMPANHAMENTO', 'SIM')
                            st.rerun()
                            
                        st.divider()
        else:
            st.info("Crie abas de certificados mensais para habilitar o acompanhamento.")

    # --- PÁGINA 2: HISTÓRICO DE CERTIFICADOS ---
    elif st.session_state['pagina_atual'] == "Historico":
        st.title(f"🏆 Histórico de Certificados")
        
        if not meses_info:
            st.warning("Nenhuma aba de certificação encontrada no Google Sheets.")
        else:
            lista_meses = [m['mes_nome'] for m in meses_info]
            mes_historico = st.selectbox("📅 Escolha o Mês para visualizar:", lista_meses, index=len(lista_meses)-1)
            
            col_re_hist = f"RE_IQ_{mes_historico}"
            
            if perfil_usuario == 'GESTÃO':
                base_historico = dados_completos
            else:
                if col_re_hist in dados_completos.columns:
                    base_historico = dados_completos[dados_completos[col_re_hist].astype(str) == re_logado_str]
                else:
                    base_historico = pd.DataFrame()

            if base_historico.empty:
                st.info(f"Você não possui técnicos vinculados ao seu RE no mês de {mes_historico}.")
            else:
                colunas_exibir = ['login', 'nome', mes_historico]
                if f"RE_IQ_{mes_historico}" in base_historico.columns: colunas_exibir.append(f"RE_IQ_{mes_historico}")
                if f"ACOMPANHAMENTO_{mes_historico}" in base_historico.columns: colunas_exibir.append(f"ACOMPANHAMENTO_{mes_historico}")

                df_exibir = base_historico[[c for c in colunas_exibir if c in base_historico.columns]].copy()
                
                renomear_cols = {
                    'login': 'Login', 
                    'nome': 'Nome do Técnico',
                    mes_historico: 'Status Certificação',
                    f"RE_IQ_{mes_historico}": 'RE do IQ (Mês)',
                    f"ACOMPANHAMENTO_{mes_historico}": 'Monitoria Concluída?'
                }
                df_exibir = df_exibir.rename(columns=renomear_cols)

                st.dataframe(df_exibir.style.map(colorir_sim_nao), hide_index=True, use_container_width=True)

    # --- PÁGINA 3: MATINAL ---
    elif st.session_state['pagina_atual'] == "Matinal":
        st.title("📋 Agendamento e Execução da Matinal")
        tab_agendar, tab_executar = st.tabs(["1. Agendar Téc", "2. Executar Vistoria (Checklist)"])
        
        with tab_agendar:
            col_a1, col_a2 = st.columns(2)
            with col_a1:
                tec_agendar = st.selectbox("Selecione o Técnico:", ["Selecione..."] + equipe_vigente['nome'].tolist())
            with col_a2:
                data_agendada = st.date_input("Escolha o Dia:", value=None, format="DD/MM/YYYY")
                
            if st.button("Adicionar à Agenda", type="primary"):
                if tec_agendar != "Selecione..." and data_agendada is not None:
                    st.session_state['agenda_matinal'][tec_agendar] = {
                        'data': data_agendada.strftime("%d/%m/%Y"),
                        'iq_nome': st.session_state['nome_iq']
                    }
                    salvar_agenda_no_sheets(st.session_state['agenda_matinal'])
                    st.success(f"Matinal agendada para {tec_agendar}!")
                    st.rerun()
            
            st.write("---")
            st.write("**Agenda de Matinais Cadastradas:**")
            if not st.session_state['agenda_matinal']:
                st.info("Nenhuma matinal agendada.")
            else:
                for tec, info in list(st.session_state['agenda_matinal'].items()):
                    c1, c2 = st.columns([4, 1])
                    c1.write(f"📌 **Data:** {info['data']} | **Técnico:** {tec} | **IQ:** {info['iq_nome']}")
                    if c2.button("🗑️ Remover", key=f"rm_{tec}"):
                        del st.session_state['agenda_matinal'][tec]
                        salvar_agenda_no_sheets(st.session_state['agenda_matinal'])
                        st.rerun()

        with tab_executar:
            if st.session_state['email_pronto']:
                st.success("✅ Matinal gravada com sucesso! O Relatório está pronto.")
                st.markdown(f'<a href="{st.session_state["email_pronto"]}" target="_blank" style="display: inline-block; padding: 0.8em 1.5em; color: white; background-color: #007BFF; border-radius: 8px; text-decoration: none; font-weight: bold; font-size: 16px;">📩 ABRIR E-MAIL COM O RELATÓRIO</a>', unsafe_allow_html=True)
                st.write("")
                if st.button("🧹 Limpar Tela e Voltar para Agenda"):
                    st.session_state['email_pronto'] = None
                    st.rerun()
            else:
                tec_atual = st.selectbox("Selecione o Téc na Agenda para Vistoriar:", ["Selecione..."] + list(st.session_state['agenda_matinal'].keys()))
                
                if tec_atual != "Selecione...":
                    st.info("⚠️ Assinale abaixo os itens que estão **FALTANDO** ou **IRREGULARES**.")
                    faltas = []
                    
                    t1, t2, t3, t4, t5 = st.tabs(["🛠️ Ferramental", "📡 GPON / Fibra", "👷 EPI / EPC", "🧹 Asseio", "🚗 Veículo / Outros"])
                    
                    with t1:
                        c1, c2, c3 = st.columns(3)
                        ferramentas_1 = ['Alicate Crimpador RG59/58', 'Alicate Crimpador RJ11/45', 'Alicate de Bico Reto 6"', 'Alicate Corte Diagonal 6"', 'Alicate Universal 8"', 'Chaves de Fenda (G/M/P)', 'Chaves Phillips (G/M/P)', 'Chave Trava Lock / GTP', 'Chave Torque / BQ']
                        ferramentas_2 = ['Estilete 18mm', 'Organizador de Ferramentas', 'Striper RG59/58', 'Fita Guia de Nylon 20m', 'Martelo Unha', 'Fuzimec (Cintadeira)', 'Furadeira de Impacto', 'Extensão Elétrica 10a20m']
                        ferramentas_3 = ['Broca de Wídea 8" e 10"', 'Mala de Ferramentas', 'Balde de Lona (Bornal)', 'Telefone Gôndola', 'Lanterna', 'Escada Fibra 6m', 'Escada 4/5 Degraus', 'Câmera Sonda Endoscópica', 'Chaveiro Mini Isolator']
                        
                        for item in ferramentas_1: 
                            if c1.checkbox(item): faltas.append(item)
                        for item in ferramentas_2: 
                            if c2.checkbox(item): faltas.append(item)
                        for item in ferramentas_3: 
                            if c3.checkbox(item): faltas.append(item)

                    with t2:
                        cg1, cg2 = st.columns(2)
                        gpon_1 = ['Clivador c/ Gabarito Profiber', 'Gabarito de Conectorização', 'Alicate Decapador Fibra', 'Alicate Decapador Drop', 'Suporte de Escada p/ Clivador', 'Suporte p/ Bobina', 'Testador Cabo de Rede', 'Kit LVM']
                        gpon_2 = ['Caneta de Limpeza Óptica', 'Caneta Óptica (Laser)', 'Kit Lenços p/ Limpeza AGC', 'Álcool Isopropílico', 'Dispenser p/ Líquidos', 'DBAM / Trilithic', 'Power Meter']
                        
                        for item in gpon_1:
                            if cg1.checkbox(item): faltas.append(item)
                        for item in gpon_2:
                            if cg2.checkbox(item): faltas.append(item)

                    with t3:
                        ce1, ce2 = st.columns(2)
                        epi_1 = ['Capacete c/ Aba e Jugular', 'Capa de Chuva', 'Cinto de Segurança', 'Talabarte de Segurança', 'Manta de Proteção', 'Luvas Pigmentada', 'Luvas Vaqueta', 'Óculos de Proteção']
                        epi_2 = ['3 Cones', 'Bandeirola p/ Escada', 'Nivelador de Escada', 'Multímetro / Chave Teste', 'Máscara Semifacial', 'Rolo Fita Zebrada', 'Protetor Solar', 'Pro-Pé']
                        
                        for item in epi_1:
                            if ce1.checkbox(item): faltas.append(item)
                        for item in epi_2:
                            if ce2.checkbox(item): faltas.append(item)
                            
                    with t4:
                        ca1, ca2 = st.columns(2)
                        asseio_1 = ['Barba Feita', 'Higiene Pessoal', 'Corte de Cabelo Padrão', 'Uso de Adornos (Irregular)']
                        asseio_2 = ['Camiseta', 'Calça', 'Bota', 'Cinto Pessoal', 'Jaqueta', 'Crachá']
                        
                        for item in asseio_1:
                            if ca1.checkbox(item): faltas.append(item)
                        for item in asseio_2:
                            if ca2.checkbox(item): faltas.append(item)

                    with t5:
                        cv1, cv2 = st.columns(2)
                        veiculo_1 = ['Limpeza do Veículo', 'Organização do Veículo', 'Avarias no Veículo']
                        veiculo_2 = ['PDA (Logado / Bat > 50%)', 'Book Fiscal', 'Flanela', 'Chip de Telefonia', 'Escova e Pá de Lixo']
                        
                        for item in veiculo_1:
                            if cv1.checkbox(item): faltas.append(item)
                        for item in veiculo_2:
                            if cv2.checkbox(item): faltas.append(item)

                    st.divider()
                    foto_upload = st.file_uploader("📸 Anexar Foto da Vistoria", type=['png', 'jpg'])
                    obs_final = st.text_area("Observações da Tratativa:")

                    resumo_faltas = "\n- ".join(faltas) if faltas else "Todas as ferramentas e condições em conformidade."
                    corpo_email = f"RELATÓRIO DE MATINAL (IVM 2026)\nTécnico: {tec_atual}\nIQ: {st.session_state['nome_iq']}\n\nITENS FALTANTES/IRREGULARES:\n- {resumo_faltas}\n\nOBSERVAÇÕES DA TRATATIVA:\n{obs_final}"
                    url_email = f"mailto:?subject=Relatorio Matinal - {tec_atual}&body={urllib.parse.quote(corpo_email)}"

                    if st.button("Gravar Vistoria e Gerar E-mail", type="primary"):
                        if not foto_upload:
                            st.warning("⚠️ O envio da foto é obrigatório para comprovação.")
                        else:
                            tec_login = equipe_vigente[equipe_vigente['nome'] == tec_atual]['login'].iloc[0]
                            if aba_acompanhamento:
                                atualizar_celula_especifica(aba_acompanhamento, tec_login, 'ACOMPANHAMENTO', 'SIM')
                            del st.session_state['agenda_matinal'][tec_atual]
                            salvar_agenda_no_sheets(st.session_state['agenda_matinal'])
                            st.session_state['email_pronto'] = url_email
                            st.rerun()
