import streamlit as st
import pandas as pd

# 1. Lendo o Banco de Dados Real (Excel)
try:
    dados_iqs = pd.read_excel('PORTAL IQ.xlsx', sheet_name='Base_IQ')
    dados_tecnicos = pd.read_excel('PORTAL IQ.xlsx', sheet_name='Base_Tecnicos')
    dados_certificados = pd.read_excel('PORTAL IQ.xlsx', sheet_name='Certificados')
    
    # Tratamento de dados: limpeza de espaços e padronização
    dados_iqs['re_iq'] = dados_iqs['re_iq'].astype(str).str.strip().str.replace('.0', '', regex=False)
    dados_iqs['senha'] = dados_iqs['senha'].astype(str).str.strip()
    
    if 'PERFIL' in dados_iqs.columns:
        dados_iqs['PERFIL'] = dados_iqs['PERFIL'].astype(str).str.strip().str.upper()
    else:
        dados_iqs['PERFIL'] = 'IQ' # Padrão caso a coluna falte
    
    dados_tecnicos['login'] = dados_tecnicos['login'].astype(str).str.strip().str.replace('.0', '', regex=False)
    dados_tecnicos['re_iq_responsavel'] = dados_tecnicos['re_iq_responsavel'].astype(str).str.strip().str.replace('.0', '', regex=False)
    dados_tecnicos['status_certificacao'] = dados_tecnicos['status_certificacao'].astype(str).str.strip().str.upper()
    
    if 'RE' in dados_tecnicos.columns:
        dados_tecnicos['RE'] = dados_tecnicos['RE'].astype(str).str.strip().str.replace('.0', '', regex=False)
        
    if 'Acompanhamento' not in dados_tecnicos.columns:
        dados_tecnicos['Acompanhamento'] = 'NÃO'
    else:
        dados_tecnicos['Acompanhamento'] = dados_tecnicos['Acompanhamento'].astype(str).str.strip().str.upper()

    # Tratamento da aba de Certificados e Mesclagem
    if 'LOGIN' in dados_certificados.columns:
        dados_certificados['LOGIN'] = dados_certificados['LOGIN'].astype(str).str.strip().str.replace('.0', '', regex=False)
        # Cruza os dados da base de técnicos com o histórico de meses via login
        dados_completos = pd.merge(dados_tecnicos, dados_certificados, left_on='login', right_on='LOGIN', how='left')
        dados_completos = dados_completos.drop(columns=['LOGIN'])
    else:
        dados_completos = dados_tecnicos

except Exception as e:
    st.error(f"Erro ao ler a planilha. Verifique os nomes das abas e colunas. Detalhe: {e}")
    st.stop()

# 2. Configuração da Página
st.set_page_config(page_title="Portal do IQ", layout="wide")

if 'logado' not in st.session_state:
    st.session_state['logado'] = False
if 're_usuario' not in st.session_state:
    st.session_state['re_usuario'] = ""

# 3. Tela de Login
if not st.session_state['logado']:
    st.title("Portal do IQ - Acesso Móvel")
    re_input = st.text_input("RE (Login)")
    senha_input = st.text_input("Senha", type="password")
    
    if st.button("Entrar"):
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

# 4. Tela Principal (Dashboard)
else:
    # Cabeçalho dinâmico por perfil
    if st.session_state.get('perfil') == 'GESTÃO':
        st.title(f"Painel de Gestão Operacional")
        st.subheader(f"Gestor: {st.session_state['nome_iq']}")
        st.info("Modo Gestor: Visualizando todos os técnicos da operação.")
        equipe = dados_completos
    else:
        st.title(f"Bem-vindo, IQ {st.session_state['nome_iq']}")
        st.subheader("Sua Equipe de Técnicos")
        equipe = dados_completos[dados_completos['re_iq_responsavel'] == st.session_state['re_usuario']]
    
    if st.button("Sair"):
        st.session_state['logado'] = False
        st.session_state['re_usuario'] = ""
        st.rerun()
        
    # Organização das colunas (Login e Nome primeiro)
    colunas_exibicao = ['login']
    if 'RE' in equipe.columns: 
        colunas_exibicao.append('RE')
    colunas_exibicao.extend(['nome', 'status_certificacao', 'Acompanhamento', 'regiao'])
    
    # Captura automaticamente todas as colunas de meses (que contêm 'CERTIFICADO ')
    colunas_meses = [col for col in equipe.columns if 'CERTIFICADO ' in str(col).upper()]
    colunas_exibicao.extend(colunas_meses)
    
    # Filtra as colunas que realmente existem no dataframe para evitar erros
    colunas_exibicao = [col for col in colunas_exibicao if col in equipe.columns]
    equipe_exibicao = equipe[colunas_exibicao]
        
    certificados = equipe_exibicao[equipe_exibicao['status_certificacao'] == 'CERTIFICADO']
    monitoramento = equipe_exibicao[equipe_exibicao['status_certificacao'] != 'CERTIFICADO']
    
    st.write("✅ **Técnicos Certificados (Histórico Mensal)**")
    st.dataframe(certificados, hide_index=True, use_container_width=True)
    
    st.write("⚠️ **Técnicos em Monitoramento**")
    st.dataframe(monitoramento, hide_index=True, use_container_width=True)
    
    # 5. Agendamento de Matinal / Monitoria
    st.divider()
    st.subheader("📝 Registro de Matinal e Acompanhamento")
    
    if not equipe.empty:
        lista_certificados = equipe[equipe['status_certificacao'] == 'CERTIFICADO']['nome'].tolist()
        lista_acompanhamento = equipe[equipe['Acompanhamento'] == 'SIM']['nome'].tolist()
        
        col1, col2 = st.columns(2)
        
        with col1:
            tecnico_certificado = st.selectbox("Técnico Certificado (Guia):", ["Selecione..."] + lista_certificados)
            
        with col2:
            tecnico_monitorado = st.selectbox("Técnico a ser acompanhado:", ["Selecione..."] + lista_acompanhamento)
            
        dia_matinal = st.selectbox("Dia da Semana para Matinal:", ['Segunda-feira', 'Terça-feira', 'Quarta-feira', 'Quinta-feira', 'Sexta-feira', 'Sábado'])
        
        st.write("📋 **Checklist de Verificação (Matinal)**")
        check1 = st.checkbox("EPIs completos e em bom estado")
        check2 = st.checkbox("Ferramentas organizadas")
        check3 = st.checkbox("Veículo inspecionado")
        
        falhas = st.text_area("Apontamento de Falhas / Pontos de Atenção adicionais:")
        
        foto_upload = st.file_uploader("📸 Enviar Foto Obrigatória (Matinal/Monitoria)", type=['png', 'jpg', 'jpeg'])
        
        if st.button("Registrar e Enviar Aviso", type="primary"):
            if tecnico_certificado == "Selecione..." or tecnico_monitorado == "Selecione...":
                st.warning("⚠️ Selecione o técnico certificado e o técnico que será acompanhado.")
            elif foto_upload is None:
                st.warning("⚠️ O envio da foto é obrigatório para registrar a ação.")
            else:
                st.success(f"✅ Acompanhamento de {tecnico_monitorado} pelo técnico {tecnico_certificado} agendado para {dia_matinal}!")
    else:
        st.info("Nenhum técnico cadastrado para visualização no momento.")
