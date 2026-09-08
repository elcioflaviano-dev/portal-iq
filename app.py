import streamlit as st
import pandas as pd
from PIL import Image
import os
import urllib.parse
from datetime import datetime

# --- 1. Configuração Inicial ---
st.set_page_config(page_title="Portal IQ - Totale", layout="wide", initial_sidebar_state="expanded")

# Variáveis de Sessão
if 'logado' not in st.session_state: st.session_state['logado'] = False
if 'pagina_atual' not in st.session_state: st.session_state['pagina_atual'] = "Dashboard"
if 'agenda_matinal' not in st.session_state: st.session_state['agenda_matinal'] = {}

# --- 2. Leitura de Dados ---
@st.cache_data
def carregar_dados():
    try:
        dados_iqs = pd.read_excel('PORTAL IQ.xlsx', sheet_name='Base_IQ')
        dados_tecnicos = pd.read_excel('PORTAL IQ.xlsx', sheet_name='Base_Tecnicos')
        dados_certificados = pd.read_excel('PORTAL IQ.xlsx', sheet_name='Certificados')
        
        dados_iqs['re_iq'] = dados_iqs['re_iq'].astype(str).str.strip().str.replace('.0', '', regex=False)
        dados_iqs['senha'] = dados_iqs['senha'].astype(str).str.strip()
        dados_iqs['PERFIL'] = dados_iqs.get('PERFIL', 'IQ').astype(str).str.strip().str.upper()
        
        dados_tecnicos['login'] = dados_tecnicos['login'].astype(str).str.strip().str.replace('.0', '', regex=False)
        dados_tecnicos['re_iq_responsavel'] = dados_tecnicos['re_iq_responsavel'].astype(str).str.strip().str.replace('.0', '', regex=False)
        dados_tecnicos['status_certificacao'] = dados_tecnicos['status_certificacao'].astype(str).str.strip().str.upper()

        if 'LOGIN' in dados_certificados.columns:
            dados_certificados['LOGIN'] = dados_certificados['LOGIN'].astype(str).str.strip().str.replace('.0', '', regex=False)
            dados_completos = pd.merge(dados_tecnicos, dados_certificados, left_on='login', right_on='LOGIN', how='left')
        else:
            dados_completos = dados_tecnicos
            
        return dados_iqs, dados_completos
    except Exception as e:
        st.error(f"Erro ao ler a planilha. Detalhe: {e}")
        st.stop()

dados_iqs, dados_completos = carregar_dados()

# Função para colorir a tabela (SIM verde / NÃO vermelho)
def colorir_sim_nao(val):
    if val == 'SIM': return 'background-color: #d4edda; color: #155724; font-weight: bold;'
    elif val == 'NÃO': return 'background-color: #f8d7da; color: #721c24; font-weight: bold;'
    return ''

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
        st.warning("⚠️ Na versão final, essa alteração será salva no Google Sheets. No momento, está em modo demonstração.")
        re_esqueci = st.text_input("Seu RE", key="re_esqueci")
        senha_atual = st.text_input("Senha Atual (ou Provisória)", type="password", key="senha_atual")
        senha_nova = st.text_input("Nova Senha", type="password", key="senha_nova")
        if st.button("Salvar Nova Senha"):
            st.success("Configuração de senha atualizada com sucesso!")

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
        
        # Filtro de colunas (removendo Região)
        colunas_exibicao = ['login', 'nome', 'status_certificacao']
        colunas_meses = [col for col in equipe_iq.columns if 'CERTIFICADO ' in str(col).upper()]
        colunas_exibicao.extend(colunas_meses)
        equipe_exibicao = equipe_iq[[col for col in colunas_exibicao if col in equipe_iq.columns]]
        
        # Tabela Certificados (Colorida)
        st.subheader("✅ Técnicos Certificados (Histórico)")
        df_certificados = equipe_exibicao[equipe_exibicao['status_certificacao'] == 'SIM']
        if df_certificados.empty:
            st.info("Nenhum técnico certificado.")
        else:
            st.dataframe(df_certificados.style.applymap(colorir_sim_nao, subset=['status_certificacao']), hide_index=True, use_container_width=True)
        
        # Monitoramento Manual
        st.divider()
        st.subheader("⚠️ Técnicos em Monitoramento (Seleção Manual)")
        st.write("Adicione manualmente os técnicos que necessitam de acompanhamento:")
        
        tecnicos_nao_cert = equipe_exibicao[equipe_exibicao['status_certificacao'] == 'NÃO']['nome'].tolist()
        tecnicos_selecionados = st.multiselect("Selecione os Técnicos para Acompanhamento:", options=tecnicos_nao_cert)
        
        if tecnicos_selecionados:
            for tec in tecnicos_selecionados:
                with st.expander(f"👤 {tec}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.text_input("Contrato Atual:", key=f"cont_{tec}")
                        st.date_input("Data do Monitoramento:", key=f"data_{tec}", format="DD/MM/YYYY")
                    with col2:
                        st.text_area("Observações:", key=f"obs_{tec}")
                    if st.button("Salvar Dados do Acompanhamento", key=f"btn_{tec}"):
                        st.success("Salvo com sucesso!")

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
                data_agendada = st.date_input("Escolha o Dia e Mês:", format="DD/MM/YYYY")
                
            if st.button("Adicionar à Agenda", type="primary"):
                if tec_agendar != "Selecione...":
                    st.session_state['agenda_matinal'][tec_agendar] = data_agendada.strftime("%d/%m/%Y")
                    st.success(f"Agendado para {data_agendada.strftime('%d/%m/%Y')}!")
            
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
                
                # Lista Completa Baseada no Matinal_2026.xlsx
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
                        st.success(f"Matinal de {tec_atual} concluída!")
                        st.markdown(f'📩 **[Clique aqui para enviar o relatório por E-mail]({url_email})**')
