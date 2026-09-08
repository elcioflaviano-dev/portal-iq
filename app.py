import streamlit as st
import pandas as pd
from PIL import Image
import os
import urllib.parse

# --- 1. Configuração Inicial ---
st.set_page_config(page_title="Portal IQ - Totale", layout="wide", initial_sidebar_state="expanded")

# Inicialização de Variáveis de Sessão para manter os dados salvos enquanto o app roda
if 'logado' not in st.session_state: st.session_state['logado'] = False
if 'pagina_atual' not in st.session_state: st.session_state['pagina_atual'] = "Dashboard"
if 'horas_monitoria' not in st.session_state: st.session_state['horas_monitoria'] = 40
if 'agenda_matinal' not in st.session_state: st.session_state['agenda_matinal'] = []
if 'matinal_ativa' not in st.session_state: st.session_state['matinal_ativa'] = None

# --- 2. Leitura de Dados ---
@st.cache_data
def carregar_dados():
    try:
        dados_iqs = pd.read_excel('PORTAL IQ.xlsx', sheet_name='Base_IQ')
        dados_tecnicos = pd.read_excel('PORTAL IQ.xlsx', sheet_name='Base_Tecnicos')
        dados_certificados = pd.read_excel('PORTAL IQ.xlsx', sheet_name='Certificados')
        
        # Padronização e Limpeza
        dados_iqs['re_iq'] = dados_iqs['re_iq'].astype(str).str.strip().str.replace('.0', '', regex=False)
        dados_iqs['senha'] = dados_iqs['senha'].astype(str).str.strip()
        dados_iqs['PERFIL'] = dados_iqs.get('PERFIL', 'IQ').astype(str).str.strip().str.upper()
        
        dados_tecnicos['login'] = dados_tecnicos['login'].astype(str).str.strip().str.replace('.0', '', regex=False)
        dados_tecnicos['re_iq_responsavel'] = dados_tecnicos['re_iq_responsavel'].astype(str).str.strip().str.replace('.0', '', regex=False)
        
        # Correção do Bug: Padroniza para SIM e NÃO
        dados_tecnicos['status_certificacao'] = dados_tecnicos['status_certificacao'].astype(str).str.strip().str.upper()
        dados_tecnicos['Acompanhamento'] = dados_tecnicos.get('Acompanhamento', 'NÃO').astype(str).str.strip().str.upper()

        # Mescla histórico de meses se existir a coluna LOGIN na aba Certificados
        if 'LOGIN' in dados_certificados.columns:
            dados_certificados['LOGIN'] = dados_certificados['LOGIN'].astype(str).str.strip().str.replace('.0', '', regex=False)
            dados_completos = pd.merge(dados_tecnicos, dados_certificados, left_on='login', right_on='LOGIN', how='left')
        else:
            dados_completos = dados_tecnicos
            
        return dados_iqs, dados_completos
    except Exception as e:
        st.error(f"Erro ao ler a planilha. Verifique os nomes das abas e colunas. Detalhe: {e}")
        st.stop()

dados_iqs, dados_completos = carregar_dados()

def mudar_pagina(nome_pagina):
    st.session_state['pagina_atual'] = nome_pagina

# --- 3. Tela de Login ---
if not st.session_state['logado']:
    col_logo, col_vazia = st.columns([1, 2])
    with col_logo:
        if os.path.exists("novo-logo-totale.png"):
            st.image(Image.open("novo-logo-totale.png"), width=250)
            
    st.title("Acesso - Portal Operacional Totale")
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

# --- 4. Sistema Principal ---
else:
    # Filtra a equipe (Gestão vê todos, IQ vê apenas os seus)
    if st.session_state.get('perfil') == 'GESTÃO':
        equipe_iq = dados_completos
    else:
        equipe_iq = dados_completos[dados_completos['re_iq_responsavel'] == st.session_state['re_usuario']]

    # SIDEBAR (Menu)
    with st.sidebar:
        if os.path.exists("novo-logo-totale.png"):
            st.image(Image.open("novo-logo-totale.png"), use_column_width=True)
        st.write(f"**Usuário:** {st.session_state['nome_iq']}")
        st.write(f"**Perfil:** {st.session_state['perfil']}")
        st.divider()
        
        if st.button("📊 Dashboard Inicial", use_container_width=True): mudar_pagina("Dashboard")
        if st.button("📅 Agenda e Matinal", use_container_width=True): mudar_pagina("Matinal")
            
        st.divider()
        if st.button("Sair", use_container_width=True):
            st.session_state['logado'] = False
            st.rerun()

    # --- PÁGINA 1: DASHBOARD ---
    if st.session_state['pagina_atual'] == "Dashboard":
        st.title(f"Portal IQ - {st.session_state['nome_iq']}")
        
        # Cálculos de Porcentagem
        total_tecnicos = len(equipe_iq)
        certificados_sim = len(equipe_iq[equipe_iq['status_certificacao'] == 'SIM'])
        certificados_nao = len(equipe_iq[equipe_iq['status_certificacao'] == 'NÃO'])
        
        pct_sim = round((certificados_sim / total_tecnicos * 100), 1) if total_tecnicos > 0 else 0
        pct_nao = round((certificados_nao / total_tecnicos * 100), 1) if total_tecnicos > 0 else 0
        
        # Faltam Matinal: Técnicos que ainda não estão na agenda de hoje e não são certificados
        tecnicos_nao_cert = equipe_iq[(equipe_iq['status_certificacao'] == 'NÃO') & (equipe_iq['Acompanhamento'] == 'NÃO')]
        tecnicos_pendentes_matinal = [t for t in tecnicos_nao_cert['nome'].tolist() if t not in st.session_state['agenda_matinal']]
        
        # Cards Superiores
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(label="🏆 Certificados", value=f"{pct_sim}% SIM", delta=f"{pct_nao}% NÃO (Total: {total_tecnicos})", delta_color="off")
        with col2:
            nova_hora = st.number_input("⏱️ Horas de Monitoria (Manual)", value=st.session_state['horas_monitoria'], step=1)
            st.session_state['horas_monitoria'] = nova_hora
        with col3:
            st.metric(label="⚠️ Faltam Matinal", value=f"{len(tecnicos_pendentes_matinal)} Técnicos", delta_color="inverse")

        st.divider()
        
        # Tabela de Certificados (SIM)
        st.subheader("✅ Técnicos Certificados (Histórico Mensal)")
        df_certificados = equipe_iq[equipe_iq['status_certificacao'] == 'SIM']
        if df_certificados.empty:
            st.info("Nenhum técnico certificado.")
        else:
            colunas_mostrar = [c for c in df_certificados.columns if c in ['login', 'nome', 'regiao'] or 'CERTIFICADO ' in c.upper()]
            st.dataframe(df_certificados[colunas_mostrar], hide_index=True, use_container_width=True)
        
        # Acordeão de Acompanhamento (Clicável)
        st.subheader("⚠️ Técnicos em Monitoramento (Acompanhamento)")
        st.markdown("*Clique no nome do técnico abaixo para registrar detalhes do acompanhamento:*")
        
        if tecnicos_nao_cert.empty:
            st.success("Nenhum técnico pendente de acompanhamento no momento.")
        else:
            for index, row in tecnicos_nao_cert.iterrows():
                # Cria uma barra expansível (clicável) para cada técnico
                with st.expander(f"👤 {row['login']} - {row['nome']} | Região: {row['regiao']}"):
                    col_form1, col_form2 = st.columns(2)
                    with col_form1:
                        contrato = st.text_input(f"Contrato (Téc: {row['nome']})", key=f"cont_{row['login']}")
                        data_mon = st.date_input(f"Data do Monitoramento", key=f"data_{row['login']}")
                    with col_form2:
                        obs = st.text_area("Observações", key=f"obs_{row['login']}")
                    
                    if st.button("Salvar Acompanhamento", key=f"btn_{row['login']}", type="primary"):
                        st.success("Dados salvos com sucesso! (Na versão final, isso atualizará o Excel).")

    # --- PÁGINA 2: AGENDA E MATINAL ---
    elif st.session_state['pagina_atual'] == "Matinal":
        st.title("📅 Matinal e Vistoria")
        
        tab_agenda, tab_executar = st.tabs(["1. Agendar Matinal", "2. Realizar Matinal"])
        
        # Aba 1: Agendamento
        with tab_agenda:
            st.subheader("Agendar novo técnico para Matinal")
            lista_elegiveis = equipe_iq[equipe_iq['status_certificacao'] == 'NÃO']['nome'].tolist()
            
            col_a1, col_a2 = st.columns(2)
            with col_a1:
                tec_agendar = st.selectbox("Selecione o Técnico:", ["Selecione..."] + lista_elegiveis)
            with col_a2:
                if st.button("Adicionar à Agenda de Hoje"):
                    if tec_agendar != "Selecione..." and tec_agendar not in st.session_state['agenda_matinal']:
                        st.session_state['agenda_matinal'].append(tec_agendar)
                        st.success(f"{tec_agendar} adicionado à agenda!")
                        st.rerun()
            
            st.divider()
            st.write("**Agenda de Matinais de Hoje:**")
            if len(st.session_state['agenda_matinal']) == 0:
                st.info("Nenhum técnico agendado para hoje.")
            else:
                for tec in st.session_state['agenda_matinal']:
                    col_nome, col_acao = st.columns([3, 1])
                    col_nome.write(f"📌 **{tec}**")
                    if col_acao.button("Iniciar Matinal", key=f"iniciar_{tec}", type="primary"):
                        st.session_state['matinal_ativa'] = tec
                        st.rerun()

        # Aba 2: Execução da Matinal
        with tab_executar:
            tec_atual = st.session_state['matinal_ativa']
            
            if tec_atual is None:
                st.warning("Nenhuma matinal em andamento. Vá na aba 'Agendar Matinal' e clique em Iniciar.")
            else:
                st.subheader(f"📋 Executando Matinal: {tec_atual}")
                st.info("⚠️ Marque os itens que estão **FALTANDO** ou **IRREGULARES**.")
                
                # Checklists baseados no arquivo Matinal_2026.xlsx
                st.markdown("**Ferramental Básico e Específico**")
                col_c1, col_c2, col_c3 = st.columns(3)
                faltas = []
                with col_c1:
                    if st.checkbox("Alicates (Crimpador, Bico, Corte)"): faltas.append("Alicates Básicos")
                    if st.checkbox("Chaves Fenda/Phillips"): faltas.append("Chaves Fenda/Phillips")
                with col_c2:
                    if st.checkbox("Fita Guia / Furadeira"): faltas.append("Fita Guia/Furadeira")
                    if st.checkbox("Clivador / Gabaritos"): faltas.append("Clivador/Gabaritos")
                with col_c3:
                    if st.checkbox("Power Meter / Caneta Óptica"): faltas.append("Power Meter/Caneta")
                    if st.checkbox("DBAM / Trilithic"): faltas.append("DBAM/Trilithic")
                
                st.markdown("**EPIs, Asseio e Veículo**")
                col_e1, col_e2, col_e3 = st.columns(3)
                with col_e1:
                    if st.checkbox("Capacete / Cinto / Luvas"): faltas.append("EPIs (Capacete/Cinto/Luvas)")
                    if st.checkbox("Óculos de Proteção"): faltas.append("Óculos de Proteção")
                with col_e2:
                    if st.checkbox("Escada / Cones / Fita Zebrada"): faltas.append("Sinalização/Escada")
                    if st.checkbox("Uniforme / Crachá / Higiene"): faltas.append("Asseio (Uniforme/Crachá)")
                with col_e3:
                    if st.checkbox("Veículo (Sujo / Desorganizado)"): faltas.append("Veículo Irregular")
                    if st.checkbox("PDA (Bateria Baixa / Deslogado)"): faltas.append("PDA Irregular")
                
                st.divider()
                st.markdown("### Conclusão")
                foto_upload = st.file_uploader("📸 Enviar Foto da Matinal", type=['png', 'jpg', 'jpeg'])
                obs_final = st.text_area("Observações Finais:")
                
                # Preparação do E-mail
                faltas_str = ", ".join(faltas) if len(faltas) > 0 else "Nenhuma irregularidade apontada."
                corpo_email = f"Matinal Realizada - Técnico: {tec_atual}\n\nIQ Responsável: {st.session_state['nome_iq']}\n\nItens Faltantes/Irregulares:\n{faltas_str}\n\nObservações: {obs_final}"
                
                # Botão que cria o link para o aplicativo de email do celular
                url_email = f"mailto:?subject=Relatório de Matinal - {tec_atual}&body={urllib.parse.quote(corpo_email)}"
                
                if st.button("Finalizar Matinal e Dar Baixa", type="primary"):
                    if foto_upload is None:
                        st.warning("A foto é obrigatória para finalizar.")
                    else:
                        st.session_state['agenda_matinal'].remove(tec_atual)
                        st.session_state['matinal_ativa'] = None
                        st.success(f"Matinal finalizada! A baixa foi dada para {tec_atual}.")
                        st.markdown(f'📩 **[Clique aqui para enviar o E-mail com o Resumo]({url_email})**')
                        
                        if st.button("Voltar para a Agenda"):
                            st.rerun()
