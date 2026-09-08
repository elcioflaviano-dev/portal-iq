import streamlit as st
import pandas as pd

# 1. Leitura de Dados
try:
    dados_iqs = pd.read_excel('PORTAL IQ.xlsx', sheet_name='Base_IQ')
    dados_tecnicos = pd.read_excel('PORTAL IQ.xlsx', sheet_name='Base_Tecnicos')
    dados_certificados = pd.read_excel('PORTAL IQ.xlsx', sheet_name='Certificados')
    
    # Tratamentos básicos de padronização
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

    # Mesclagem das bases
    if 'LOGIN' in dados_certificados.columns:
        dados_certificados['LOGIN'] = dados_certificados['LOGIN'].astype(str).str.strip().str.replace('.0', '', regex=False)
        dados_completos = pd.merge(dados_tecnicos, dados_certificados, left_on='login', right_on='LOGIN', how='left')
        dados_completos = dados_completos.drop(columns=['LOGIN'])
    else:
        dados_completos = dados_tecnicos

except Exception as e:
    st.error(f"Erro ao ler a planilha. Detalhe: {e}")
    st.stop()

# 2. Configuração
st.set_page_config(page_title="Portal do IQ", layout="wide")

if 'logado' not in st.session_state:
    st.session_state['logado'] = False
if 're_usuario' not in st.session_state:
    st.session_state['re_usuario'] = ""

# 3. Login
if not st.session_state['logado']:
    st.title("Portal do IQ")
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

# 4. Dashboard e Agendamento
else:
    if st.session_state.get('perfil') == 'GESTÃO':
        st.title(f"Painel de Gestão - {st.session_state['nome_iq']}")
        equipe = dados_completos
    else:
        st.title(f"Portal IQ - {st.session_state['nome_iq']}")
        equipe = dados_completos[dados_completos['re_iq_responsavel'] == st.session_state['re_usuario']]
    
    if st.button("Sair"):
        st.session_state['logado'] = False
        st.session_state['re_usuario'] = ""
        st.rerun()

    # Define colunas base
    colunas_exibicao = ['login', 'nome', 'status_certificacao', 'Acompanhamento', 'regiao']
    colunas_meses = [col for col in equipe.columns if 'CERTIFICADO ' in str(col).upper()]
    colunas_exibicao.extend(colunas_meses)
    colunas_exibicao = [col for col in colunas_exibicao if col in equipe.columns]
    
    equipe_exibicao = equipe[colunas_exibicao]
    
    # Imagem 1: Técnicos Certificados (Histórico Mensal)
    certificados = equipe_exibicao[equipe_exibicao['status_certificacao'] == 'CERTIFICADO']
    st.write("✅ **Técnicos Certificados (Histórico Mensal)**")
    st.dataframe(certificados, hide_index=True, use_container_width=True)
    
    # Imagem 2: Técnicos em Monitoramento (Os que NÃO são certificados)
    monitoramento = equipe_exibicao[equipe_exibicao['status_certificacao'] != 'CERTIFICADO']
    st.write("⚠️ **Técnicos em Monitoramento**")
    st.dataframe(monitoramento, hide_index=True, use_container_width=True)
    
    # Imagem 3: Formulário de Matinal Baseado na Planilha 2026
    st.divider()
    st.subheader("📝 Registro de Matinal e Acompanhamento")
    
    if not equipe.empty:
        lista_certificados = equipe[equipe['status_certificacao'] == 'CERTIFICADO']['nome'].tolist()
        # Técnicos a serem acompanhados: Aqueles com Acompanhamento = SIM
        lista_acompanhamento = equipe[equipe['Acompanhamento'] == 'SIM']['nome'].tolist()
        
        col1, col2 = st.columns(2)
        with col1:
            tecnico_certificado = st.selectbox("Técnico Certificado (Guia):", ["Selecione..."] + lista_certificados)
        with col2:
            tecnico_monitorado = st.selectbox("Técnico a ser acompanhado:", ["Selecione..."] + lista_acompanhamento)
            
        dia_matinal = st.selectbox("Dia da Semana:", ['Segunda-feira', 'Terça-feira', 'Quarta-feira', 'Quinta-feira', 'Sexta-feira', 'Sábado'])
        
        # Baseado nas colunas do arquivo Matinal_2026.xlsx
        st.write("📋 **Checklist de Verificação - Padrão 2026**")
        
        col_chk1, col_chk2 = st.columns(2)
        with col_chk1:
            st.markdown("**Ferramental & Equipamentos**")
            ch_ferramentas = st.checkbox("Kit de Ferramentas / Alicates completos")
            ch_gpon = st.checkbox("Kit GPON / Medidores")
            ch_escada = st.checkbox("Escada / Suportes em bom estado")
            
        with col_chk2:
            st.markdown("**EPI / Asseio / Veículo**")
            ch_epi = st.checkbox("EPIs (Luvas, Óculos, Capacete, Cinto)")
            ch_asseio = st.checkbox("Asseio (Uniforme, Crachá, Bota)")
            ch_veiculo = st.checkbox("Veículo (Limpeza / Organização)")
            
        falhas = st.text_area("Apontamento de Falhas / Pontos de Atenção adicionais:")
        foto_upload = st.file_uploader("📸 Enviar Foto Obrigatória", type=['png', 'jpg', 'jpeg'])
        
        if st.button("Registrar e Enviar Aviso", type="primary"):
            if tecnico_certificado == "Selecione..." or tecnico_monitorado == "Selecione...":
                st.warning("⚠️ Selecione o guia e o técnico que será acompanhado.")
            elif foto_upload is None:
                st.warning("⚠️ O envio da foto é obrigatório para registrar a ação.")
            else:
                st.success(f"✅ Matinal de {tecnico_monitorado} com o guia {tecnico_certificado} agendada para {dia_matinal}!")
    else:
        st.info("Nenhum técnico cadastrado.")
