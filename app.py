import streamlit as st
import pandas as pd
from PIL import Image
import os

# --- 1. Configuração Inicial da Página ---
st.set_page_config(page_title="Portal IQ - Totale", layout="wide", initial_sidebar_state="expanded")

# --- 2. Leitura de Dados ---
@st.cache_data
def carregar_dados():
    try:
        dados_iqs = pd.read_excel('PORTAL IQ.xlsx', sheet_name='Base_IQ')
        dados_tecnicos = pd.read_excel('PORTAL IQ.xlsx', sheet_name='Base_Tecnicos')
        dados_certificados = pd.read_excel('PORTAL IQ.xlsx', sheet_name='Certificados')
        
        dados_iqs['re_iq'] = dados_iqs['re_iq'].astype(str).str.strip().str.replace('.0', '', regex=False)
        dados_iqs['senha'] = dados_iqs['senha'].astype(str).str.strip()
        
        if 'PERFIL' in dados_iqs.columns:
            dados_iqs['PERFIL'] = dados_iqs['PERFIL'].astype(str).str.strip().str.upper()
        else:
            dados_iqs['PERFIL'] = 'IQ'
        
        dados_tecnicos['login'] = dados_tecnicos['login'].astype(str).str.strip().str.replace('.0', '', regex=False)
        dados_tecnicos['re_iq_responsavel'] = dados_tecnicos['re_iq_responsavel'].astype(str).str.strip().str.replace('.0', '', regex=False)
        dados_tecnicos['status_certificacao'] = dados_tecnicos['status_certificacao'].astype(str).str.strip().str.upper()
        
        if 'Acompanhamento' not in dados_tecnicos.columns:
            dados_tecnicos['Acompanhamento'] = 'NÃO'
        else:
            dados_tecnicos['Acompanhamento'] = dados_tecnicos['Acompanhamento'].astype(str).str.strip().str.upper()

        if 'LOGIN' in dados_certificados.columns:
            dados_certificados['LOGIN'] = dados_certificados['LOGIN'].astype(str).str.strip().str.replace('.0', '', regex=False)
            dados_completos = pd.merge(dados_tecnicos, dados_certificados, left_on='login', right_on='LOGIN', how='left')
            dados_completos = dados_completos.drop(columns=['LOGIN'])
        else:
            dados_completos = dados_tecnicos
            
        return dados_iqs, dados_completos
    except Exception as e:
        st.error(f"Erro ao ler a planilha. Detalhe: {e}")
        st.stop()

dados_iqs, dados_completos = carregar_dados()

# --- 3. Controle de Sessão e Navegação ---
if 'logado' not in st.session_state:
    st.session_state['logado'] = False
if 'pagina_atual' not in st.session_state:
    st.session_state['pagina_atual'] = "Dashboard"

# Função para mudar de página pelos botões
def mudar_pagina(nome_pagina):
    st.session_state['pagina_atual'] = nome_pagina

# --- 4. Tela de Login ---
if not st.session_state['logado']:
    col_logo, col_vazia = st.columns([1, 2])
    with col_logo:
        if os.path.exists("novo-logo-totale.png"):
            st.image(Image.open("novo-logo-totale.png"), width=250)
            
    st.title("Acesso - Portal Operacional")
    re_input = st.text_input("RE (Login)")
    senha_input = st.text_input("Senha", type="password")
    
    if st.button("Entrar", type="primary"):
        re_limpo = re_input.strip()
        senha_limpa = senha_input.strip()
        iq_valido = dados_iqs[(dados_iqs['re_iq'] == re_limpo) & (dados_iqs['senha'] == senha_limpa)]
        
        if not iq_valido.empty:
            st.session_state['logado'] = True
            st.session_state['re_usuario'] = re_limpo
            st.session_state['nome_iq'] = iq_valido.iloc[0]['nome_iq']
            st.session_state['perfil'] = iq_valido.iloc[0]['PERFIL']
            st.rerun()
        else:
            st.error("RE ou Senha incorretos.")

# --- 5. Sistema Principal (Logado) ---
else:
    # FILTRO DA EQUIPE DO IQ LOGADO
    if st.session_state.get('perfil') == 'GESTÃO':
        equipe_iq = dados_completos
    else:
        equipe_iq = dados_completos[dados_completos['re_iq_responsavel'] == st.session_state['re_usuario']]

    # SIDEBAR - MENU DE NAVEGAÇÃO
    with st.sidebar:
        if os.path.exists("novo-logo-totale.png"):
            st.image(Image.open("novo-logo-totale.png"), use_column_width=True)
        st.write(f"**Usuário:** {st.session_state['nome_iq']}")
        st.write(f"**Perfil:** {st.session_state['perfil']}")
        st.divider()
        
        if st.button("📊 Dashboard Inicial", use_container_width=True):
            mudar_pagina("Dashboard")
        if st.button("📋 Executar Matinal", use_container_width=True):
            mudar_pagina("Matinal")
            
        st.divider()
        if st.button("Sair", use_container_width=True):
            st.session_state['logado'] = False
            st.session_state['pagina_atual'] = "Dashboard"
            st.rerun()

    # --- PÁGINA 1: DASHBOARD INICIAL ---
    if st.session_state['pagina_atual'] == "Dashboard":
        st.title(f"Portal IQ - {st.session_state['nome_iq']}")
        
        # Lógica para os Indicadores
        total_certificados = len(equipe_iq[equipe_iq['status_certificacao'] == 'CERTIFICADO'])
        porcentagem_cert = round((total_certificados / len(equipe_iq) * 100) if len(equipe_iq) > 0 else 0, 1)
        
        tecnicos_faltam_matinal = len(equipe_iq[(equipe_iq['status_certificacao'] != 'CERTIFICADO') & (equipe_iq['Acompanhamento'] == 'NÃO')])
        horas_monitoria_manuais = "40h" # Substitua pelo valor real ou campo dinâmico
        
        # Cards Superiores
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(label="🏆 Técnicos Certificados", value=f"{porcentagem_cert}%", delta=f"{total_certificados} Técnicos")
        with col2:
            st.metric(label="⏱️ Horas de Monitoria", value=horas_monitoria_manuais)
        with col3:
            st.metric(label="⚠️ Faltam Matinal", value=f"{tecnicos_faltam_matinal} Técnicos", delta_color="inverse")

        st.divider()
        
        # Organização das colunas da tabela
        colunas_exibicao = ['login', 'nome', 'status_certificacao', 'Acompanhamento', 'regiao']
        colunas_meses = [col for col in equipe_iq.columns if 'CERTIFICADO ' in str(col).upper()]
        colunas_exibicao.extend(colunas_meses)
        colunas_exibicao = [col for col in colunas_exibicao if col in equipe_iq.columns]
        equipe_exibicao = equipe_iq[colunas_exibicao]
        
        st.subheader("✅ Técnicos Certificados (Histórico Mensal)")
        certificados_df = equipe_exibicao[equipe_exibicao['status_certificacao'] == 'CERTIFICADO']
        if certificados_df.empty:
            st.info("Nenhum técnico certificado cadastrado.")
        else:
            st.dataframe(certificados_df, hide_index=True, use_container_width=True)
        
        st.subheader("⚠️ Técnicos em Monitoramento (Falta Matinal)")
        st.markdown("*Abaixo os técnicos que não estão certificados e possuem Acompanhamento = NÃO.*")
        # Filtro Específico: Não certificados e que Não possuem acompanhamento agendado/sim
        monitoramento_df = equipe_exibicao[(equipe_exibicao['status_certificacao'] != 'CERTIFICADO') & (equipe_exibicao['Acompanhamento'] == 'NÃO')]
        
        if monitoramento_df.empty:
            st.success("Todos os técnicos não certificados já possuem acompanhamento.")
        else:
            st.dataframe(monitoramento_df, hide_index=True, use_container_width=True)
            col_btn, _ = st.columns([1, 4])
            with col_btn:
                if st.button("Ir para Matinal", type="primary", use_container_width=True):
                    mudar_pagina("Matinal")
                    st.rerun()

    # --- PÁGINA 2: MATINAL E VISTORIA COMPLETA ---
    elif st.session_state['pagina_atual'] == "Matinal":
        st.title("📋 Formulário de Matinal e Vistoria")
        
        lista_nao_certificados = equipe_iq[equipe_iq['status_certificacao'] != 'CERTIFICADO']['nome'].tolist()
        lista_certificados = equipe_iq[equipe_iq['status_certificacao'] == 'CERTIFICADO']['nome'].tolist()
        
        st.markdown("### 1. Iniciar Vistoria")
        col_t1, col_t2 = st.columns(2)
        with col_t1:
            tec_alvo = st.selectbox("Selecione o Técnico a ser monitorado:", ["Selecione..."] + lista_nao_certificados)
        with col_t2:
            tec_guia = st.selectbox("Técnico Certificado (Guia/Vistoriador):", ["Selecione..."] + lista_certificados)

        if tec_alvo != "Selecione..." and tec_guia != "Selecione...":
            st.divider()
            st.markdown(f"### 2. Formulário de Vistoria - Técnico: **{tec_alvo}**")
            st.info("⚠️ Marque os itens que estão **FALTANDO** ou **IRREGULARES**.")
            
            # Estrutura baseada no arquivo Matinal_2026.xlsx
            tab1, tab2, tab3, tab4 = st.tabs(["🛠️ Ferramental Básico", "📡 Ferramental GPON/LVM", "👷 EPIs e EPCs", "🚗 Asseio e Veículo"])
            
            with tab1:
                st.write("**Falta ou Irregularidade no Ferramental Básico:**")
                col_f1, col_f2, col_f3 = st.columns(3)
                with col_f1:
                    st.checkbox("Alicates (Crimpador, Bico, Corte)")
                    st.checkbox("Chaves Fenda/Phillips")
                    st.checkbox("Estilete / Striper")
                with col_f2:
                    st.checkbox("Fita Guia / Furadeira")
                    st.checkbox("Martelo / Extensão")
                    st.checkbox("Brocas de Wídea")
                with col_f3:
                    st.checkbox("Mala / Bornal")
                    st.checkbox("Lanterna")
                    st.checkbox("Telefone Gôndola")
                    
            with tab2:
                st.write("**Falta ou Irregularidade no Kit Específico:**")
                col_g1, col_g2 = st.columns(2)
                with col_g1:
                    st.checkbox("Clivador / Gabaritos")
                    st.checkbox("Alicate Decapador Fibra/Drop")
                    st.checkbox("Power Meter / Caneta Óptica")
                with col_g2:
                    st.checkbox("Álcool Isopropílico / Dispenser")
                    st.checkbox("Kit Lenços de Limpeza")
                    st.checkbox("DBAM / Trilithic")

            with tab3:
                st.write("**Falta ou Irregularidade em Segurança:**")
                col_e1, col_e2 = st.columns(2)
                with col_e1:
                    st.checkbox("Capacete / Jugular")
                    st.checkbox("Cinto de Segurança / Talabarte")
                    st.checkbox("Luvas (Pigmentada / Vaqueta)")
                    st.checkbox("Óculos de Proteção")
                with col_e2:
                    st.checkbox("Escadas (6m ou 4 degraus)")
                    st.checkbox("Cones (3) / Bandeirola")
                    st.checkbox("Manta / Fita Zebrada")

            with tab4:
                st.write("**Falta ou Irregularidade Pessoal e Veicular:**")
                col_v1, col_v2 = st.columns(2)
                with col_v1:
                    st.checkbox("Uniforme Incompleto / Sujo")
                    st.checkbox("Crachá Indisponível")
                    st.checkbox("Barba / Higiene / Adornos")
                with col_v2:
                    st.checkbox("Veículo (Sujo / Desorganizado)")
                    st.checkbox("Avarias no Veículo Interno/Externo")
                    st.checkbox("PDA (Bateria < 50% / Logado)")
            
            st.divider()
            st.markdown("### 3. Conclusão e Registro")
            foto_upload = st.file_uploader("📸 Enviar Foto da Matinal (Obrigatório)", type=['png', 'jpg', 'jpeg'])
            observacoes = st.text_area("Observações ou Falhas Adicionais:")
            
            if st.button("Confirmar Matinal", type="primary", use_container_width=True):
                if foto_upload is None:
                    st.warning("⚠️ O envio da foto é obrigatório para concluir a matinal.")
                else:
                    st.success(f"✅ Matinal de {tec_alvo} concluída com sucesso! Os apontamentos foram registrados.")
                    # Aqui entra a lógica futura para atualizar o Excel e baixar a falta matinal
