import streamlit as st
import pandas as pd

# 1. Lendo o Banco de Dados Real (Excel)
# O Streamlit vai ler as abas do arquivo que você subiu
dados_iqs = pd.read_excel('PORTAL IQ.xlsx', sheet_name='Base_IQ')
# Lendo os técnicos e garantindo que login e re sejam tratados como texto para não perder zeros
dados_tecnicos = pd.read_excel('PORTAL IQ.xlsx', sheet_name='Base_Tecnicos', dtype={'login': str, 're_iq_responsavel': str})

# 2. Configuração da Página
st.set_page_config(page_title="Portal do IQ", layout="centered")

# Variável de controle de sessão para o login
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
        # Validação do login
        iq_valido = dados_iqs[(dados_iqs['re_iq'] == re_input) & (dados_iqs['senha'] == senha_input)]
        
        if not iq_valido.empty:
            st.session_state['logado'] = True
            st.session_state['re_usuario'] = re_input
            st.session_state['nome_iq'] = iq_valido.iloc[0]['nome_iq']
            st.rerun()
        else:
            st.error("RE ou Senha incorretos.")

# 4. Tela Principal (Dashboard do IQ)
else:
    st.title(f"Bem-vindo, IQ {st.session_state['nome_iq']}")
    
    # Botão de sair
    if st.button("Sair"):
        st.session_state['logado'] = False
        st.session_state['re_usuario'] = ""
        st.rerun()
        
    st.subheader("Sua Equipe de Técnicos")
    
    # Filtrar apenas os técnicos do IQ logado
    equipe = dados_tecnicos[dados_tecnicos['re_iq_responsavel'] == st.session_state['re_usuario']]
    
    # Organizar a ordem das colunas para exibir login e nome primeiro
    equipe_exibicao = equipe[['login', 'nome', 'status_certificacao', 'regiao']]
    
    # Dividir as tabelas por status
    certificados = equipe_exibicao[equipe_exibicao['status_certificacao'] == 'Certificado']
    monitoramento = equipe_exibicao[equipe_exibicao['status_certificacao'] == 'Em Monitoramento']
    
    st.write("✅ **Técnicos Certificados**")
    st.dataframe(certificados, hide_index=True, use_container_width=True)
    
    st.write("⚠️ **Técnicos em Monitoramento (Necessitam Matinal)**")
    st.dataframe(monitoramento, hide_index=True, use_container_width=True)
