import streamlit as st
import pandas as pd
from PIL import Image
import os
import urllib.parse
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta, timezone
import uuid
import io
import time

# Importação para Google Calendar API
from googleapiclient.discovery import build
from google.oauth2 import service_account

# Importação do Cloudinary
import cloudinary
import cloudinary.uploader

# --- FUSO HORÁRIO DO BRASIL (UTC-3) ---
fuso_brasil = timezone(timedelta(hours=-3))

# --- CONFIGURAÇÕES DE DESTINATÁRIOS E WHATSAPP ---
DESTINATARIOS_MATINAL = "helifa.silva@totaletecnologia.com.br,alexandre.sousa@totaletecnologia.com.br,genilson.almeida@totaletecnologia.com.br,vania.ssousa@totaletecnologia.com.br,elcio.nunes@totaletecnologia.com.br,denis.vick@totaletecnologia.com.br,paulo.correia@totaletecnologia.com.br,richard.silva@totaletecnologia.com.br,ariel.dias@totaletecnologia.com.br,alexandre.gianechini@totaletecnologia.com.br"
DESTINATARIOS_INSTALACAO = "alexandre.sousa@totaletecnologia.com.br,genilson.almeida@totaletecnologia.com.br,vania.ssousa@totaletecnologia.com.br,elcio.nunes@totaletecnologia.com.br,denis.vick@totaletecnologia.com.br"

WHATSAPP_GRUPO_ID = "5511993259361-1587731165@g.us"

# --- LISTA DE FALHAS DE INSTALAÇÃO (POR CATEGORIA) ---
FALHAS_INSTALACAO = {
    "Tap/Isolador/Emenda": [
        "001G-Identificação do cabo", "002G-Torque correto na conexão do TAP", "003G-Anel de vedação no TAP",
        "004G-Preparação dos conectores no TAP", "005M-Abraçadeiras", "006G-Ponto da Âncora no poste Elétrica",
        "007G-Ponto da Âncora no poste Assinante", "008G-Afastamento da rede elétrica",
        "009G-Altura do drop (trav 5,15m) (c/gar 4,5m) (s/gar 3,5m)", "010G-Parafuso olhal reto (pitão)",
        "011G-Integridade do cabo", "012G-Instalação do isolator", "013G-Pingadeira do cabo Isolador/Emenda",
        "014G-Anel de vedação/ fita fusão Isolator/Emenda", "015G-Preparação dos conectores do Isolator/Emenda",
        "016G-Conexão em poste correto", "067G-Divisor na Rede"
    ],
    "DG/Apto": [
        "017G-Identificação do cabo", "018G-Torque correto na conexão do DG", "019G-Preparação dos conectores do DG",
        "020M-Disposição do cabo (dentro do DG)", "021M-Roteamento do Cabo", "022M-Fixação do cabo"
    ],
    "PAQ": [
        "023G-Identificação do funcionário (uniformizado e crahá em local visivel)", "024G-Educação do técnico (instalador atencioso)",
        "025G-Confirmação do produto antes da instalação", "026M-Uso do Pro-pé", "027G-Limpeza (deixau o local limpo e organizado)",
        "028M-Entrega da Guia da OS/Orientação sobre envio da documentação", "029G-Explicação do sistema (funcionalidades e interatividas do produto)",
        "030G-Explicação sobre o Now", "031M-Preencimento da OS (verificar na guia do cliente)", "032M-Assinatura da OS",
        "033G-Técnico não chegou no horário combinado", "034G-Satisfação Geral < 7", "088G-Uso do Santinho"
    ],
    "Cabeamento Interior": [
        "035M-Ponto de entrada em local adequado", "036M-Pingadeira Ponto de Entrada", "037M-Bucha de acabamento",
        "038M-Excesso/falta de cabo", "039M-Organização do cabo", "040G-Integridade do cabo",
        "041M-Local de fixação do cabo", "042M-Fixação correta do cabo", "043M-Local de fixação do passivo",
        "044M-Fixação correta do passivo", "045G-Torque correto nas conexões", "046G-Conexão correta nos passivos",
        "047G-Instalação de extensões do Net Fone", "048G-Serviço executado sem aut NET", "049G-Configuração/habilitação correta",
        "050G-Sintonia da TV/AV/HDMI", "051G-Qualidade do sinal (Imagem)", "052G-Qualidade do sinal (Internet)",
        "053G-Qualidade do sinal (Voz)", "055G-Danos causados na instalação", "095G-Instalação de Mini Isolator com Sleev",
        "096G-Preenchimento da Etiqueta WIFI ou O.S", "097G-Rede WIFI configurada/instalada"
    ],
    "Medição de Sinal": [
        "056M-Nivel correto do canal baixo", "057M-Nivel correto do canal alto", "058G-Nivel correto do TX",
        "059G-Nivel correto do RX", "060G-Qualidade do sinal - PS/QS/BER", "098G-WIFI - Técnico garantiu a cobertura em 80% dos cômodos",
        "099G-WIFI - Técnico orientou cliente sobre a cobertura do Wi-Fi (Obs. na OS)"
    ],
    "Divergência de Materiais": [
        "061G-Cabos", "062G-Conectores", "063G-Passivos", "064G-Terminais"
    ],
    "Outros": [
        "087G-Instalação ocorreu no endereço do contrato"
    ]
}

ITENS_MATINAL = {
    "🛠️ Ferramental": [
        "ALICATE CRIMPADOR RG59/58 (PRESSÃO)", "ALICATE CRIMPADOR RJ11/45", "ALICATE DE BICO RETO 6\"", 
        "ALICATE DE CORTE DIAGONAL 6\"", "ALICATE UNIVERSAL 8\"", "CHAVE DE FENDA 1/4 (GRANDE)", 
        "CHAVE DE FENDA 3/16 (MÉDIA)", "CHAVE DE FENDA 1/8 (PEQUENA)", "CHAVE PHILLIPS 1/4 (GRANDE)", 
        "CHAVE PHILLIPS 3/16 (MÉDIA)", "CHAVE PHILLIPS 1/8 (PEQUENA)", "CHAVE TRAVA LOCK - (Preta)", 
        "CHAVE GTP SEGURANÇA - (Azul)", "ESTILETE 18MM C/ TRAVA", "CHAVE TORQUE", "CHAVE BQ", 
        "ORGANIZADOR DE FERRAMENTAS", "STRIPER (DESCASCADOR) RG59/58", "FITA GUIA DE NYLON 20Mts", 
        "MARTELO UNHA (500G)", "FUZIMEC (CINTADEIRA)", "FURADEIRA DE IMPACTO", 
        "EXTENSÃO DE TOMADA ELÉTRICA DE 10 A 20M", "BROCA DE WÍDEA LONGA 8\"", "BROCA DE WÍDEA LONGA 10\"", 
        "MALA DE FERRAMENTAS", "BALDE DE LONA (BORNAL)", "TELEFONE GÔNDOLA COM IDENTIFICADOR DE CHAMADA", 
        "LANTERNA", "ESCADA DE FIBRA (6Mts)", "ESCADA DE 4 E/OU 5 DEGRAUS ALTURA UTIL 1.50m (MÍNIMO)", 
        "CÂMERA SONDA ENDOSCÓPICA", "CHAVEIRO MINI ISOLATOR", "capa de mini", "numeral"
    ],
    "📡 GPON/Outros": [
        "CLIVADOR COM GABARITO PROFIBER", "GABARITO DE CONECTORIZAÇÃO", "ALICATE DECAPADOR DE FIBRA ÓPTICA", 
        "SUPORTE DE ESCADA PARA CLIVADOR", "SUPORTE PARA BOBINA DE CABO", "TESTADOR DE CABO DE REDE", 
        "CANETA DE LIMPEZA ÓPTICA", "ALICATE DECAPADOR DE DROP (BETTER)",
        "BOOK FISCAL", "MANTA DE PROTEÇÃO", "FLANELA", "CHIP DE TELEFONIA", "ESCOVA DE LIMPEZA E PÁ DE LIXO", 
        "KIT LENÇOS PARA LIMPEZA FIBRA AGC", "ÁLCOOL ISOPROPÍLICO", "DISPENSER PARA LÍQUIDOS",
        "DBAM / TRILITHIC", "POWER METER", "CANETA ÓPTICA"
    ],
    "👷 EPI / EPC": [
        "CAPACETE COM ABA TOTAL E JUGULAR", "CAPA DE CHUVA", "CINTO DE SEGURANÇA", 
        "TALABARTE DE SEGURANÇA - POSICIONAMENTO E/O ANCORAGEM", "KIT LVM", "PAR DE LUVAS PIGMENTADA", 
        "PAR DE LUVAS DE VAQUETA (COURO)", "ÓCULOS DE PROTEÇÃO", "3 CONES", "BANDEIROLA PARA ESCADA DE 6Mts", 
        "NIVELADOR DE ESCADA", "MULTIMETRO OU CHAVE TESTE", "MÁSCARA PROTEÇÃO SEMIFACIAL", 
        "ROLO DE FITA ZEBRADA", "PROTETOR SOLAR", "PRO-PÉ",
        "Escada: Bandeirola", "Escada: Papagaio", "Escada: Sapata", "Escada: Guia de ponta da escada", "Escada: Cinta de Borracha"
    ],
    "🧹 Asseio": [
        "Barba feita", "Higiene pessoal", "Corte de cabelo padrão Claro", "Uso de adornos", "Crachá"
    ],
    "📱 Sistemas": [
        "PDA (Logado e bateria com mínimo de 50%)", 
        "Acesso Conectado/Nota 10 (verificar treinamentos de 1 ponto pendentes)", 
        "Acesso ao Conectale (portal da empresa)"
    ],
    "🚗 Veículo": [
        "Veículo Interno: Organizado?", "Veículo Interno: Limpo?", "Veículo Interno: Tomada Carregamento OK?", 
        "Veículo Interno: Óleo no Nível?", "Veículo Interno: Água no Nível?",
        "Veículo Externo: Lâmpadas Queimadas?", "Veículo Externo: Pneus em Boas Condições?", 
        "Veículo Externo: Calotas OK?", "Veículo Externo: Rack OK?", "Veículo Externo: Avarias?", 
        "Veículo Externo: Bandeirola OK?", "Veículo Externo: Adesivos OK?"
    ]
}

# --- 1. Configuração Inicial ---
st.set_page_config(page_title="Portal do IQ - TOTALE ABC", layout="wide", initial_sidebar_state="expanded")

if 'logado' not in st.session_state: st.session_state['logado'] = False
if 'pagina_atual' not in st.session_state: st.session_state['pagina_atual'] = "Dashboard"
if 'email_pronto' not in st.session_state: st.session_state['email_pronto'] = None
if 'zap_pronto' not in st.session_state: st.session_state['zap_pronto'] = None
if 'zap_agenda_pronto' not in st.session_state: st.session_state['zap_agenda_pronto'] = None
if 'gcal_status' not in st.session_state: st.session_state['gcal_status'] = None
if 'tec_selecionado_atalho' not in st.session_state: st.session_state['tec_selecionado_atalho'] = None
if 'aba_matinal_ativa' not in st.session_state: st.session_state['aba_matinal_ativa'] = 0

# --- Estilização CSS ---
st.markdown("""
    <style>
    .metric-card-blue, .metric-card-green, .metric-card-orange, .metric-card-purple {
        padding: 20px;
        border-radius: 12px;
        color: white !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.15);
        margin-bottom: 10px;
    }
    .metric-card-blue { background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); }
    .metric-card-green { background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); }
    .metric-card-orange { background: linear-gradient(135deg, #f2994a 0%, #f2c94c 100%); }
    .metric-card-purple { background: linear-gradient(135deg, #654ea3 0%, #eaafc8 100%); }
    
    .metric-card-blue *, .metric-card-purple *, .metric-card-green *, .metric-card-orange * { color: white !important; }
    .metric-title { font-size: 14px; font-weight: 600; text-transform: uppercase; margin-bottom: 8px; opacity: 0.9; }
    .metric-value { font-size: 28px; font-weight: 700; margin-bottom: 5px; }
    .metric-sub { font-size: 12px; opacity: 0.85; }
    </style>
""", unsafe_allow_html=True)

# --- 2. Conexão com Google Sheets e Google Calendar (Proteção Avançada contra Erro 429) ---
def conectar_planilha():
    tentativas = 5
    espera = 3
    for tentativa in range(tentativas):
        try:
            creds_dict = json.loads(st.secrets["gcp_service_account"])
            scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
            client = gspread.authorize(creds)
            return client.open("PORTAL IQ")
        except Exception as e:
            if "429" in str(e) or "Quota exceeded" in str(e):
                if tentativa < tentativas - 1:
                    time.sleep(espera)
                    espera *= 2
                    continue
            if tentativa == tentativas - 1:
                st.error("Servidor ocupado devido a acessos simultâneos (Erro 429). Aguarde alguns segundos e tente novamente.")
                st.stop()
            time.sleep(2)

def criar_evento_google_calendar(nome_tec, data_agendamento, nome_iq, email_tec=""):
    try:
        creds_dict = json.loads(st.secrets["gcp_service_account"])
        scopes = ["https://www.googleapis.com/auth/calendar"]
        credentials = service_account.Credentials.from_service_account_info(creds_dict, scopes=scopes)
        
        service = build('calendar', 'v3', credentials=credentials)
        
        data_str = data_agendada.strftime('%Y-%m-%d')
        start_datetime = f"{data_str}T07:00:00-03:00"
        end_datetime = f"{data_str}T08:00:00-03:00"
        
        event = {
            'summary': f'Vistoria Matinal (IVM) - {nome_tec}',
            'location': 'Base TOTALE ABC',
            'description': f'Vistoria matinal agendada pelo IQ {nome_iq} com o técnico {nome_tec}.',
            'start': {
                'dateTime': start_datetime,
                'timeZone': 'America/Sao_Paulo',
            },
            'end': {
                'dateTime': end_datetime,
                'timeZone': 'America/Sao_Paulo',
            },
            'attendees': [{'email': email_tec}] if email_tec and "@" in email_tec else [],
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'popup', 'minutes': 30},
                    {'method': 'email', 'minutes': 60},
                ],
            },
        }
        
        calendar_id = 'primary'
        service.events().insert(calendarId=calendar_id, body=event, sendUpdates='all' if email_tec else 'none').execute()
        return True
    except Exception as e:
        print(f"Erro ao inserir no Google Calendar: {e}")
        return False

def registrar_log_acesso(re_iq, nome_iq, acao, pagina):
    try:
        planilha = conectar_planilha()
        try:
            ws = planilha.worksheet("Log_Acessos")
        except:
            ws = planilha.add_worksheet(title="Log_Acessos", rows=100, cols=6)
            ws.append_row(["Data_Hora", "RE_IQ", "Nome_IQ", "Acao", "Pagina"])
        
        data_hora = datetime.now(fuso_brasil).strftime("%d/%m/%Y %H:%M:%S")
        ws.append_row([data_hora, str(re_iq), nome_iq, acao, pagina])
    except Exception as e:
        print(f"Erro ao registrar log: {e}")

def alterar_senha_sheets(re_iq, nova_senha):
    try:
        planilha = conectar_planilha()
        ws = planilha.worksheet("Base_IQ")
        cabecalhos = [str(c).strip().upper() for c in ws.row_values(1)]
        col_re, col_senha = -1, -1
        
        for i, c in enumerate(cabecalhos):
            if 'RE' in c: col_re = i + 1
            if 'SENHA' in c: col_senha = i + 1
            
        if col_re == -1 or col_senha == -1:
            return False, "Colunas RE ou Senha não encontradas na Base_IQ."
            
        coluna_res = ws.col_values(col_re)
        for idx, val in enumerate(coluna_res):
            if str(val).strip().replace('.0', '') == str(re_iq).strip():
                ws.update_cell(idx + 1, col_senha, nova_senha.strip())
                return True, "Senha alterada com sucesso!"
        return False, "RE não encontrado na base."
    except Exception as e:
        return False, f"Erro ao atualizar senha: {e}"

@st.cache_data(ttl=300)
def carregar_resultados_matinal():
    try:
        planilha = conectar_planilha()
        try:
            ws = planilha.worksheet("Resultado_Matinal")
            registros = ws.get_all_records()
            return pd.DataFrame(registros) if registros else pd.DataFrame()
        except:
            ws = planilha.add_worksheet(title="Resultado_Matinal", rows=100, cols=5)
            ws.append_row(["Data", "RE_IQ", "Nome_IQ", "Nota_IQ", "Nota_Geral"])
            return pd.DataFrame()
    except:
        return pd.DataFrame()

def configurar_cloudinary():
    try:
        cloudinary.config(
            cloud_name = st.secrets["cloudinary"]["cloud_name"],
            api_key = st.secrets["cloudinary"]["api_key"],
            api_secret = st.secrets["cloudinary"]["api_secret"],
            secure = True
        )
    except Exception as e:
        st.error(f"Erro nas configurações do Cloudinary nos segredos: {e}")

def salvar_fotos_no_cloudinary(uploaded_files, nome_tecnico, tipo_pasta):
    links = []
    try:
        configurar_cloudinary()
        for i, uploaded_file in enumerate(uploaded_files):
            data_hora_str = datetime.now(fuso_brasil).strftime('%Y-%m-%d_%H-%M-%S')
            nome_limpo = "".join([c for c in nome_tecnico if c.isalnum() or c in (' ', '_')]).strip().replace(' ', '_')
            public_id = f"{tipo_pasta}/{tipo_pasta}_{nome_limpo}_{data_hora_str}_{i+1}"
            
            resultado = cloudinary.uploader.upload(
                uploaded_file,
                public_id=public_id,
                folder=tipo_pasta,
                overwrite=True,
                resource_type="image"
            )
            links.append(resultado.get("secure_url"))
        return links
    except Exception as e:
        return [f"(ERRO CLOUDINARY: {e})"]

@st.cache_data(ttl=300)
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
    
    dados_iqs.columns = [str(c).strip() for c in dados_iqs.columns]
    
    col_re_name = next((c for c in dados_iqs.columns if c.upper() == 'RE_IQ'), 're_iq')
    col_senha_name = next((c for c in dados_iqs.columns if c.upper() == 'SENHA'), 'senha')
    col_nome_name = next((c for c in dados_iqs.columns if c.upper() == 'NOME_IQ'), 'nome_iq')
    col_perfil_name = next((c for c in dados_iqs.columns if c.upper() == 'PERFIL'), 'PERFIL')
    
    col_reg_name = next((c for c in dados_iqs.columns if 'REG' in c.upper() or 'BASE' in c.upper()), None)
    
    dados_iqs['re_iq'] = dados_iqs[col_re_name].astype(str).str.strip().str.replace(r'\.0$', '', regex=True)
    dados_iqs['senha'] = dados_iqs.get(col_senha_name, '').astype(str).str.strip()
    dados_iqs['PERFIL'] = dados_iqs.get(col_perfil_name, 'IQ').astype(str).str.strip().str.upper()
    
    if col_reg_name:
        dados_iqs['REGIAO_FINAL'] = dados_iqs[col_reg_name].astype(str).str.strip()
    else:
        dados_iqs['REGIAO_FINAL'] = 'N/A'
    
    dados_tecnicos.columns = [str(c).strip() for c in dados_tecnicos.columns]
    col_login_tec = next((c for c in dados_tecnicos.columns if 'LOGIN' in c.upper()), 'login')
    dados_tecnicos['login'] = dados_tecnicos[col_login_tec].astype(str).str.strip().str.replace(r'\.0$', '', regex=True)
    
    dados_tecnicos = dados_tecnicos.drop(columns=['re_iq_responsavel'], errors='ignore')
    
    col_tel = next((c for c in dados_tecnicos.columns if 'TEL' in c.upper() or 'CEL' in c.upper() or 'WPP' in c.upper() or 'ZAP' in c.upper() or 'WHATS' in c.upper()), None)
    if col_tel:
        def forcar_ddd_11(val):
            num = ''.join([c for c in str(val) if c.isdigit()])
            if not num:
                return "5511994524040"
            if num.startswith("55"):
                num = num[2:]
            if len(num) >= 9:
                if len(num) > 9:
                    num = num[2:]
                return "5511" + num
            return "5511994524040"
            
        dados_tecnicos['telefone_tec'] = dados_tecnicos[col_tel].apply(forcar_ddd_11)
    else:
        dados_tecnicos['telefone_tec'] = '5511994524040'

    col_email = next((c for c in dados_tecnicos.columns if 'MAIL' in c.upper() or 'CORREIO' in c.upper()), None)
    if col_email:
        dados_tecnicos['email_tec'] = dados_tecnicos[col_email].astype(str).str.strip()
    else:
        dados_tecnicos['email_tec'] = ''

    colunas_remover = ['status_certificacao', 'Acompanhamento', 'Contrato', 'Data_Monitoramento', 'Observacao']
    dados_tecnicos = dados_tecnicos.drop(columns=[c for c in colunas_remover if c in dados_tecnicos.columns], errors='ignore')

    dados_completos = dados_tecnicos.copy()
    todas_abas = [ws.title for ws in planilha.worksheets()]
    
    meses_info = []
    abas_meses = [aba for aba in todas_abas if aba not in ['Base_IQ', 'Base_Tecnicos', 'Controle_IQ', 'Agenda_Matinal', 'Vistorias_Matinal', 'Vistoria_Instalacao', 'Log_Acessos', 'Resultado_Matinal']]

    for aba in abas_meses:
        df_mes = ler_aba(aba)
        if not df_mes.empty:
            mes_nome = aba.upper().replace('CERTIFICADO', '').replace('_', ' ').strip()
            if not mes_nome: mes_nome = aba.upper()
            
            colunas_novas = {}
            for c in df_mes.columns:
                c_up = str(c).strip().upper()
                if 'LOGIN' in c_up: colunas_novas[c] = 'LOGIN'
                elif 'RE' in c_up and 'IQ' in c_up: colunas_novas[c] = f're_iq_responsavel_{mes_nome}'
                elif 'ACOMPANHAMENTO' in c_up: colunas_novas[c] = f'ACOMPANHAMENTO_{mes_nome}'
                elif c_up in ['MONIT_1', 'M1']: colunas_novas[c] = f'MONIT_1_{mes_nome}'
                elif c_up in ['MONIT_2', 'M2']: colunas_novas[c] = f'MONIT_2_{mes_nome}'
                elif c_up in ['MONIT_3', 'M3']: colunas_novas[c] = f'MONIT_3_{mes_nome}'
                else:
                    if mes_nome in c_up or c_up in mes_nome:
                        colunas_novas[c] = mes_nome
            
            df_mes = df_mes.rename(columns=colunas_novas)
            
            if 'LOGIN' in df_mes.columns:
                df_mes['LOGIN'] = df_mes['LOGIN'].astype(str).str.strip().str.replace(r'\.0$', '', regex=True)
                col_re_mes_alvo = f're_iq_responsavel_{mes_nome}'
                if col_re_mes_alvo in df_mes.columns:
                    df_mes[col_re_mes_alvo] = df_mes[col_re_mes_alvo].astype(str).str.strip().str.replace(r'\.0$', '', regex=True)
                
                if mes_nome not in df_mes.columns: df_mes[mes_nome] = 'NÃO'
                if f'ACOMPANHAMENTO_{mes_nome}' not in df_mes.columns: df_mes[f'ACOMPANHAMENTO_{mes_nome}'] = 'NÃO'
                if f'MONIT_1_{mes_nome}' not in df_mes.columns: df_mes[f'MONIT_1_{mes_nome}'] = 'NÃO'
                if f'MONIT_2_{mes_nome}' not in df_mes.columns: df_mes[f'MONIT_2_{mes_nome}'] = 'NÃO'
                if f'MONIT_3_{mes_nome}' not in df_mes.columns: df_mes[f'MONIT_3_{mes_nome}'] = 'NÃO'
                
                df_mes[mes_nome] = df_mes[mes_nome].fillna('NÃO').astype(str).str.strip().str.upper()
                df_mes[f'ACOMPANHAMENTO_{mes_nome}'] = df_mes[f'ACOMPANHAMENTO_{mes_nome}'].fillna('NÃO').astype(str).str.strip().str.upper()
                
                dados_completos = pd.merge(dados_completos, df_mes, left_on='login', right_on='LOGIN', how='left')
                if 'LOGIN' in dados_completos.columns: dados_completos = dados_completos.drop(columns=['LOGIN'])
                meses_info.append({'nome_aba': aba, 'mes_nome': mes_nome})

    if not meses_info:
        meses_info = [{'nome_aba': 'Base_Tecnicos', 'mes_nome': 'AGOSTO'}]

    dados_completos = dados_completos.fillna('')
    dados_completos = dados_completos.replace(['nan', 'None', 'NaN'], '')

    return dados_iqs, dados_completos, meses_info

@st.cache_data(ttl=300)
def carregar_controle_iq():
    try:
        planilha = conectar_planilha()
        try:
            ws = planilha.worksheet("Controle_IQ")
        except:
            ws = planilha.add_worksheet(title="Controle_IQ", rows=100, cols=5)
            ws.append_row(["RE_IQ", "META_HORAS", "REALIZADO_HORAS"])
        registros = ws.get_all_records()
        return pd.DataFrame(registros) if registros else pd.DataFrame()
    except:
        return pd.DataFrame()

def carregar_agenda_matinal_sheets():
    try:
        planilha = conectar_planilha()
        try:
            ws = planilha.worksheet("Agenda_Matinal")
        except:
            ws = planilha.add_worksheet(title="Agenda_Matinal", rows=100, cols=10)
            ws.append_row(["RE_IQ", "AGENDA_TECNICO", "AGENDA_DATA", "AGENDA_IQ_NOME"])
        registros = ws.get_all_records()
        agenda_dict = {}
        for row in registros:
            tec = str(row.get('AGENDA_TECNICO', '')).strip()
            if tec:
                agenda_dict[tec] = {
                    'data': str(row.get('AGENDA_DATA', '')),
                    'iq_nome': str(row.get('AGENDA_IQ_NOME', '')),
                    're_iq': str(row.get('RE_IQ', ''))
                }
        return agenda_dict
    except:
        return {}

def salvar_horas_no_sheets(re_iq, meta, realizado):
    try:
        planilha = conectar_planilha()
        ws = planilha.worksheet("Controle_IQ")
        registros = ws.get_all_records()
        encontrou = False
        
        for idx, row in enumerate(registros):
            if str(row.get('RE_IQ', '')).strip().replace('.0', '') == str(re_iq):
                ws.update_cell(idx + 2, 2, meta)
                ws.update_cell(idx + 2, 3, realizado)
                encontrou = True
                break
        if not encontrou:
            ws.append_row([str(re_iq), meta, realizado])
        st.cache_data.clear()
    except Exception as e:
        st.error(f"Erro ao salvar horas: {e}")

def salvar_agenda_no_sheets(agenda_dict):
    try:
        planilha = conectar_planilha()
        try:
            ws = planilha.worksheet("Agenda_Matinal")
        except:
            ws = planilha.add_worksheet(title="Agenda_Matinal", rows=100, cols=10)
            
        novas_linhas = []
        for tec, info in agenda_dict.items():
            novas_linhas.append([str(info['re_iq']), tec, info['data'], info['iq_nome']])
                
        ws.clear()
        ws.append_row(["RE_IQ", "AGENDA_TECNICO", "AGENDA_DATA", "AGENDA_IQ_NOME"])
        if novas_linhas:
            ws.append_rows(novas_linhas)
        st.cache_data.clear()
    except Exception as e:
        print(f"Erro ao salvar agenda: {e}")

def registrar_vistoria_completa(re_iq, nome_iq, login_tec, nome_tec, tipo, irregulares, extra_info, obs, links_fotos):
    try:
        planilha = conectar_planilha()
        try:
            ws = planilha.worksheet("Vistorias_Matinal")
        except:
            ws = planilha.add_worksheet(title="Vistorias_Matinal", rows=100, cols=22)
            ws.append_row([
                "ID_Vistoria", "Data_Hora", "RE_IQ", "Nome_IQ", "Login_Tecnico", "Nome_Tecnico", 
                "Tipo_Vistoria", "Itens_Irregulares", "Placa_Veiculo", "Lote_Capacete", "Venc_Carneira", "Lote_Cinto", 
                "Lote_Talabarte", "Lote_Luva_Pig", "Lote_Luva_Vaq", "Venc_Protetor_Solar", 
                "Tam_Camisa", "Tam_Calca", "Tam_Jaqueta", "Observacao", "Links_Fotos", "Status"
            ])
            
        vistoria_id = str(uuid.uuid4())[:8].upper()
        data_hora = datetime.now(fuso_brasil).strftime("%d/%m/%Y %H:%M:%S")
        links_str = " | ".join(links_fotos)
        
        ws.append_row([
            vistoria_id, data_hora, str(re_iq), nome_iq, str(login_tec), nome_tec, tipo, irregulares,
            extra_info.get('placa_veiculo', ''), extra_info.get('lote_capacete', ''), extra_info.get('venc_carneira', ''), extra_info.get('lote_cinto', ''),
            extra_info.get('lote_talabarte', ''), extra_info.get('lote_luva_pig', ''),
            extra_info.get('lote_luva_vaq', ''), extra_info.get('venc_protetor', ''),
            extra_info.get('tam_camisa', ''), extra_info.get('tam_calca', ''),
            extra_info.get('tam_jaqueta', ''), obs, links_str, "Concluída"
        ])
        st.cache_data.clear()
        return vistoria_id
    except Exception as e:
        st.error(f"Erro ao gravar histórico de vistoria: {e}")
        return "ERRO"

def registrar_vistoria_instalacao_sheets(re_iq, nome_iq, login_tec, nome_tec, contrato, irregulares, obs, links_fotos):
    try:
        planilha = conectar_planilha()
        try:
            ws = planilha.worksheet("Vistoria_Instalacao")
        except:
            ws = planilha.add_worksheet(title="Vistoria_Instalacao", rows=100, cols=11)
            ws.append_row(["ID_Vistoria", "Data_Hora", "RE_IQ", "Nome_IQ", "Login_Tecnico", "Nome_Tecnico", "Contrato", "Erros_Instalacao", "Observacao", "Links_Fotos", "Status"])
            
        vistoria_id = str(uuid.uuid4())[:8].upper()
        data_hora = datetime.now(fuso_brasil).strftime("%d/%m/%Y %H:%M:%S")
        links_str = " | ".join(links_fotos)
        ws.append_row([vistoria_id, data_hora, str(re_iq), nome_iq, str(login_tec), nome_tec, str(contrato), irregulares, obs, links_str, "Registrada"])
        st.cache_data.clear()
        return vistoria_id
    except Exception as e:
        st.error(f"Erro ao gravar vistoria de instalação: {e}")
        return "ERRO"

def atualizar_celula_especifica(nome_aba, login_tecnico, coluna_alvo, valor):
    try:
        planilha = conectar_planilha()
        ws = planilha.worksheet(nome_aba)
        cabecalhos = [str(c).strip().upper() for c in ws.row_values(1)]
        col_idx = -1
        
        for i, c in enumerate(cabecalhos):
            if coluna_alvo.upper() in c:
                col_idx = i + 1
                break
        if col_idx == -1: return 
        
        col_login_idx = -1
        for i, c in enumerate(cabecalhos):
            if 'LOGIN' in c:
                col_login_idx = i + 1
                break
        if col_login_idx == -1: return
        
        coluna_logins = ws.col_values(col_login_idx)
        for row_idx, val in enumerate(coluna_logins):
            if str(val).strip().replace('.0', '') == str(login_tecnico).strip().replace('.0', ''):
                ws.update_cell(row_idx + 1, col_idx, valor)
                break
        st.cache_data.clear()
    except Exception as e:
        st.error(f"Erro ao atualizar planilha: {e}")

def colorir_sim_nao(val):
    texto = str(val).strip().upper()
    if texto == 'SIM' or '3/3 - SIM' in texto: 
        return 'background-color: #d4edda; color: #155724; font-weight: bold;'
    elif texto == 'NÃO' or texto == 'NAO' or '- NÃO' in texto: 
        return 'background-color: #f8d7da; color: #721c24; font-weight: bold;'
    return ''

def exportar_para_excel(df, nome_arquivo):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Dados')
    processed_data = output.getvalue()
    return processed_data

dados_iqs, dados_completos, meses_info = carregar_dados()

if meses_info:
    mes_vigente_info = meses_info[-1]
    mes_vigente = mes_vigente_info['mes_nome']
    if len(meses_info) >= 2:
        mes_acompanhamento_info = meses_info[-2]
        mes_acompanhamento = mes_acompanhamento_info['mes_nome']
        aba_acompanhamento = mes_acompanhamento_info['nome_aba']
    else:
        mes_acompanhamento = mes_vigente
        aba_acompanhamento = mes_vigente_info['nome_aba']
else:
    mes_vigente, aba_acompanhamento, mes_acompanhamento = None, None, None

df_ctrl = carregar_controle_iq()

# --- 3. Telas de Acesso ---
if not st.session_state['logado']:
    col_logo, _ = st.columns([1, 2])
    with col_logo:
        if os.path.exists("novo-logo-totale.png"): st.image(Image.open("novo-logo-totale.png"), use_container_width=True)
            
    st.title("Acesso Operacional - IQ TOTALE ABC")
    
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
            st.session_state['regiao_iq'] = iq_valido.iloc[0].get('REGIAO_FINAL', 'N/A')
            
            registrar_log_acesso(re_input.strip(), iq_valido.iloc[0]['nome_iq'], "LOGIN", "Dashboard")
            st.rerun()
        else:
            st.error("RE ou Senha incorretos.")

else:
    re_logado = st.session_state['re_usuario']
    re_logado_str = str(re_logado).strip().replace('.0', '')
    perfil_usuario = st.session_state.get('perfil', 'IQ')

    if 'agenda_matinal' not in st.session_state:
        st.session_state['agenda_matinal'] = carregar_agenda_matinal_sheets()

    meta_atual, realizado_atual = 60, "0"
    if not df_ctrl.empty and 'RE_IQ' in df_ctrl.columns:
        filtro_h = df_ctrl[df_ctrl['RE_IQ'].astype(str).str.strip().str.replace('.0','') == re_logado_str]
        if not filtro_h.empty:
            try: meta_atual = int(filtro_h.iloc[0]['META_HORAS']) if filtro_h.iloc[0]['META_HORAS'] != '' else 60
            except: pass
            val_real = filtro_h.iloc[0]['REALIZADO_HORAS']
            realizado_atual = str(val_real) if val_real != '' else "0"

    # Definir coluna de RE do IQ para o mês de acompanhamento atual (ex: AGOSTO)
    col_re_iq_mes_acomp = f're_iq_responsavel_{mes_acompanhamento}' if mes_acompanhamento else None

    # Gestão vs IQ (Filtro rigoroso por perfil)
    if perfil_usuario == 'GESTÃO':
        st.sidebar.divider()
        st.sidebar.subheader("🎛️ Filtro de Gestão")
        lista_iqs = dados_iqs[dados_iqs['PERFIL'] != 'GESTÃO'][['re_iq', 'nome_iq']].drop_duplicates()
        opcoes_iq = ["Visão Geral (Todos)"] + [f"{row['re_iq']} - {row['nome_iq']}" for _, row in lista_iqs.iterrows()]
        
        iq_selecionado = st.sidebar.selectbox("Visualizar painel do IQ:", opcoes_iq)
        
        if "Visão Geral" in iq_selecionado:
            equipe_vigente = dados_completos
            re_alvo_str = None
        else:
            re_alvo_str = iq_selecionado.split(" - ")[0].strip()
            if col_re_iq_mes_acomp and col_re_iq_mes_acomp in dados_completos.columns:
                equipe_vigente = dados_completos[dados_completos[col_re_iq_mes_acomp].astype(str).str.replace('.0', '') == str(re_alvo_str)]
            else:
                equipe_vigente = dados_completos
    else:
        re_alvo_str = re_logado_str
        # Garante que o IQ comum veja APENAS os técnicos vinculados a ele no mês de referência
        if col_re_iq_mes_acomp and col_re_iq_mes_acomp in dados_completos.columns:
            equipe_vigente = dados_completos[dados_completos[col_re_iq_mes_acomp].astype(str).str.replace('.0', '') == str(re_logado_str)]
        else:
            equipe_vigente = pd.DataFrame()

    with st.sidebar:
        if os.path.exists("novo-logo-totale.png"): st.image(Image.open("novo-logo-totale.png"), use_container_width=True)
        st.write(f"**Usuário:** {st.session_state['nome_iq']}")
        st.write(f"**Região:** {st.session_state.get('regiao_iq', 'N/A')}")
        st.write(f"**Perfil:** {perfil_usuario}")
        st.divider()
        
        if st.button("📊 Dashboard Inicial", use_container_width=True): 
            registrar_log_acesso(re_logado_str, st.session_state['nome_iq'], "NAVEGACAO", "Dashboard")
            st.session_state['pagina_atual'] = "Dashboard"
            st.rerun()
        if st.button("🏆 Histórico de Certificados", use_container_width=True): 
            registrar_log_acesso(re_logado_str, st.session_state['nome_iq'], "NAVEGACAO", "Historico")
            st.session_state['pagina_atual'] = "Historico"
            st.rerun()
        if st.button("📋 Agendamento de Matinal", use_container_width=True): 
            registrar_log_acesso(re_logado_str, st.session_state['nome_iq'], "NAVEGACAO", "Matinal")
            st.session_state['pagina_atual'] = "Matinal"
            st.session_state['aba_matinal_ativa'] = 0
            st.rerun()
        if st.button("🛠️ Vistoria de Instalação", use_container_width=True): 
            registrar_log_acesso(re_logado_str, st.session_state['nome_iq'], "NAVEGACAO", "Instalacao")
            st.session_state['pagina_atual'] = "Instalacao"
            st.rerun()
        if st.button("🔑 Alterar Senha", use_container_width=True):
            registrar_log_acesso(re_logado_str, st.session_state['nome_iq'], "NAVEGACAO", "AlterarSenha")
            st.session_state['pagina_atual'] = "AlterarSenha"
            st.rerun()
            
        if perfil_usuario == 'GESTÃO':
            if st.button("📥 Relatórios e Exportação", use_container_width=True): 
                registrar_log_acesso(re_logado_str, st.session_state['nome_iq'], "NAVEGACAO", "Relatorios")
                st.session_state['pagina_atual'] = "Relatorios"
                st.rerun()
            
        st.divider()
        if st.button("Sair", use_container_width=True):
            registrar_log_acesso(re_logado_str, st.session_state['nome_iq'], "LOGOUT", "Sistema")
            st.session_state['logado'] = False
            st.rerun()

    # --- PÁGINA: ALTERAR SENHA ---
    if st.session_state['pagina_atual'] == "AlterarSenha":
        st.title("🔑 Alterar Senha de Acesso")
        st.write("Atualize sua senha de login no sistema.")
        
        with st.form("form_nova_senha"):
            senha_atual = st.text_input("Senha Atual", type="password")
            nova_senha_1 = st.text_input("Nova Senha", type="password")
            nova_senha_2 = st.text_input("Confirme a Nova Senha", type="password")
            btn_salvar_senha = st.form_submit_button("Salvar Nova Senha", type="primary")
            
        if btn_salvar_senha:
            iq_reg = dados_iqs[dados_iqs['re_iq'] == re_logado_str]
            if iq_reg.empty or iq_reg.iloc[0]['senha'] != senha_atual.strip():
                st.error("A senha atual está incorreta.")
            elif not nova_senha_1.strip():
                st.error("A nova senha não pode estar vazia.")
            elif nova_senha_1.strip() != nova_senha_2.strip():
                st.error("As senhas novas não coincidem.")
            else:
                sucesso, msg = alterar_senha_sheets(re_logado_str, nova_senha_1)
                if sucesso:
                    st.success("✅ Senha alterada com sucesso!")
                    st.cache_data.clear()
                else:
                    st.error(f"Erro: {msg}")

    # --- PÁGINA 1: DASHBOARD ---
    elif st.session_state['pagina_atual'] == "Dashboard":
        titulo_painel = f"Painel Operacional - {st.session_state['nome_iq']}"
        if perfil_usuario == 'GESTÃO' and 're_alvo_str' in locals() and re_alvo_str:
            nome_iq_filtro = dados_iqs[dados_iqs['re_iq'] == re_alvo_str]['nome_iq'].values
            if nome_iq_filtro: titulo_painel = f"Painel Operacional (Visão: {nome_iq_filtro[0]})"
        
        st.title(titulo_painel)
        st.write("")

        # --- CARREGAR E EXIBIR NOTAS DA MATINAL EM DESTAQUE ---
        df_res_mat = carregar_resultados_matinal()
        nota_geral_val = "Aguardando lançamento"
        nota_iq_val = "Aguardando lançamento"

        if not df_res_mat.empty:
            df_res_mat.columns = [str(c).strip() for c in df_res_mat.columns]
            
            col_ng = next((c for c in df_res_mat.columns if c.upper() == 'NOTA_GERAL'), None)
            if col_ng:
                vals_g = df_res_mat[col_ng].dropna()
                if not vals_g.empty:
                    nota_geral_val = str(vals_g.iloc[-1])
            
            col_re = next((c for c in df_res_mat.columns if c.upper() == 'RE_IQ'), None)
            col_niq = next((c for c in df_res_mat.columns if c.upper() == 'NOTA_IQ'), None)
            
            if col_re and col_niq:
                df_iq_log = df_res_mat[df_res_mat[col_re].astype(str).str.strip().str.replace('.0','') == re_logado_str]
                if not df_iq_log.empty:
                    vals_iq = df_iq_log[col_niq].dropna()
                    if not vals_iq.empty:
                        nota_iq_val = str(vals_iq.iloc[-1])

        st.markdown("### 📊 Resultado da Matinal CLARO")
        c_nota1, c_nota2 = st.columns(2)
        with c_nota1:
            st.markdown('<div class="metric-card-blue">', unsafe_allow_html=True)
            st.markdown('<div class="metric-title">⭐ Nota Geral da Operação</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="metric-value">{nota_geral_val}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="metric-sub">Média consolidada</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        with c_nota2:
            st.markdown('<div class="metric-card-purple">', unsafe_allow_html=True)
            st.markdown(f'<div class="metric-title">⭐ Nota do IQ ({st.session_state["nome_iq"]})</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="metric-value">{nota_iq_val}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="metric-sub">Seu resultado recente</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

        st.divider()

        re_alvo_horas = re_alvo_str if (perfil_usuario == 'GESTÃO' and re_alvo_str) else re_logado_str
        
        meta_alvo, realizado_alvo = meta_atual, realizado_atual
        if perfil_usuario == 'GESTÃO' and re_alvo_str and not df_ctrl.empty:
            f_alvo = df_ctrl[df_ctrl['RE_IQ'].astype(str).str.strip().str.replace('.0','') == str(re_alvo_str)]
            if not f_alvo.empty:
                try: meta_alvo = int(f_alvo.iloc[0]['META_HORAS']) if f_alvo.iloc[0]['META_HORAS'] != '' else 60
                except: pass
                val_real = f_alvo.iloc[0]['REALIZADO_HORAS']
                realizado_alvo = str(val_real) if val_real != '' else "0"

        col1, col2, col3 = st.columns(3)
        
        # CARD 1: % CERTIFICADOS
        with col1:
            st.markdown('<div class="metric-card-blue">', unsafe_allow_html=True)
            st.markdown('<div class="metric-title">🏆 % Certificados</div>', unsafe_allow_html=True)
            
            if meses_info:
                lista_meses = [m['mes_nome'] for m in meses_info]
                mes_selecionado = st.selectbox("Selecione o Mês:", lista_meses, index=len(lista_meses)-1, key="sel_mes_card")
                
                col_re_mes = f"re_iq_responsavel_{mes_selecionado}"
                if perfil_usuario == 'GESTÃO' and (not locals().get('re_alvo_str') or re_alvo_str is None):
                    base_calc_mes = dados_completos
                else:
                    target_re = re_alvo_str if perfil_usuario == 'GESTÃO' else re_logado_str
                    if col_re_mes in dados_completos.columns:
                        base_calc_mes = dados_completos[dados_completos[col_re_mes].astype(str).str.replace('.0', '') == str(target_re)]
                    else:
                        base_calc_mes = pd.DataFrame()
                
                if not base_calc_mes.empty and mes_selecionado in base_calc_mes.columns:
                    filtro_validos = (base_calc_mes[mes_selecionado] != '')
                    base_mes_valida = base_calc_mes[filtro_validos]
                    total_mes = len(base_mes_valida)
                    sim_mes = len(base_mes_valida[base_mes_valida[mes_selecionado].astype(str).str.upper() == 'SIM'])
                    pct_mes = round((sim_mes / total_mes * 100), 1) if total_mes > 0 else 0
                    
                    st.markdown(f'<div class="metric-value">{pct_mes}% SIM</div>', unsafe_allow_html=True)
                    st.markdown(f'<div class="metric-sub">Base: {total_mes} Técnicos ({mes_selecionado})</div>', unsafe_allow_html=True)
                else:
                    st.markdown('<div class="metric-value">0% SIM</div>', unsafe_allow_html=True)
                    st.markdown('<div class="metric-sub">Sem técnicos vinculados</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="metric-value">N/A</div>', unsafe_allow_html=True)
                st.markdown('<div class="metric-sub">Sem abas mensais</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

        # CARD 2: HORAS DE MONITORIA
        with col2:
            st.markdown('<div class="metric-card-green">', unsafe_allow_html=True)
            st.markdown('<div class="metric-title">⏱️ Horas de Monitoria RPPA</div>', unsafe_allow_html=True)
            
            if perfil_usuario == 'GESTÃO':
                meta_input = st.number_input("Meta de Horas:", value=meta_alvo, step=1, key=f"meta_{re_alvo_horas}")
                
                # Se realizado_alvo for string com formato de hora, permitimos atualizar ou editar
                st.markdown(f'<div class="metric-value" style="font-size:24px; margin-top:5px;">Realizado: {realizado_alvo}</div>', unsafe_allow_html=True)
                
                novo_real = st.text_input("Atualizar Realizado (HH:MM:SS):", value=str(realizado_alvo), key=f"real_txt_{re_alvo_horas}")
                if meta_input != meta_alvo or novo_real != str(realizado_alvo):
                    salvar_horas_no_sheets(re_alvo_horas, meta_input, novo_real)
                    st.rerun()
            else:
                st.markdown(f'<div class="metric-value">Meta: {meta_alvo}h</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="metric-value" style="font-size:20px; margin-top:5px;">Realizado: {realizado_alvo}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="metric-sub">Controle individual de horas</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

        # CARD 3: PENDENTES
        with col3:
            st.markdown('<div class="metric-card-orange">', unsafe_allow_html=True)
            st.markdown('<div class="metric-title">⚠️ Monitoramento Pendente</div>', unsafe_allow_html=True)
            
            if mes_acompanhamento:
                pendentes_hoje = len(equipe_vigente[(equipe_vigente[mes_acompanhamento] == 'NÃO') & (equipe_vigente[f'ACOMPANHAMENTO_{mes_acompanhamento}'] != 'SIM')])
                st.markdown(f'<div class="metric-value">{pendentes_hoje} Técnicos</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="metric-sub">Referência: {mes_acompanhamento}</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="metric-value">N/A</div>', unsafe_allow_html=True)
                st.markdown('<div class="metric-sub">Sem base mensal</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

        st.divider()
        
        # --- AGENDA DE MATINAIS ---
        st.subheader("📅 Agenda de Matinais (Clique no nome para realizar a vistoria)")
        agenda_do_usuario = {tec: info for tec, info in st.session_state['agenda_matinal'].items() if str(info.get('re_iq')) == str(re_logado_str) or perfil_usuario == 'GESTÃO'}
        
        if not agenda_do_usuario:
            st.info("Sua agenda está vazia. Vá na aba 'Agendamento de Matinal' para adicionar.")
        else:
            for tec, info in list(agenda_do_usuario.items()):
                c_dash1, c_dash2, c_dash3 = st.columns([3, 2, 1])
                c_dash1.write(f"📌 **Data:** {info['data']} | **IQ:** {info['iq_nome']}")
                
                if c_dash2.button(f"👤 {tec}", key=f"btn_link_{tec}", help="Clique para ir direto à execução"):
                    st.session_state['tec_selecionado_atalho'] = tec
                    st.session_state['pagina_atual'] = "Matinal"
                    st.session_state['aba_matinal_ativa'] = 1
                    st.rerun()
                    
                if perfil_usuario == 'GESTÃO' or str(info.get('re_iq')) == str(re_logado_str):
                    if c_dash3.button("🗑️ Remover", key=f"rm_dash_{tec}"):
                        del st.session_state['agenda_matinal'][tec]
                        salvar_agenda_no_sheets(st.session_state['agenda_matinal'])
                        st.rerun()

        st.divider()
        
        # --- ACOMPANHAMENTO PENDENTE ---
        st.subheader(f"⚠️ Acompanhamento Pendente (Referência: {mes_acompanhamento or 'N/A'})")
        
        if mes_acompanhamento:
            tecnicos_nao_cert = equipe_vigente[(equipe_vigente[mes_acompanhamento] == 'NÃO') & (equipe_vigente[f'ACOMPANHAMENTO_{mes_acompanhamento}'] != 'SIM')]
            
            if tecnicos_nao_cert.empty:
                st.success(f"Todos os técnicos pendentes de {mes_acompanhamento} já concluíram as monitorias.")
            else:
                for index, row in tecnicos_nao_cert.iterrows():
                    tec_login = row['login']
                    tec_nome = row['nome']
                    col_re_mes_acomp = f're_iq_responsavel_{mes_acompanhamento}'
                    iq_resp = row.get(col_re_mes_acomp, '')
                    
                    nome_iq_resp = iq_resp
                    match_iq = dados_iqs[dados_iqs['re_iq'] == str(iq_resp)]
                    if not match_iq.empty: nome_iq_resp = match_iq.iloc[0]['nome_iq']

                    m1_val = str(row.get(f'MONIT_1_{mes_acompanhamento}', '')).upper() == 'SIM'
                    m2_val = str(row.get(f'MONIT_2_{mes_acompanhamento}', '')).upper() == 'SIM'
                    m3_val = str(row.get(f'MONIT_3_{mes_acompanhamento}', '')).upper() == 'SIM'

                    with st.form(key=f"form_monit_{tec_login}"):
                        c_info, c_m1, c_m2, c_m3, c_btn = st.columns([3, 1, 1, 1, 1])
                        c_info.write(f"👤 **{tec_nome}** (IQ: {nome_iq_resp})")
                        
                        f_m1 = c_m1.checkbox("Monit. 1", value=m1_val)
                        f_m2 = c_m2.checkbox("Monit. 2", value=m2_val)
                        f_m3 = c_m3.checkbox("Monit. 3", value=m3_val)
                        
                        btn_salvar_m = c_btn.form_submit_button("Salvar")
                        
                        if btn_salvar_m:
                            val_m1 = 'SIM' if f_m1 else 'NÃO'
                            val_m2 = 'SIM' if f_m2 else 'NÃO'
                            val_m3 = 'SIM' if f_m3 else 'NÃO'
                            
                            atualizar_celula_especifica(aba_acompanhamento, tec_login, 'MONIT_1', val_m1)
                            atualizar_celula_especifica(aba_acompanhamento, tec_login, 'MONIT_2', val_m2)
                            atualizar_celula_especifica(aba_acompanhamento, tec_login, 'MONIT_3', val_m3)
                            
                            if f_m1 and f_m2 and f_m3:
                                atualizar_celula_especifica(aba_acompanhamento, tec_login, 'ACOMPANHAMENTO', 'SIM')
                            
                            st.success(f"Monitorias de {tec_nome} salvas com sucesso!")
                            st.rerun()
                    st.divider()
        else:
            st.info("Crie abas de certificados mensais para habilitar o acompanhamento.")

    # --- PÁGINA 2: HISTÓRICO DE CERTIFICADOS ---
    elif st.session_state['pagina_atual'] == "Historico":
        st.title(f"🏆 Histórico de Certificados")
        
        if not meses_info:
            st.warning("Nenhuma aba de certificação encontrada no Google Sheets.")
        else:
            lista_meses = [m['mes_nome'] for m in meses_info]
            mes_historico = st.selectbox("📅 Escolha o Mês para visualizar:", lista_meses, index=len(lista_meses)-1)
            
            col_re_hist = f"re_iq_responsavel_{mes_historico}"
            if perfil_usuario == 'GESTÃO':
                if 're_alvo_str' in locals() and re_alvo_str:
                    base_historico = dados_completos[dados_completos[col_re_hist].astype(str) == str(re_alvo_str)]
                else:
                    base_historico = dados_completos
            else:
                if col_re_hist in dados_completos.columns:
                    base_historico = dados_completos[dados_completos[col_re_hist].astype(str).str.replace('.0', '') == str(re_logado_str)]
                else:
                    base_historico = pd.DataFrame()

            if base_historico.empty:
                st.info(f"Nenhum técnico encontrado para o filtro selecionado no mês de {mes_historico}.")
            else:
                filtro_validos = (base_historico[mes_historico] != '')
                base_mes_valida = base_historico[filtro_validos]
                total_mes = len(base_mes_valida)
                sim_mes = len(base_mes_valida[base_mes_valida[mes_historico].astype(str).str.upper() == 'SIM'])
                pct_mes = round((sim_mes / total_mes * 100), 1) if total_mes > 0 else 0

                st.metric(f"🏆 % Certificados ({mes_historico})", f"{pct_mes}% SIM", f"Base: {total_mes} Técnicos")
                st.write("")

                colunas_exibir = ['login', 'nome', mes_historico]
                if col_re_hist in base_historico.columns: colunas_exibir.append(col_re_hist)
                if f"MONIT_1_{mes_historico}" in base_historico.columns: colunas_exibir.append(f"MONIT_1_{mes_historico}")
                if f"MONIT_2_{mes_historico}" in base_historico.columns: colunas_exibir.append(f"MONIT_2_{mes_historico}")
                if f"MONIT_3_{mes_historico}" in base_historico.columns: colunas_exibir.append(f"MONIT_3_{mes_historico}")

                df_exibir = base_historico[[c for c in colunas_exibir if c in base_historico.columns]].copy()
                
                if all(col in df_exibir.columns for col in [f"MONIT_1_{mes_historico}", f"MONIT_2_{mes_historico}", f"MONIT_3_{mes_historico}"]):
                    m1 = df_exibir[f"MONIT_1_{mes_historico}"].astype(str).str.upper() == 'SIM'
                    m2 = df_exibir[f"MONIT_2_{mes_historico}"].astype(str).str.upper() == 'SIM'
                    m3 = df_exibir[f"MONIT_3_{mes_historico}"].astype(str).str.upper() == 'SIM'
                    soma = m1.astype(int) + m2.astype(int) + m3.astype(int)
                    df_exibir['Contagem_Monitorias'] = soma.astype(str) + "/3 - " + soma.apply(lambda x: "SIM" if x == 3 else "NÃO")

                df_exibir['ordem_sort'] = df_exibir[mes_historico].astype(str).str.upper().apply(lambda x: 0 if x == 'NÃO' else 1)
                df_exibir = df_exibir.sort_values(by='ordem_sort').drop(columns=['ordem_sort'])

                drop_cols = [c for c in df_exibir.columns if 'MONIT_' in c]
                df_exibir = df_exibir.drop(columns=drop_cols, errors='ignore')

                renomear_cols = {
                    'login': 'Login', 
                    'nome': 'Nome do Técnico',
                    mes_historico: 'Status Certificação',
                    col_re_hist: 'RE do IQ (Mês)',
                    'Contagem_Monitorias': 'Monitoria Concluída?'
                }
                df_exibir = df_exibir.rename(columns=renomear_cols)

                st.dataframe(df_exibir.style.map(colorir_sim_nao), hide_index=True, use_container_width=True)

    # --- PÁGINA 3: MATINAL ---
    elif st.session_state['pagina_atual'] == "Matinal":
        st.title("📋 Agendamento e Execução da Matinal")
        
        tab_agendar, tab_executar = st.tabs(["1. Agendar Téc", "2. Executar Vistoria (Checklist)"])
        
        with tab_agendar:
            if st.session_state.get('zap_agenda_pronto'):
                st.success("✅ Matinal agendada com sucesso!")
                
                c_btn_zap, c_btn_gcal = st.columns(2)
                with c_btn_zap:
                    st.markdown(f'<a href="{st.session_state["zap_agenda_pronto"]}" target="_blank" style="display: block; text-align: center; padding: 0.8em; color: white; background-color: #25D366; border-radius: 8px; text-decoration: none; font-weight: bold; font-size: 15px;">💬 AVISAR NO WHATSAPP</a>', unsafe_allow_html=True)
                with c_btn_gcal:
                    if st.session_state.get('gcal_link'):
                        st.markdown(f'<a href="{st.session_state["gcal_link"]}" target="_blank" style="display: block; text-align: center; padding: 0.8em; color: white; background-color: #4285F4; border-radius: 8px; text-decoration: none; font-weight: bold; font-size: 15px;">📅 ADICIONAR AO GOOGLE AGENDA</a>', unsafe_allow_html=True)
                
                st.write("")
                if st.button("🧹 Concluir e Agendar Outro"):
                    st.session_state['zap_agenda_pronto'] = None
                    st.session_state['gcal_link'] = None
                    st.rerun()
            else:
                tipo_selecao_tec = st.radio("Selecione a base de técnicos para agendamento:", ["Minha Equipe", "Geral (Todos os Técnicos)"], horizontal=True)
                lista_tecs_disponiveis = equipe_vigente['nome'].tolist() if tipo_selecao_tec == "Minha Equipe" else dados_completos['nome'].tolist()

                col_a1, col_a2 = st.columns(2)
                with col_a1:
                    tec_agendar = st.selectbox("Selecione o Técnico:", ["Selecione..."] + lista_tecs_disponiveis)
                with col_a2:
                    data_agendada = st.date_input("Escolha o Dia:", value=None, format="DD/MM/YYYY")
                    
                if st.button("Adicionar à Agenda", type="primary"):
                    if tec_agendar != "Selecione..." and data_agendada is not None:
                        st.session_state['agenda_matinal'][tec_agendar] = {
                            'data': data_agendada.strftime("%d/%m/%Y"),
                            'iq_nome': st.session_state['nome_iq'],
                            're_iq': re_logado_str
                        }
                        salvar_agenda_no_sheets(st.session_state['agenda_matinal'])
                        
                        tec_row_info = dados_completos[dados_completos['nome'] == tec_agendar]
                        tel_tec = "5511994524040"
                        if not tec_row_info.empty and 'telefone_tec' in tec_row_info.columns and str(tec_row_info.iloc[0]['telefone_tec']).strip():
                            tel_tec = str(tec_row_info.iloc[0]['telefone_tec']).strip()
                        
                        msg_zap_tec = f"Olá *{tec_agendar}*,\n\nSua *Vistoria Matinal (IVM)* foi agendada pelo IQ *{st.session_state['nome_iq']}* para a data: *{data_agendada.strftime('%d/%m/%Y')}* às *07:00* (Local: Base TOTALE ABC).\n\nPor favor, *chegue cedo*, mantenha seus EPIs, ferramentas e veículos organizados para a verificação."
                        url_zap_tec = f"https://api.whatsapp.com/send?phone={tel_tec}&text={urllib.parse.quote(msg_zap_tec)}"
                        
                        gcal_start = data_agendada.strftime('%Y%m%d') + 'T070000'
                        gcal_end = data_agendada.strftime('%Y%m%d') + 'T080000'
                        gcal_title = urllib.parse.quote(f"Vistoria Matinal (IVM) - {tec_agendar}")
                        gcal_location = urllib.parse.quote("Base TOTALE ABC")
                        gcal_details = urllib.parse.quote(f"Vistoria matinal agendada pelo IQ {st.session_state['nome_iq']} com o técnico {tec_agendar}.")
                        gcal_url = f"https://calendar.google.com/calendar/render?action=TEMPLATE&text={gcal_title}&dates={gcal_start}/{gcal_end}&location={gcal_location}&details={gcal_details}"

                        st.session_state['zap_agenda_pronto'] = url_zap_tec
                        st.session_state['gcal_link'] = gcal_url
                        st.rerun()
            
            st.write("---")
            st.write("**Agenda de Matinais:**")
            agenda_do_usuario = {tec: info for tec, info in st.session_state['agenda_matinal'].items() if str(info.get('re_iq')) == str(re_logado_str) or perfil_usuario == 'GESTÃO'}
            
            if not agenda_do_usuario:
                st.info("Nenhuma matinal agendada.")
            else:
                for tec, info in list(agenda_do_usuario.items()):
                    c1, c2 = st.columns([4, 1])
                    c1.write(f"📌 **Data:** {info['data']} | **Técnico:** {tec} | **IQ:** {info['iq_nome']} (RE: {info['re_iq']})")
                    if c2.button("🗑️ Remover", key=f"rm_mat_{tec}"):
                        del st.session_state['agenda_matinal'][tec]
                        salvar_agenda_no_sheets(st.session_state['agenda_matinal'])
                        st.rerun()

        with tab_executar:
            agenda_do_usuario = {tec: info for tec, info in st.session_state['agenda_matinal'].items() if str(info.get('re_iq')) == str(re_logado_str) or perfil_usuario == 'GESTÃO'}
            
            if st.session_state['email_pronto']:
                st.success("✅ Vistoria gravada no Google Sheets e evidência armazenada no Cloudinary!")
                st.markdown(f'<a href="{st.session_state["email_pronto"]}" target="_blank" style="display: inline-block; padding: 0.8em 1.5em; color: white; background-color: #007BFF; border-radius: 8px; text-decoration: none; font-weight: bold; font-size: 16px;">📩 ABRIR E-MAIL COM O RELATÓRIO</a>', unsafe_allow_html=True)
                st.write("")
                if st.button("🧹 Limpar Tela e Voltar para Agenda"):
                    st.session_state['email_pronto'] = None
                    st.session_state['tec_selecionado_atalho'] = None
                    st.rerun()
            else:
                if not agenda_do_usuario:
                    st.warning("Não há nenhum técnico agendado na sua agenda.")
                else:
                    datas_disponiveis = sorted(list(set([info['data'] for info in agenda_do_usuario.values()])))
                    
                    col_d1, col_d2 = st.columns(2)
                    with col_d1:
                        data_selecionada_exec = st.selectbox("📅 Selecione a Data da Matinal:", datas_disponiveis)
                    
                    tecs_na_data = [tec for tec, info in agenda_do_usuario.items() if info['data'] == data_selecionada_exec]
                    
                    indice_default = 0
                    if st.session_state.get('tec_selecionado_atalho') in tecs_na_data:
                        indice_default = tecs_na_data.index(st.session_state['tec_selecionado_atalho']) + 1
                    
                    with col_d2:
                        tec_atual = st.selectbox("Selecione o Técnico Agendado:", ["Selecione..."] + tecs_na_data, index=indice_default)
                    
                    if tec_atual != "Selecione...":
                        st.info(f"⚠️ Assinale abaixo os itens que estão **FALTANDO** ou **IRREGULARES** para **{tec_atual}** ({data_selecionada_exec}).")
                        
                        # CAMPOS OBRIGATÓRIOS (PLACA, LOTES, VALIDADES E TAMANHOS)
                        st.markdown("### 🏷️ Informações de Veículo, Lotes, Validades e Tamanhos (Preenchimento Obrigatório)")
                        col_p1, col_l1, col_l2 = st.columns(3)
                        with col_p1:
                            placa_veiculo = st.text_input("Placa do Veículo *")
                            lote_capacete = st.text_input("Lote Capacete *")
                        with col_l1:
                            venc_carneira = st.text_input("Vencimento Carneira *")
                            lote_cinto = st.text_input("Lote Cinto *")
                        with col_l2:
                            lote_talabarte = st.text_input("Lote Talabarte *")
                            lote_luva_pig = st.text_input("Lote Luva Pigmentada *")

                        st.write("")
                        col_l3, col_l4, col_t1, col_t2 = st.columns(4)
                        with col_l3:
                            lote_luva_vaq = st.text_input("Lote Luva Vaqueta *")
                        with col_l4:
                            venc_protetor = st.text_input("Vencimento Protetor Solar *")
                        with col_t1:
                            tam_camisa = st.text_input("Tamanho Uniforme | CAMISA *")
                        with col_t2:
                            tam_calca = st.text_input("Tamanho Uniforme | CALÇA *")

                        st.write("")
                        col_t3, _, _ = st.columns(3)
                        with col_t3:
                            tam_jaqueta = st.text_input("Tamanho Uniforme | JAQUETA *")

                        st.divider()
                        faltas = []
                        
                        t_ferr, t_gpon, t_epi, t_asseio, t_sis, t_veic = st.tabs([
                            "🛠️ Ferramental", "📡 GPON/Outros", "👷 EPI / EPC", "🧹 Asseio", "📱 Sistemas", "🚗 Veículo"
                        ])
                        
                        def renderizar_itens_matinal(lista_itens, aba):
                            with aba:
                                cols = st.columns(2)
                                for i, item in enumerate(lista_itens):
                                    col_atual = cols[i % 2]
                                    if col_atual.checkbox(item, key=f"mat_{item}_{i}"):
                                        faltas.append(item)

                        renderizar_itens_matinal(ITENS_MATINAL["🛠️ Ferramental"], t_ferr)
                        renderizar_itens_matinal(ITENS_MATINAL["📡 GPON/Outros"], t_gpon)
                        
                        with t_epi:
                            cols_epi = st.columns(2)
                            itens_epi_base = ITENS_MATINAL["👷 EPI / EPC"]
                            for i, item in enumerate(itens_epi_base):
                                if cols_epi[i % 2].checkbox(item, key=f"mat_epi_{i}"):
                                    faltas.append(item)
                            
                            st.divider()
                            st.write("**Confirmação de Posse dos Itens Obrigatórios:**")
                            if not cols_epi[0].checkbox("Possui Capacete e Carneira?", key="posse_cap"): faltas.append("Capacete/Carneira não ticado como presente")
                            if not cols_epi[1].checkbox("Possui Cinto de Segurança?", key="posse_cin"): faltas.append("Cinto não ticado como presente")
                            if not cols_epi[0].checkbox("Possui Talabarte?", key="posse_tal"): faltas.append("Talabarte não ticado como presente")
                            if not cols_epi[1].checkbox("Possui Luva Pigmentada?", key="posse_lvp"): faltas.append("Luva Pigmentada não ticado como presente")
                            if not cols_epi[0].checkbox("Possui Luva Vaqueta?", key="posse_lvv"): faltas.append("Luva Vaqueta não ticado como presente")
                            if not cols_epi[1].checkbox("Possui Protetor Solar?", key="posse_pro"): faltas.append("Protetor Solar não ticado como presente")

                        renderizar_itens_matinal(ITENS_MATINAL["🧹 Asseio"], t_asseio)
                        
                        with t_sis:
                            cols_sis = st.columns(2)
                            itens_sis_base = ITENS_MATINAL["📱 Sistemas"]
                            for i, item in enumerate(itens_sis_base):
                                if cols_sis[i % 2].checkbox(item, key=f"mat_sis_{i}"):
                                    faltas.append(item)
                                    
                            st.divider()
                            st.write("**Confirmação de Uniformes:**")
                            if not cols_sis[0].checkbox("Possui Uniforme - Camisa?", key="posse_cam"): faltas.append("Uniforme Camisa não ticado")
                            if not cols_sis[1].checkbox("Possui Uniforme - Calça?", key="posse_calc"): faltas.append("Uniforme Calça não ticado")
                            if not cols_sis[0].checkbox("Possui Uniforme - Jaqueta?", key="posse_jaq"): faltas.append("Uniforme Jaqueta não ticado")

                        renderizar_itens_matinal(ITENS_MATINAL["🚗 Veículo"], t_veic)

                        st.divider()
                        fotos_upload = st.file_uploader("📸 Anexar Fotos da Vistoria (Múltiplas fotos permitidas)", type=['png', 'jpg'], accept_multiple_files=True)
                        obs_final = st.text_area("Observações da Tratativa:")

                        resumo_faltas = " / ".join(faltas) if faltas else "Todas as ferramentas e condições em conformidade."
                        
                        if st.button("Gravar Vistoria e Gerar E-mail", type="primary"):
                            if not fotos_upload:
                                st.warning("⚠️ O envio de ao menos uma foto é obrigatório para comprovação.")
                            elif not (placa_veiculo.strip() and lote_capacete.strip() and venc_carneira.strip() and lote_cinto.strip() and lote_talabarte.strip() and lote_luva_pig.strip() and lote_luva_vaq.strip() and venc_protetor.strip() and tam_camisa.strip() and tam_calca.strip() and tam_jaqueta.strip()):
                                st.warning("⚠️ Todos os campos de Placa do Veículo, Lotes, Validades e Tamanhos de Uniformes são obrigatórios.")
                            else:
                                tec_row = equipe_vigente[equipe_vigente['nome'] == tec_atual]
                                tec_login = tec_row['login'].iloc[0] if not tec_row.empty else "N/A"
                                tec_re = tec_row['re'].iloc[0] if ('re' in tec_row.columns and not tec_row.empty) else tec_login
                                
                                links_fotos = salvar_fotos_no_cloudinary(fotos_upload, tec_atual, "Evidencias_Matinal")
                                
                                extra_info = {
                                    'placa_veiculo': placa_veiculo,
                                    'lote_capacete': lote_capacete,
                                    'venc_carneira': venc_carneira,
                                    'lote_cinto': lote_cinto,
                                    'lote_talabarte': lote_talabarte,
                                    'lote_luva_pig': lote_luva_pig,
                                    'lote_luva_vaq': lote_luva_vaq,
                                    'venc_protetor': venc_protetor,
                                    'tam_camisa': tam_camisa,
                                    'tam_calca': tam_calca,
                                    'tam_jaqueta': tam_jaqueta
                                }

                                vistoria_id = registrar_vistoria_completa(
                                    re_iq=re_logado_str,
                                    nome_iq=st.session_state['nome_iq'],
                                    login_tec=tec_login,
                                    nome_tec=tec_atual,
                                    tipo="Matinal",
                                    irregulares=resumo_faltas,
                                    extra_info=extra_info,
                                    obs=obs_final,
                                    links_fotos=links_fotos
                                )
                                
                                if aba_acompanhamento:
                                    atualizar_celula_especifica(aba_acompanhamento, tec_login, 'ACOMPANHAMENTO', 'SIM')
                                    
                                del st.session_state['agenda_matinal'][tec_atual]
                                salvar_agenda_no_sheets(st.session_state['agenda_matinal'])
                                
                                fotos_txt = "\n".join(links_fn for links_fn in links_fotos) if 'links_fotos' in locals() else ""
                                corpo_email = f"RELATÓRIO DE MATINAL (IVM 2026)\nID da Vistoria: {vistoria_id}\nRE: {tec_re}\nTécnico: {tec_atual}\nIQ: {st.session_state['nome_iq']}\n\nVEÍCULOS, LOTES, VALIDADES E TAMANHOS:\n- Placa do Veículo: {placa_veiculo}\n- Lote Capacete: {lote_capacete}\n- Vencimento Carneira: {venc_carneira}\n- Lote Cinto: {lote_cinto}\n- Lote Talabarte: {lote_talabarte}\n- Lote Luva Pigmentada: {lote_luva_pig}\n- Lote Luva Vaqueta: {lote_luva_vaq}\n- Venc. Protetor Solar: {venc_protetor}\n- Tamanho Camisa: {tam_camisa}\n- Tamanho Calça: {tam_calca}\n- Tamanho Jaqueta: {tam_jaqueta}\n\nITENS FALTANTES/IRREGULARES:\n- {resumo_faltas}\n\nOBSERVAÇÕES:\n{obs_final}\n\nEVIDÊNCIAS FOTOS:\n{fotos_txt}"
                                url_email = f"mailto:{DESTINATARIOS_MATINAL}?subject=Relatorio Matinal [ID {vistoria_id}] - RE {tec_re} - {tec_atual}&body={urllib.parse.quote(corpo_email)}"
                                
                                st.session_state['email_pronto'] = url_email
                                st.session_state['tec_selecionado_atalho'] = None
                                st.rerun()

    # --- PÁGINA 5: RELATÓRIOS E EXPORTAÇÃO (EXCLUSIVO PARA GESTÃO) ---
    elif st.session_state['pagina_atual'] == "Relatorios":
        if perfil_usuario != 'GESTÃO':
            st.warning("Acesso restrito a gestores.")
        else:
            st.title("📥 Relatórios e Exportação de Dados")
            st.write("Baixe os relatórios completos de Vistorias Matinais e Auditorias de Instalação em formato Excel (.xlsx).")
            
            planilha_con = conectar_planilha()
            
            tab_exp1, tab_exp2 = st.tabs(["📊 Vistorias Matinais", "🛠️ Vistorias de Instalação"])
            
            with tab_exp1:
                st.subheader("Relatório de Vistorias Matinais")
                try:
                    ws_mat = planilha_con.worksheet("Vistorias_Matinal")
                    df_mat = pd.DataFrame(ws_mat.get_all_records())
                except:
                    df_mat = pd.DataFrame()
                    
                if df_mat.empty:
                    st.info("Nenhum registro encontrado na aba Vistorias_Matinal.")
                else:
                    st.dataframe(df_mat, hide_index=True, use_container_width=True)
                    excel_mat = exportar_para_excel(df_mat, "vistorias_matinais.xlsx")
                    st.download_button(
                        label="📥 Baixar Excel (Matinais)",
                        data=excel_mat,
                        file_name=f"Vistorias_Matinal_{datetime.now(fuso_brasil).strftime('%Y-%m-%d')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        type="primary"
                    )
                    
            with tab_exp2:
                st.subheader("Relatório de Auditorias de Instalação")
                try:
                    ws_inst = planilha_con.worksheet("Vistoria_Instalacao")
                    df_inst = pd.DataFrame(ws_inst.get_all_records())
                except:
                    df_inst = pd.DataFrame()
                    
                if df_inst.empty:
                    st.info("Nenhum registro encontrado na aba Vistoria_Instalacao.")
                else:
                    st.dataframe(df_inst, hide_index=True, use_container_width=True)
                    excel_inst = exportar_para_excel(df_inst, "vistorias_instalacao.xlsx")
                    st.download_button(
                        label="📥 Baixar Excel (Instalação)",
                        data=excel_inst,
                        file_name=f"Vistorias_Instalacao_{datetime.now(fuso_brasil).strftime('%Y-%m-%d')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        type="primary"
                    )
