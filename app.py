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
if 'agenda_matinal' not in st.session_state: st.session_state['agenda_matinal'] = {}
if 'horas_meta_geral' not in st.session_state: st.session_state['horas_meta_geral'] = 40
if 'email_pronto' not in st.session_state: st.session_state['email_pronto'] = None

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

@st.cache_data(ttl=60)
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
    
    # Padronização Base
    dados_iqs['re_iq'] = dados_iqs['re_iq'].astype(str).str.strip().str.replace('.0', '', regex=False)
    dados_iqs['senha'] = dados_iqs.get('senha', '').astype(str).str.strip()
    dados_iqs['PERFIL'] = dados_iqs.get('PERFIL', 'IQ').astype(str).str.strip().str.upper()
    
    dados_tecnicos['login'] = dados_tecnicos.get('login', '').astype(str).str.strip().str.replace('.0', '', regex=False)
    dados_tecnicos['re_iq_responsavel'] = dados_tecnicos.get('re_iq_responsavel', '').astype(str).str.strip().str.replace('.0', '', regex=False)
    
    # Remove as colunas antigas da Base_Tecnicos, pois agora vivem nas abas de meses
    colunas_remover = ['status_certificacao', 'Acompanhamento', 'Contrato', 'Data_Monitoramento', 'Observacao']
    dados_tecnicos = dados_tecnicos.drop(columns=[c for c in colunas_remover if c in dados_tecnicos.columns], errors='ignore')

    dados_completos = dados_tecnicos.copy()
    
    # LEITURA INTELIGENTE DAS ABAS DE MESES
    todas_abas = [ws.title for ws in planilha.worksheets()]
    abas_meses = [aba for aba in todas_abas if aba not in ['Base_IQ', 'Base_Tecnicos']]
    
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
                elif 'CONTRATO' in c_up: colunas_novas[c] = f'CONTRATO_{mes_nome}'
                elif 'DATA' in c_up: colunas_novas[c] = f'DATA_MON_{mes_nome}'
                elif 'OBS' in c_up: colunas_novas[c] = f'OBS_{mes_nome}'
                else:
                    if mes_nome in c_up or c_up in mes_nome:
                        colunas_novas[c] = mes_nome
            
            df_mes = df_mes.rename(columns=colunas_novas)
            
            if 'LOGIN' in df_mes.columns:
                df_mes['LOGIN'] = df_mes['LOGIN'].astype(str).str.strip().str.replace('.0', '', regex=False)
                
                if mes_nome not in df_mes.columns: df_mes[mes_nome] = 'NÃO'
                if f'ACOMPANHAMENTO_{mes_nome}' not in df_mes.columns: df_mes[f'ACOMPANHAMENTO_{mes_nome}'] = 'NÃO'
                
                df_mes[mes_nome] = df_mes[mes_nome].fillna('NÃO').astype(str).str.strip().str.upper()
                df_mes[f'ACOMPANHAMENTO_{mes_nome}'] = df_mes[f'ACOMPANHAMENTO_{mes_nome}'].fillna('NÃO').astype(str).str.strip().str.upper()
                
                # CORREÇÃO DO CRUZAMENTO AQUI:
                dados_completos = pd.merge(dados_completos, df_mes, left_on='login', right_on='LOGIN', how='left')
                
                # Apaga o LOGIN em maiúsculo após juntar para não causar erro no próximo mês
                if 'LOGIN' in dados_completos.columns:
                    dados_completos = dados_completos.drop(columns=['LOGIN'])
                    
                meses_info.append({'nome_aba': aba, 'mes_nome': mes_nome})

    return dados_iqs, dados_completos, meses_info

def atualizar_planilha_mes(nome_aba, login_tecnico, coluna_busca, valor):
    ws = conectar_planilha().worksheet(nome_aba)
    cabecalhos = ws.row_values(1)
    col_idx = -1
    
    for i, c in enumerate(cabecalhos):
        if coluna_busca.upper() in str(c).upper():
            col_idx = i + 1
            break
            
    if col_idx == -1: return 
    
    registros = ws.get_all_records()
    for idx, row in enumerate(registros):
        login_key = next((k for k in row.keys() if 'LOGIN' in str(k).upper()), None)
        if login_key and str(row.get(login_key, '')).strip().replace('.0','') == str(login_tecnico):
            ws.update_cell(idx + 2, col_idx, valor)
            break
    st.cache_data.clear()

def colorir_sim_nao(val):
    texto = str(val).strip().upper()
    if texto == 'SIM': return 'background-color: #d4edda; color: #155724; font-weight: bold;'
    elif texto == 'NÃO' or texto == 'NAO': return 'background-color: #f8d7da; color: #721c24; font-weight: bold;'
    return ''

dados_iqs, dados_completos, meses_info = carregar_dados()

if meses_info:
    mes_vigente_info = meses_info[-1]
    mes_vigente = mes_vigente_info['mes_nome']
    aba_vigente = mes_vigente_info['nome_aba']
else:
    mes_vigente, aba_vigente = None, None

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
    
    if st.session_state.get('perfil') == 'GESTÃO':
        equipe_vigente = dados_completos
        equipe_historico = dados_completos
    else:
        equipe_vigente = dados_completos[dados_completos['re_iq_responsavel'] == re_logado]
        
        tecnicos_hist = []
        for index, row in dados_completos.iterrows():
            pertence = False
            for info in meses_info:
                col_re = f"RE_IQ_{info['mes_nome']}"
                if col_re in row and str(row[col_re]).strip() == str(re_logado):
                    pertence = True
            if pertence:
                tecnicos_hist.append(row)
        equipe_historico = pd.DataFrame(tecnicos_hist) if tecnicos_hist else pd.DataFrame(columns=dados_completos.columns)

    with st.sidebar:
        if os.path.exists("novo-logo-totale.png"): st.image(Image.open("novo-logo-totale.png"), use_container_width=True)
        st.write(f"**Usuário:** {st.session_state['nome_iq']}")
        st.write(f"**Perfil:** {st.session_state['perfil']}")
        st.divider()
        
        if st.button("📊 Dashboard Inicial", use_container_width=True): 
            st.session_state['pagina_atual'] = "Dashboard"
            st.rerun()
        if st.button("🏆 Histórico de Certificados", use_container_width=True): 
            st.session_state['pagina_atual'] = "Historico"
            st.rerun()
        if st.button("📋 Executar Matinal", use_container_width=True): 
            st.session_state['pagina_atual'] = "Matinal"
            st.rerun()
            
        st.divider()
        if st.button("Sair", use_container_width=True):
            st.session_state['logado'] = False
            st.rerun()

    if st.session_state['pagina_atual'] == "Dashboard":
        st.title(f"Painel Operacional - {st.session_state['nome_iq']}")
        
        col1, col2, col3 = st.columns(3)
        with col2:
            if st.session_state['perfil'] == 'GESTÃO':
                nova_meta = st.number_input("⏱️ Definir Meta de Horas (Monitoria):", value=st.session_state['horas_meta_geral'], step=1)
                st.session_state['horas_meta_geral'] = nova_meta
            else:
                st.metric("⏱️ Meta de Horas (Monitoria)", f"{st.session_state['horas_meta_geral']}h")
                
        with col1:
            if meses_info:
                lista_meses = [m['mes_nome'] for m in meses_info]
                mes_selecionado = st.selectbox("📅 Selecione o Mês (Para %):", lista_meses, index=len(lista_meses)-1)
                
                if not equipe_historico.empty and mes_selecionado in equipe_historico.columns:
                    total_mes = len(equipe_historico[equipe_historico[mes_selecionado].notna() & (equipe_historico[mes_selecionado] != '')])
                    sim_mes = len(equipe_historico[equipe_historico[mes_selecionado].astype(str).str.upper() == 'SIM'])
                    pct_mes = round((sim_mes / total_mes * 100), 1) if total_mes > 0 else 0
                    st.metric(f"🏆 % Certificados ({mes_selecionado})", f"{pct_mes}% SIM", f"Base: {total_mes} Téc", delta_color="off")
                else:
                    st.metric(f"🏆 % Certificados ({mes_selecionado})", "0% SIM", "Sem técnicos vinculados.")
            else:
                st.metric("🏆 Certificados", "N/A", "Nenhuma aba de mês encontrada.")
        
        with col3:
            if mes_vigente:
                pendentes_hoje = len(equipe_vigente[(equipe_vigente[mes_vigente] == 'NÃO') & (equipe_vigente[f'ACOMPANHAMENTO_{mes_vigente}'] != 'SIM')])
                st.metric(f"⚠️ Pendentes ({mes_vigente})", f"{pendentes_hoje} Técnicos", delta_color="inverse")
            else:
                st.metric("⚠️ Monitoramento", "N/A", "Sem base mensal")

        st.divider()
        st.subheader("📅 Sua Agenda de Matinais (Hoje)")
        if not st.session_state['agenda_matinal']:
            st.info("Sua agenda está vazia. Vá em 'Executar Matinal' para agendar.")
        else:
            for tec, data in list(st.session_state['agenda_matinal'].items()):
                st.write(f"📌 **{data}** - Técnico: **{tec}**")

        st.divider()
        st.subheader("⚠️ Acompanhamento Pendente")
        st.write(f"*Abaixo os técnicos da sua equipe que estão como 'NÃO' no certificado de **{mes_vigente or 'N/A'}** e precisam de tratativa:*")
        
        if mes_vigente:
            tecnicos_nao_cert = equipe_vigente[(equipe_vigente[mes_vigente] == 'NÃO') & (equipe_vigente[f'ACOMPANHAMENTO_{mes_vigente}'] != 'SIM')]
            
            if tecnicos_nao_cert.empty:
                st.success(f"Todos os técnicos pendentes de {mes_vigente} já possuem acompanhamento registrado.")
            else:
                for index, row in tecnicos_nao_cert.iterrows():
                    with st.expander(f"👤 {row['nome']} (Login: {row['login']})"):
                        col_f1, col_f2 = st.columns(2)
                        with col_f1:
                            novo_contrato = st.text_input("Contrato do Técnico:", value=row.get(f'CONTRATO_{mes_vigente}', ''), key=f"c_{row['login']}")
                            data_mon = st.date_input("Data do Monitoramento:", value=None, format="DD/MM/YYYY", key=f"d_{row['login']}")
                        with col_f2:
                            obs = st.text_area("Observações / Motivo:", value=row.get(f'OBS_{mes_vigente}', ''), key=f"o_{row['login']}")
                        
                        if st.button("Salvar Evolução", key=f"b_{row['login']}", type="primary"):
                            if data_mon: atualizar_planilha_mes(aba_vigente, row['login'], 'DATA', data_mon.strftime("%d/%m/%Y"))
                            atualizar_planilha_mes(aba_vigente, row['login'], 'CONTRATO', novo_contrato)
                            atualizar_planilha_mes(aba_vigente, row['login'], 'OBS', obs)
                            atualizar_planilha_mes(aba_vigente, row['login'], 'ACOMPANHAMENTO', 'SIM')
                            st.success(f"Salvo na aba {aba_vigente}! Status de acompanhamento alterado para SIM.")
                            st.rerun()
        else:
            st.info("Crie as abas de certificados mensais no Sheets para visualizar pendências.")

    elif st.session_state['pagina_atual'] == "Historico":
        st.title(f"🏆 Histórico de Certificados - {st.session_state['nome_iq']}")
        
        if not meses_info:
            st.warning("Nenhuma aba de certificação encontrada no Google Sheets.")
        elif equipe_historico.empty:
            st.info("Você não possui técnicos vinculados ao seu RE no histórico de certificações.")
        else:
            colunas_exibir = ['login', 'nome']
            
            for info in meses_info:
                mes = info['mes_nome']
                if mes in equipe_historico.columns: colunas_exibir.append(mes)
                if f'RE_IQ_{mes}' in equipe_historico.columns: colunas_exibir.append(f'RE_IQ_{mes}')
            
            df_exibir = equipe_historico[[col for col in colunas_exibir if col in equipe_historico.columns]]
            st.dataframe(df_exibir.style.map(colorir_sim_nao), hide_index=True, use_container_width=True)

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
                    st.session_state['agenda_matinal'][tec_agendar] = data_agendada.strftime("%d/%m/%Y")
                    st.success(f"Agendado!")
            
            st.write("---")
            for tec, data in list(st.session_state['agenda_matinal'].items()):
                c1, c2 = st.columns([4, 1])
                c1.write(f"📌 {data} - **{tec}**")
                if c2.button("🗑️ Remover", key=f"rm_{tec}"):
                    del st.session_state['agenda_matinal'][tec]
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
                            if aba_vigente:
                                atualizar_planilha_mes(aba_vigente, tec_login, 'ACOMPANHAMENTO', 'SIM')
                            del st.session_state['agenda_matinal'][tec_atual]
                            st.session_state['email_pronto'] = url_email
                            st.rerun()
