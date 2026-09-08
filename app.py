import streamlit as st
import pandas as pd

# 1. Lendo o Banco de Dados Real (Excel)
# Usando o novo nome do arquivo
dados_iqs = pd.read_excel('PORTAL IQ.xlsx', sheet_name='Base_IQ', dtype={'re_iq': str})

# Adicionada a leitura da coluna 'RE' como texto
dados_tecnicos = pd.read_excel('PORTAL IQ.xlsx', sheet_name='Base_Tecnicos', dtype={'login': str, 'RE': str, 're_iq_responsavel': str})

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

st.divider()
    st.subheader("📝 Registro de Matinal / Monitoria")
    
    # Seleção do Técnico
    tecnico_selecionado = st.selectbox("Selecione o Técnico:", equipe['nome'].tolist())
    
    # Escolha do Dia da Semana
    dias_semana = ['Segunda-feira', 'Terça-feira', 'Quarta-feira', 'Quinta-feira', 'Sexta-feira', 'Sábado']
    dia_matinal = st.selectbox("Dia da Semana para Matinal:", dias_semana)
    
    # Campo para apontar as falhas
    falhas = st.text_area("Apontamento de Falhas / Pontos de Atenção:")
    
    # OBRIGATÓRIO: Botão para enviar foto (abre a câmera no celular)
    foto_upload = st.file_uploader("📸 Enviar Foto Obrigatória (Matinal/Monitoria)", type=['png', 'jpg', 'jpeg'])
    
    if st.button("Registrar e Enviar Aviso"):
        if foto_upload is None:
            st.warning("⚠️ O envio da foto é obrigatório para registrar a ação.")
        elif falhas == "":
            st.warning("⚠️ É necessário preencher o apontamento de falhas.")
        else:
            st.success(f"✅ Matinal de {tecnico_selecionado} agendada para {dia_matinal} com sucesso!")
            # Aqui entrará a automação de e-mail e WhatsApp no próximo passo
