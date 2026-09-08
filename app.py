import streamlit as st
import pandas as pd

# 1. Lendo o Banco de Dados Real (Excel)
try:
    dados_iqs = pd.read_excel('PORTAL IQ.xlsx', sheet_name='Base_IQ')
    dados_tecnicos = pd.read_excel('PORTAL IQ.xlsx', sheet_name='Base_Tecnicos')
    
    # TRATAMENTO ANTI-ERRO: Limpar espaços e forçar tudo a ser texto
    dados_iqs['re_iq'] = dados_iqs['re_iq'].astype(str).str.strip()
    dados_iqs['re_iq'] = dados_iqs['re_iq'].apply(lambda x: x.replace('.0', '') if x.endswith('.0') else x)
    dados_iqs['senha'] = dados_iqs['senha'].astype(str).str.strip()
    
    dados_tecnicos['login'] = dados_tecnicos['login'].astype(str).str.strip()
    dados_tecnicos['login'] = dados_tecnicos['login'].apply(lambda x: x.replace('.0', '') if x.endswith('.0') else x)
    
    if 'RE' in dados_tecnicos.columns:
        dados_tecnicos['RE'] = dados_tecnicos['RE'].astype(str).str.strip()
        dados_tecnicos['RE'] = dados_tecnicos['RE'].apply(lambda x: x.replace('.0', '') if x.endswith('.0') else x)
        
    dados_tecnicos['re_iq_responsavel'] = dados_tecnicos['re_iq_responsavel'].astype(str).str.strip()
    dados_tecnicos['re_iq_responsavel'] = dados_tecnicos['re_iq_responsavel'].apply(lambda x: x.replace('.0', '') if x.endswith('.0') else x)

except Exception as e:
    st.error("Erro ao ler a planilha. Verifique se as abas 'Base_IQ' e 'Base_Tecnicos' existem.")
    st.stop()

# 2. Configuração da Página
st.set_page_config(page_title="Portal do IQ", layout="centered")

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
        # Limpa o que o usuário digitou no celular (tira espaços)
        re_limpo = re_input.strip()
        senha_limpa = senha_input.strip()
        
        # Validação
        iq_valido = dados_iqs[(dados_iqs['re_iq'] == re_limpo) & (dados_iqs['senha'] == senha_limpa)]
        
        if not iq_valido.empty:
            st.session_state['logado'] = True
            st.session_state['re_usuario'] = re_limpo
            st.session_state['nome_iq'] = iq_valido.iloc[0]['nome_iq']
            st.rerun()
        else:
            st.error("RE ou Senha incorretos.")

# 4. Tela Principal (Dashboard do IQ)
else:
    st.title(f"Bem-vindo, IQ {st.session_state['nome_iq']}")
    
    if st.button("Sair"):
        st.session_state['logado'] = False
        st.session_state['re_usuario'] = ""
        st.rerun()
        
    st.subheader("Sua Equipe de Técnicos")
    
    # Filtrar técnicos
    equipe = dados_tecnicos[dados_tecnicos['re_iq_responsavel'] == st.session_state['re_usuario']]
    
    # Exibir Login e Nome antes da Geo (Região)
    if 'RE' in equipe.columns:
        equipe_exibicao = equipe[['login', 'RE', 'nome', 'status_certificacao', 'regiao']]
    else:
        equipe_exibicao = equipe[['login', 'nome', 'status_certificacao', 'regiao']]
        
    certificados = equipe_exibicao[equipe_exibicao['status_certificacao'] == 'Certificado']
    monitoramento = equipe_exibicao[equipe_exibicao['status_certificacao'] == 'Em Monitoramento']
    
    st.write("✅ **Técnicos Certificados**")
    st.dataframe(certificados, hide_index=True, use_container_width=True)
    
    st.write("⚠️ **Técnicos em Monitoramento (Necessitam Matinal)**")
    st.dataframe(monitoramento, hide_index=True, use_container_width=True)
    
    # 5. Agendamento de Matinal / Monitoria
    st.divider()
    st.subheader("📝 Registro de Matinal / Monitoria")
    
    if not equipe.empty:
        tecnico_selecionado = st.selectbox("Selecione o Técnico:", equipe['nome'].tolist())
        
        dias_semana = ['Segunda-feira', 'Terça-feira', 'Quarta-feira', 'Quinta-feira', 'Sexta-feira', 'Sábado']
        dia_matinal = st.selectbox("Dia da Semana para Matinal:", dias_semana)
        
        falhas = st.text_area("Apontamento de Falhas / Pontos de Atenção:")
        
        foto_upload = st.file_uploader("📸 Enviar Foto Obrigatória (Matinal/Monitoria)", type=['png', 'jpg', 'jpeg'])
        
        if st.button("Registrar e Enviar Aviso"):
            if foto_upload is None:
                st.warning("⚠️ O envio da foto é obrigatório para registrar a ação.")
            elif falhas == "":
                st.warning("⚠️ É necessário preencher o apontamento de falhas.")
            else:
                st.success(f"✅ Matinal de {tecnico_selecionado} agendada para {dia_matinal} com sucesso!")
    else:
        st.info("Nenhum técnico cadastrado para este IQ.")
