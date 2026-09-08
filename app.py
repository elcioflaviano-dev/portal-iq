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

# Variáveis de Sessão
if 'logado' not in st.session_state: st.session_state['logado'] = False
if 'pagina_atual' not in st.session_state: st.session_state['pagina_atual'] = "Dashboard"
if 'agenda_matinal' not in st.session_state: st.session_state['agenda_matinal'] = {}

# --- 2. Conexão com Google Sheets ---
def conectar_planilha():
    try:
        # Puxa o JSON salvo nos Secrets do Streamlit
        creds_dict = json.loads(st.secrets["gcp_service_account"])
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        return client.open("PORTAL IQ")
    except Exception as e:
        st.error(f"Erro ao conectar com o Google Sheets. Verifique se o e-mail do robô foi adicionado como Editor na planilha. Detalhe: {e}")
        st.stop()

# Função para ler os dados (com cache de 60 segundos)
@st.cache_data(ttl=60)
def carregar_dados():
    planilha = conectar_planilha()
    
    # Função auxiliar para ler abas evitando erro de aba vazia
    def ler_aba(nome_aba):
        try:
            registros = planilha.worksheet(nome_aba).get_all_records()
            if not registros: return pd.DataFrame()
            return pd.DataFrame(registros)
        except:
            return pd.DataFrame()
            
    dados_iqs = ler_aba("Base_IQ")
    dados_tecnicos = ler_aba("Base_Tecnicos")
    dados_certificados = ler_aba("Certificados")
    
    # Se a base principal estiver vazia, para o sistema com um aviso amigável
    if dados_iqs.empty or dados_tecnicos.empty:
        st.error("A planilha do Google está vazia ou sem cabeçalhos. Preencha a Base_IQ e Base_Tecnicos.")
        st.stop()
    
    # Padronização e Limpeza
    dados_iqs['re_iq'] = dados_iqs['re_iq'].astype(str).str.strip().str.replace('.0', '', regex=False)
    dados_iqs['senha'] = dados_iqs.get('senha', '').astype(str).str.strip()
    dados_iqs['PERFIL'] = dados_iqs.get('PERFIL', 'IQ').astype(str).str.strip().str.upper()
    
    dados_tecnicos['login'] = dados_tecnicos.get('login', '').astype(str).str.strip().str.replace('.0', '', regex=False)
    dados_tecnicos['re_iq_responsavel'] = dados_tecnicos.get('re_iq_responsavel', '').astype(str).str.strip().str.replace('.0', '', regex=False)
    dados_tecnicos['status_certificacao'] = dados_tecnicos.get('status_certificacao', 'NÃO').astype(str).str.strip().str.upper()
    dados_tecnicos['Acompanhamento'] = dados_tecnicos.get('Acompanhamento', 'NÃO').astype(str).str.strip().str.upper()

    if not dados_certificados.empty and 'LOGIN' in dados_certificados.columns:
        dados_certificados['LOGIN'] = dados_certificados['LOGIN'].astype(str).str.strip().str.replace('.0', '', regex=False)
        dados_completos = pd.merge(dados_tecnicos, dados_certificados, left_on='login', right_on='LOGIN', how='left')
    else:
        dados_completos = dados_tecnicos
        
    return dados_iqs, dados_completos

# Funções para SALVAR dados no Google Sheets em tempo real
def salvar_nova_senha(re_usuario, nova_senha):
    ws = conectar_planilha().worksheet("Base_IQ")
    registros = ws.get_all_records()
    for idx, row in enumerate(registros):
        if str(row.get('re_iq', '')).strip().replace('.0','') == str(re_usuario):
            col_idx = list(row.keys()).index('senha') + 1
            ws.update_cell(idx + 2, col_idx, nova_senha) # +2 por causa do cabeçalho
            break
    st.cache_data.clear() 

def atualizar_acompanhamento(login_tecnico, status, contrato="", data_mon="", obs=""):
    ws = conectar_planilha().worksheet("Base_Tecnicos")
    registros = ws.get_all_records()
    for idx, row in enumerate(registros):
        if str(row.get('login', '')).strip().replace('.0','') == str(login_tecnico):
            if 'Acompanhamento' in row:
                ws.update_cell(idx + 2, list(row.keys()).index('Acompanhamento') + 1, status)
            if 'Contrato' in row: 
                ws.update_cell(idx + 2, list(row.keys()).index('Contrato') + 1, contrato)
            if 'Data_Monitoramento' in row: 
                ws.update_cell(idx + 2, list(row.keys()).index('Data_Monitoramento') + 1, data_mon)
            if 'Observacao' in row: 
                ws.update_cell(idx + 2, list(row.keys()).index('Observacao') + 1, obs)
            break
    st.cache_data.clear()

# Helpers Visuais
def colorir_sim_nao(val):
    if val == 'SIM': return 'background-color: #d4edda; color: #155724; font-weight: bold;'
    elif val == 'NÃO': return 'background-color: #f8d7da; color: #721c24; font-weight: bold;'
    return ''

# Carregamento Principal
dados_iqs, dados_completos = carregar_dados()

# --- 3. Tela de Login e Alteração de Senha ---
if not st.session_state['logado']:
    col_logo, _ = st.columns([1, 2])
    with col_logo:
        if os.path.exists("novo-logo-totale.png"):
            st.image(Image.open("novo-logo-totale.png"), use_container_width=True)
            
    st.title("Acesso Operacional - Totale")
    
    tab_login, tab_senha = st.tabs(["🔑 Fazer Login", "🔄 Alterar Senha"])
    
    with tab_login:
        re_input = st.text_input("RE (Login)")
        senha_input = st.text_input("Senha", type="password")
        if st.button("Entrar", type="primary"):
            iq_valido = dados_iqs[(dados_iqs['re_iq'] == re_input.strip()) & (dados_iqs['senha'] == senha_input.strip())]
            if not iq_valido.empty:
                st.session_state['logado'] = True
                st.session_state['re_usuario'] = re_input.strip()
                st.session_state['nome_iq'] = iq_valido.iloc[0]['nome_iq']
                st.session_state['perfil'] = iq_valido.iloc[0]['PERFIL']
                st.rerun()
            else:
                st.error("RE ou Senha incorretos.")
                
    with tab_senha:
        st.info("Para alterar sua senha, confirme seu RE e sua senha atual.")
        re_esqueci = st.text_input("Seu RE", key="re_esqueci")
        senha_atual = st.text_input("Senha Atual (ou Provisória)", type="password", key="senha_atual")
        senha_nova = st.text_input("Nova Senha", type="password", key="senha_nova")
        if st.button("Salvar Nova Senha"):
            iq_valido = dados_iqs[(dados_iqs['re_iq'] == re_esqueci.strip()) & (dados_iqs['senha'] == senha_atual.strip())]
            if not iq_valido.empty:
                salvar_nova_senha(re_esqueci.strip(), senha_nova.strip())
                st.success("Senha alterada com sucesso no Google Sheets! Você já pode fazer login.")
            else:
                st.error("RE ou Senha atual não conferem.")

# --- 4. Sistema Principal ---
else:
    if st.session_state.get('perfil') == 'GESTÃO':
        equipe_iq = dados_completos
    else:
        equipe_iq = dados_completos[dados_completos['re_iq_responsavel'] == st.session_state['re_usuario']]

    # SIDEBAR
    with st.sidebar:
        if os.path.exists("novo-logo-totale.png"):
            st.image(Image.open("novo-logo-totale.png"), use_container_width=True)
        st.write(f"**Usuário:** {st.session_state['nome_iq']}")
        st.divider()
        if st.button("📊 Dashboard Inicial", use_container_width=True): st.session_state['pagina_atual'] = "Dashboard"; st.rerun()
        if st.button("📅 Agenda e Matinal", use_container_width=True): st.session_state['pagina_atual'] = "Matinal"; st.rerun()
        st.divider()
        if st.button("Sair", use_container_width=True):
            st.session_state['logado'] = False
            st.rerun()

    # --- DASHBOARD ---
    if st.session_state['pagina_atual'] == "Dashboard":
        st.title(f"Painel IQ - {st.session_state['nome_iq']}")
        
        colunas_exibicao = ['login', 'nome', 'status_certificacao', 'Acompanhamento']
        colunas_meses = [col for col in equipe_iq.columns if 'CERTIFICADO ' in str(col).upper()]
        colunas_exibicao.extend(colunas_meses)
        equipe_exibicao = equipe_iq[[col for col in colunas_exibicao if col in equipe_iq.columns]]
        
        st.subheader("✅ Técnicos Certificados (Histórico)")
        df_certificados = equipe_exibicao[equipe_exibicao['status_certificacao'] == 'SIM']
        if df_certificados.empty:
            st.info("Nenhum técnico certificado.")
        else:
            # Correção do applymap para map
            st.dataframe(df_certificados.style.map(colorir_sim_nao, subset=['status_certificacao']), hide_index=True, use_container_width=True)
        
        st.divider()
        st.subheader("⚠️ Técnicos em Monitoramento (Seleção Manual)")
        
        tecnicos_nao_cert_df = equipe_exibicao[equipe_exibicao['status_certificacao'] == 'NÃO']
        opcoes_tecnicos = tecnicos_nao_cert_df['nome'].tolist()
        
        tecnicos_selecionados = st.multiselect("Selecione os Técnicos para abrir o painel de Acompanhamento:", options=opcoes_tecnicos)
        
        if tecnicos_selecionados:
            for tec_nome in tecnicos_selecionados:
                tec_login = tecnicos_nao_cert_df[tecnicos_nao_cert_df['nome'] == tec_nome]['login'].iloc[0]
                with st.expander(f"👤 {tec_nome}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        contrato = st.text_input("Contrato Atual:", key=f"cont_{tec_login}")
                        # Correção para aceitar data vazia (value=None)
                        data_mon = st.date_input("Data do Monitoramento:", value=None, format="DD/MM/YYYY", key=f"data_{tec_login}")
                    with col2:
                        obs = st.text_area("Observações:", key=f"obs_{tec_login}")
                    
                    if st.button("Salvar Dados no Banco de Dados", key=f"btn_{tec_login}", type="primary"):
                        data_str = data_mon.strftime("%d/%m/%Y") if data_mon else ""
                        atualizar_acompanhamento(tec_login, "SIM", contrato, data_str, obs)
                        st.success("Dados salvos e status de Acompanhamento alterado para SIM na planilha!")

    # --- MATINAL ---
    elif st.session_state['pagina_atual'] == "Matinal":
        st.title("📅 Agendamento e Realização da Matinal")
        tab_agenda, tab_exec = st.tabs(["1. Agendar", "2. Executar Formulário"])
        
        with tab_agenda:
            st.subheader("Agendar nova Matinal")
            col_a1, col_a2 = st.columns(2)
            with col_a1:
                tec_agendar = st.selectbox("Técnico:", ["Selecione..."] + equipe_iq['nome'].tolist())
            with col_a2:
                # Correção para aceitar data vazia (value=None)
                data_agendada = st.date_input("Escolha o Dia e Mês:", value=None, format="DD/MM/YYYY")
                
            if st.button("Adicionar à Agenda Interna", type="primary"):
                if tec_agendar != "Selecione..." and data_agendada is not None:
                    st.session_state['agenda_matinal'][tec_agendar] = data_agendada.strftime("%d/%m/%Y")
                    st.success(f"Agendado para {data_agendada.strftime('%d/%m/%Y')}!")
                else:
                    st.warning("Selecione o técnico e preencha uma data válida.")
            
            st.divider()
            st.write("**Sua Agenda Atual:**")
            if not st.session_state['agenda_matinal']:
                st.info("Nenhuma matinal agendada.")
            else:
                for tec, data in st.session_state['agenda_matinal'].items():
                    st.write(f"📌 **{data}** - Técnico: {tec}")

        with tab_exec:
            tec_atual = st.selectbox("Selecione o Técnico para Iniciar a Vistoria:", ["Selecione..."] + list(st.session_state['agenda_matinal'].keys()))
            
            if tec_atual != "Selecione...":
                st.info("⚠️ Assinale **apenas o que estiver faltando ou irregular** no checklist.")
                faltas = []
                
                t1, t2, t3, t4, t5 = st.tabs(["Manuais", "Acessórios", "GPON/Fibra", "EPI/Segurança", "Veículo/Asseio"])
                
                with t1:
                    if st.checkbox("Alicates (Crimpador, Bico, Corte, Universal)"): faltas.append("Alicates faltantes")
                    if st.checkbox("Chaves de Fenda / Phillips (Todas)"): faltas.append("Chaves faltantes")
                    if st.checkbox("Chave Trava Lock / GTP Segurança"): faltas.append("Chaves de segurança")
                    if st.checkbox("Estilete / Striper / Martelo"): faltas.append("Estilete/Striper/Martelo")
                with t2:
                    if st.checkbox("Fita Guia / Fuzimec"): faltas.append("Fita Guia/Fuzimec")
                    if st.checkbox("Furadeira e Brocas de Wídea"): faltas.append("Furadeira/Brocas")
                    if st.checkbox("Mala / Bornal / Lanterna"): faltas.append("Mala/Lanterna")
                    if st.checkbox("Escadas (Fibra 6m / 4 Degraus)"): faltas.append("Escada Inadequada")
                with t3:
                    if st.checkbox("Clivador / Gabaritos de Conector"): faltas.append("Clivador/Gabarito")
                    if st.checkbox("Alicate Decapador Fibra/Drop"): faltas.append("Alicate Óptico")
                    if st.checkbox("DBAM / Trilithic / Power Meter"): faltas.append("Medidores Ópticos")
                    if st.checkbox("Álcool Isopropílico / Dispenser / Lenços"): faltas.append("Kit Limpeza Fibra")
                with t4:
                    if st.checkbox("Capacete / Jugular"): faltas.append("Capacete")
                    if st.checkbox("Cinto Segurança / Talabarte"): faltas.append("Cinto/Talabarte")
                    if st.checkbox("Luvas / Óculos / Máscara"): faltas.append("Luvas/Óculos")
                    if st.checkbox("Cones / Bandeirola / Fita Zebrada"): faltas.append("Sinalização Visual")
                with t5:
                    if st.checkbox("Barba, Cabelo, Higiene / Adornos"): faltas.append("Higiene Pessoal")
                    if st.checkbox("Uniforme Incompleto / Sem Crachá"): faltas.append("Uniforme/Crachá")
                    if st.checkbox("Veículo (Sujo, Desorganizado ou com Avarias)"): faltas.append("Problemas no Veículo")
                    if st.checkbox("PDA (Deslogado ou Bateria < 50%)"): faltas.append("PDA Irregular")

                st.divider()
                foto_upload = st.file_uploader("📸 Enviar Foto Comprobatória", type=['png', 'jpg'])
                obs_final = st.text_area("Observações Finais:")
                
                resumo_faltas = ", ".join(faltas) if faltas else "Nenhuma irregularidade apontada."
                corpo_email = f"Matinal de {tec_atual}\nIQ: {st.session_state['nome_iq']}\n\nFALTAS/IRREGULARIDADES:\n{resumo_faltas}\n\nObs: {obs_final}"
                url_email = f"mailto:?subject=Matinal - {tec_atual}&body={urllib.parse.quote(corpo_email)}"

                if st.button("Concluir e Enviar E-mail", type="primary"):
                    if not foto_upload:
                        st.warning("⚠️ A foto é obrigatória.")
                    else:
                        tec_login = equipe_iq[equipe_iq['nome'] == tec_atual]['login'].iloc[0]
                        atualizar_acompanhamento(tec_login, "NÃO", obs=f"Matinal Concluída em {datetime.now().strftime('%d/%m/%Y')}")
                        del st.session_state['agenda_matinal'][tec_atual]
                        
                        st.success(f"Matinal de {tec_atual} concluída e gravada na planilha Google!")
                        st.markdown(f'📩 **[Clique aqui para enviar o relatório por E-mail]({url_email})**')
