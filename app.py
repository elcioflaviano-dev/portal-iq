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
if 'horas_meta_geral' not in st.session_state: st.session_state['horas_meta_geral'] = 40 # Variável temporária de horas
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
            registros = planilha.worksheet(nome_aba).get_all_records()
            return pd.DataFrame(registros) if registros else pd.DataFrame()
        except:
            return pd.DataFrame()
            
    dados_iqs = ler_aba("Base_IQ")
    dados_tecnicos = ler_aba("Base_Tecnicos")
    dados_certificados = ler_aba("Certificados")
    
    if dados_iqs.empty or dados_tecnicos.empty:
        st.error("Planilha do Google está vazia ou sem cabeçalhos.")
        st.stop()
    
    # Padronização
    dados_iqs['re_iq'] = dados_iqs['re_iq'].astype(str).str.strip().str.replace('.0', '', regex=False)
    dados_iqs['senha'] = dados_iqs.get('senha', '').astype(str).str.strip()
    dados_iqs['PERFIL'] = dados_iqs.get('PERFIL', 'IQ').astype(str).str.strip().str.upper()
    
    dados_tecnicos['login'] = dados_tecnicos.get('login', '').astype(str).str.strip().str.replace('.0', '', regex=False)
    dados_tecnicos['re_iq_responsavel'] = dados_tecnicos.get('re_iq_responsavel', '').astype(str).str.strip().str.replace('.0', '', regex=False)
    dados_tecnicos['status_certificacao'] = dados_tecnicos.get('status_certificacao', 'NÃO').astype(str).str.strip().str.upper()

    if not dados_certificados.empty and 'LOGIN' in dados_certificados.columns:
        dados_certificados['LOGIN'] = dados_certificados['LOGIN'].astype(str).str.strip().str.replace('.0', '', regex=False)
        dados_completos = pd.merge(dados_tecnicos, dados_certificados, left_on='login', right_on='LOGIN', how='left')
    else:
        dados_completos = dados_tecnicos
        
    return dados_iqs, dados_completos

def atualizar_planilha_tecnicos(login_tecnico, coluna, valor):
    ws = conectar_planilha().worksheet("Base_Tecnicos")
    registros = ws.get_all_records()
    for idx, row in enumerate(registros):
        if str(row.get('login', '')).strip().replace('.0','') == str(login_tecnico):
            if coluna in row:
                ws.update_cell(idx + 2, list(row.keys()).index(coluna) + 1, valor)
            break
    st.cache_data.clear()

def colorir_sim_nao(val):
    if str(val).strip().upper() == 'SIM': return 'background-color: #d4edda; color: #155724; font-weight: bold;'
    elif str(val).strip().upper() == 'NÃO': return 'background-color: #f8d7da; color: #721c24; font-weight: bold;'
    return ''

dados_iqs, dados_completos = carregar_dados()

# --- 3. Telas ---
if not st.session_state['logado']:
    col_logo, _ = st.columns([1, 2])
    with col_logo:
        if os.path.exists("novo-logo-totale.png"): st.image(Image.open("novo-logo-totale.png"), use_container_width=True)
            
    st.title("Acesso Operacional - Totale")
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

else:
    # Lógica de Equipe Vigente vs Histórico
    # O dashboard mostra tudo, mas o acompanhamento foca no mês vigente.
    if st.session_state.get('perfil') == 'GESTÃO':
        equipe_iq = dados_completos
    else:
        equipe_iq = dados_completos[dados_completos['re_iq_responsavel'] == st.session_state['re_usuario']]

    with st.sidebar:
        if os.path.exists("novo-logo-totale.png"): st.image(Image.open("novo-logo-totale.png"), use_container_width=True)
        st.write(f"**Usuário:** {st.session_state['nome_iq']}")
        st.write(f"**Perfil:** {st.session_state['perfil']}")
        st.divider()
        if st.button("📊 Dashboard Inicial", use_container_width=True): 
            st.session_state['pagina_atual'] = "Dashboard"
            st.session_state['email_pronto'] = None
            st.rerun()
        if st.button("📋 Executar Matinal", use_container_width=True): 
            st.session_state['pagina_atual'] = "Matinal"
            st.session_state['email_pronto'] = None
            st.rerun()
        st.divider()
        if st.button("Sair", use_container_width=True):
            st.session_state['logado'] = False
            st.rerun()

    # --- DASHBOARD ---
    if st.session_state['pagina_atual'] == "Dashboard":
        st.title(f"Painel Operacional - {st.session_state['nome_iq']}")
        
        col1, col2, col3 = st.columns(3)
        
        # Lógica de Horas: Gestor edita, IQ visualiza
        with col2:
            if st.session_state['perfil'] == 'GESTÃO':
                nova_meta = st.number_input("⏱️ Definir Meta de Horas (Monitoria):", value=st.session_state['horas_meta_geral'], step=1)
                st.session_state['horas_meta_geral'] = nova_meta
            else:
                st.metric("⏱️ Meta de Horas (Monitoria)", f"{st.session_state['horas_meta_geral']}h")
                
        # Percentual de Certificação por Mês (Lendo a aba Certificados)
        meses_certificacao = [col for col in dados_completos.columns if 'CERTIFICADO' in str(col).upper() and col.upper() != 'STATUS_CERTIFICACAO']
        
        with col1:
            if meses_certificacao:
                mes_selecionado = st.selectbox("📅 Selecione o Mês:", meses_certificacao)
                # Filtra os dados apenas para o mês selecionado e IQ (se aplicável via RE na aba certificados futuramente)
                total_mes = len(equipe_iq[equipe_iq[mes_selecionado].notna() & (equipe_iq[mes_selecionado] != '')])
                sim_mes = len(equipe_iq[equipe_iq[mes_selecionado].astype(str).str.upper() == 'SIM'])
                pct_mes = round((sim_mes / total_mes * 100), 1) if total_mes > 0 else 0
                st.metric(f"🏆 Certificados ({mes_selecionado.replace('CERTIFICADO ','')})", f"{pct_mes}% SIM", f"Base: {total_mes} Téc", delta_color="off")
            else:
                st.metric("🏆 Certificados", "N/A", "Nenhuma coluna de mês encontrada.")
        
        with col3:
            pendentes_hoje = len(equipe_iq[equipe_iq['status_certificacao'] == 'NÃO'])
            st.metric("⚠️ Monitoramento Pendente (Atual)", f"{pendentes_hoje} Técnicos", delta_color="inverse")

        st.divider()

        # Agenda na Tela Inicial
        st.subheader("📅 Sua Agenda de Matinais")
        if not st.session_state['agenda_matinal']:
            st.info("Sua agenda está vazia. Vá em 'Executar Matinal' para agendar.")
        else:
            for tec, data in list(st.session_state['agenda_matinal'].items()):
                st.write(f"📌 **{data}** - Técnico: **{tec}**")

        st.divider()

        # Botão Expansível para Certificados
        with st.expander("👁️ Ver Lista de Técnicos Certificados (Histórico)"):
            if meses_certificacao:
                df_exibir = equipe_iq[['login', 'nome'] + meses_certificacao]
                st.dataframe(df_exibir.style.map(colorir_sim_nao), hide_index=True, use_container_width=True)
            else:
                st.write("Sem histórico disponível.")

        # Monitoramento Automático (Técnicos com Status Atual = NÃO)
        st.subheader("⚠️ Acompanhamento / Monitoramento Automático")
        st.write("*Abaixo estão os técnicos não certificados no mês vigente que necessitam da sua tratativa:*")
        
        tecnicos_nao_cert = equipe_iq[equipe_iq['status_certificacao'] == 'NÃO']
        
        if tecnicos_nao_cert.empty:
            st.success("Todos os técnicos estão certificados ou sem pendências.")
        else:
            for index, row in tecnicos_nao_cert.iterrows():
                with st.expander(f"👤 {row['nome']} (Login: {row['login']})"):
                    col_f1, col_f2 = st.columns(2)
                    with col_f1:
                        novo_contrato = st.text_input("Contrato do Técnico:", value=row.get('Contrato', ''), key=f"c_{row['login']}")
                        data_mon = st.date_input("Data do Monitoramento:", value=None, format="DD/MM/YYYY", key=f"d_{row['login']}")
                    with col_f2:
                        obs = st.text_area("Observações / Motivo:", value=row.get('Observacao', ''), key=f"o_{row['login']}")
                    
                    if st.button("Salvar Evolução", key=f"b_{row['login']}", type="primary"):
                        if data_mon: atualizar_planilha_tecnicos(row['login'], 'Data_Monitoramento', data_mon.strftime("%d/%m/%Y"))
                        atualizar_planilha_tecnicos(row['login'], 'Contrato', novo_contrato)
                        atualizar_planilha_tecnicos(row['login'], 'Observacao', obs)
                        st.success("Salvo no Google Sheets!")

    # --- MATINAL (Checklist Completo) ---
    elif st.session_state['pagina_atual'] == "Matinal":
        st.title("📋 Agendamento e Execução da Matinal")
        
        tab_agendar, tab_executar = st.tabs(["1. Agendar Téc", "2. Executar Vistoria (Checklist)"])
        
        with tab_agendar:
            col_a1, col_a2 = st.columns(2)
            with col_a1:
                tec_agendar = st.selectbox("Selecione o Técnico:", ["Selecione..."] + equipe_iq['nome'].tolist())
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
            # Controle de Tela Pós-Email
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
                    
                    # AS 84 COLUNAS DIVIDIDAS EM BLOCOS CATEGORIZADOS
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
                            del st.session_state['agenda_matinal'][tec_atual] # Remove da agenda
                            st.session_state['email_pronto'] = url_email # Salva o link e apaga a tela
                            st.rerun()
