import streamlit as st
import json
import math
import os
import time
import google.generativeai as genai

# ==========================================
# CONFIGURAÇÃO DA PÁGINA E CSS PREMIUM (SaaS)
# ==========================================
st.set_page_config(page_title="SafeDose Pro", page_icon="⚡", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stApp { background-color: #f4f7f6; }

    [data-testid="stSidebar"] { background-color: #1e293b !important; border-right: 1px solid #334155 !important; }
    [data-testid="stSidebar"] * { color: #f8f9fa !important; }

    [data-testid="stSidebar"] .stButton>button {
        background-color: rgba(255, 255, 255, 0.05) !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
        color: #ffffff !important; box-shadow: none !important;
    }
    [data-testid="stSidebar"] .stButton>button p { color: #ffffff !important; }
    [data-testid="stSidebar"] .stButton>button:hover { background-color: rgba(255, 255, 255, 0.15) !important; border-color: #4CAF50 !important; }

    [data-testid="stSidebar"] div[data-baseweb="select"] > div,
    [data-testid="stSidebar"] div[data-baseweb="input"] {
        background-color: rgba(0, 0, 0, 0.2) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important; color: white !important;
    }
    [data-testid="stSidebar"] input { color: #ffffff !important; background-color: transparent !important; -webkit-text-fill-color: #ffffff !important; }

    [data-testid="stSidebar"] div[data-testid="stNumberInputContainer"] {
        background-color: rgba(0, 0, 0, 0.2) !important; border: 1px solid rgba(255, 255, 255, 0.1) !important; border-radius: 8px;
    }
    [data-testid="stSidebar"] div[data-testid="stNumberInputContainer"] * { background-color: transparent !important; }
    [data-testid="stSidebar"] div[data-testid="stNumberInputStepUp"],
    [data-testid="stSidebar"] div[data-testid="stNumberInputStepDown"] { border-left: 1px solid rgba(255, 255, 255, 0.1) !important; }
    [data-testid="stSidebar"] svg { fill: #ffffff !important; color: #ffffff !important; }

    [data-testid="stAppViewBlockContainer"] .stButton>button {
        background-color: #ffffff; border: 1px solid #e0e6ed; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); transition: all 0.2s ease-in-out;
    }
    [data-testid="stAppViewBlockContainer"] .stButton>button p { color: #3c4858 !important; font-weight: 600; }
    [data-testid="stAppViewBlockContainer"] .stButton>button:hover { transform: translateY(-2px); box-shadow: 0 5px 15px rgba(0,0,0,0.1); border-color: #0056b3; }

    button[kind="primary"] { background: linear-gradient(135deg, #0056b3, #003d82) !important; border: none !important; box-shadow: 0 4px 10px rgba(0, 86, 179, 0.3) !important; }
    button[kind="primary"] p { color: #ffffff !important; }
    button[kind="primary"]:hover { background: linear-gradient(135deg, #003d82, #002752) !important; }

    button[data-baseweb="tab"] { background-color: transparent !important; border: none !important; border-bottom: 3px solid transparent !important; padding-top: 15px !important; padding-bottom: 15px !important; font-weight: 600 !important; color: #8392a5 !important; font-size: 1.1rem !important; }
    button[data-baseweb="tab"][aria-selected="true"] { border-bottom: 3px solid #0056b3 !important; color: #0056b3 !important; }

    .stAlert { border-radius: 12px !important; border: none !important; box-shadow: 0 2px 8px rgba(0,0,0,0.04) !important; }
    div[data-testid="stMetricValue"] { font-size: 2.2rem; font-weight: 800; color: #0056b3; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# LEITURA DOS BANCOS DE DADOS E CACHE
# ==========================================
try:
    with open("Usuarios.json", "r", encoding="utf-8") as file: banco_usuarios = json.load(file)
except:
    banco_usuarios = {"admin": {"nome": "Administrador de TI", "senha": "admin", "cargo": "ADM"}}
    with open("Usuarios.json", "w", encoding="utf-8") as f: json.dump(banco_usuarios, f, indent=2, ensure_ascii=False)

try:
    with open("Database.json", "r", encoding="utf-8") as file: banco_medicamentos = json.load(file)
except: banco_medicamentos = {}

try:
    with open("Pacientes.json", "r", encoding="utf-8") as file: banco_pacientes = json.load(file)
except: banco_pacientes = {}

if 'cache_pareceres' not in st.session_state: st.session_state['cache_pareceres'] = {}
if 'cache_holistico' not in st.session_state: st.session_state['cache_holistico'] = {}

# ==========================================
# SISTEMA DE LOGIN
# ==========================================
if 'usuario_logado' not in st.session_state:
    st.session_state['usuario_logado'] = None
    st.session_state['cargo_usuario'] = None

if st.session_state['usuario_logado'] is None:
    c1, col_login, c2 = st.columns([1, 1.5, 1])
    with col_login:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        with st.container(border=True):
            st.title("🔐 Acesso Restrito")
            st.caption("SafeDose Pro - Sistema de Decisão Clínica")
            with st.form("form_login"):
                usuario = st.text_input("ID de Acesso:")
                senha = st.text_input("Senha:", type="password")
                if st.form_submit_button("Entrar no Sistema", use_container_width=True):
                    if usuario in banco_usuarios and banco_usuarios[usuario]["senha"] == senha:
                        st.session_state['usuario_logado'] = banco_usuarios[usuario]["nome"]
                        st.session_state['cargo_usuario'] = banco_usuarios[usuario]["cargo"]
                        st.rerun()
                    else: st.error("❌ Credenciais inválidas.")
    st.stop()

# ==========================================
# MOTOR DA IA
# ==========================================
CHAVE_API = os.environ.get("GEMINI_API_KEY")

@st.cache_data(show_spinner=False)
def descobrir_modelo(chave):
    if not chave: return None
    genai.configure(api_key=chave)
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods: return m.name.replace('models/', '')
    except: pass
    return "gemini-1.5-pro"

modelo_valido = descobrir_modelo(CHAVE_API)
model = genai.GenerativeModel(modelo_valido) if modelo_valido else None

# ==========================================
# BARRA LATERAL & ALGORITMO DE SCORE DE RISCO
# ==========================================
with st.sidebar:
    st.title("SafeDose Pro ⚡")
    cargo = st.session_state['cargo_usuario']
    icone_cargo = "👨‍💻" if cargo == "ADM" else "👨‍⚕️" if cargo == "Médico" else "🩺"
    st.success(f"{icone_cargo} **Plantão:** \n\n {st.session_state['usuario_logado']}\n\n*Perfil: {cargo}*")
    
    if st.button("🚪 Encerrar Sessão", use_container_width=True):
        st.session_state['usuario_logado'] = None
        st.session_state['cargo_usuario'] = None
        st.rerun()
        
    st.markdown("---")
    st.markdown("### 🏥 Triagem do Paciente")
    lista_pacientes = [info["nome"] for info in banco_pacientes.values()]
    pac_sel = st.selectbox("Buscar Prontuário:", ["(Avulso / Emergência)"] + lista_pacientes)
    
    idade_paciente_atual = 0
    score_risco = 0 # Algoritmo de Score
    
    if pac_sel != "(Avulso / Emergência)":
        dados_pac = next(v for v in banco_pacientes.values() if v["nome"] == pac_sel)
        peso_paciente = float(dados_pac["peso"])
        idade_paciente_atual = int(dados_pac.get('idade', 0))
        medicamentos_em_uso = dados_pac.get("uso_continuo", [])
        
        st.markdown(f"**👤 {dados_pac['nome']}**")
        col_m1, col_m2 = st.columns(2)
        col_m1.metric("Peso", f"{peso_paciente}kg")
        col_m2.metric("Idade", f"{idade_paciente_atual}a")
        if medicamentos_em_uso: st.warning(f"💊 **Em uso:**\n {', '.join(medicamentos_em_uso)}")
    else:
        peso_paciente = st.number_input("Peso Atual (kg):", 1.0, 250.0, 70.0, 0.5)
        idade_paciente_atual = st.number_input("Idade (anos):", 0, 120, 30)
        lista_remedios = [v["nome_apresentacao"] for v in banco_medicamentos.values()]
        medicamentos_em_uso = st.multiselect("O que o paciente já toma?", lista_remedios)

    # Lógica do Score de Risco
    if idade_paciente_atual >= 60: score_risco += 1
    if len(medicamentos_em_uso) >= 5: score_risco += 2

    if len(medicamentos_em_uso) >= 5:
        st.error("⚠️ **POLIFARMÁCIA DETECTADA**")

    st.markdown("---")
    if st.button("🔄 Atualizar Sistema", use_container_width=True): st.rerun()
    st.caption("🚀 Versão 15.0 | Clinical Intelligence")

# ==========================================
# GESTÃO DE ABAS 
# ==========================================
is_admin = (cargo == "ADM")
if is_admin: abas = st.tabs(["🚨 Código Azul", "📋 Prescrição", "👥 Pacientes", "⚙️ Sistema", "🛡️ Gestão de Equipe"])
else: abas = st.tabs(["🚨 Código Azul", "📋 Prescrição", "👥 Pacientes", "⚙️ Sistema"])
aba_emergencia, aba_rotina, aba_pacientes, aba_admin = abas[0], abas[1], abas[2], abas[3]
if is_admin: aba_equipe = abas[4]

# ==========================================
# ABA 1: EMERGÊNCIA
# ==========================================
with aba_emergencia:
    st.markdown("""<style>button[kind="primary"] { height: 100px; border-radius: 12px !important; font-weight: bold !important; font-size: 1.2rem !important; }</style>""", unsafe_allow_html=True)
    if peso_paciente >= 40.0:
        st.error(f"🚨 **PROTOCOLO ADULTO** | Peso base: **{peso_paciente} kg**")
        c1, c2 = st.columns(2)
        if c1.button("🚨 ADRENALINA", use_container_width=True, type="primary"): st.success("✅ 1 mg (1 ampola) | Flush 20ml SF")
        if c2.button("🫀 AMIODARONA", use_container_width=True, type="primary"): st.success("✅ 300 mg (2 ampolas) | SG 5%")
    else:
        st.warning(f"🧸 **PROTOCOLO PEDIÁTRICO** | Peso base: **{peso_paciente} kg**")
        c1, c2 = st.columns(2)
        if c1.button("🚨 ADRENALINA Ped.", use_container_width=True, type="primary"): st.success(f"✅ {round(peso_paciente*0.01, 2)} mg")
        if c2.button("🫀 AMIODARONA Ped.", use_container_width=True, type="primary"): st.success(f"✅ {round(peso_paciente*5.0, 2)} mg")

# ==========================================
# ABA 2: PRESCRIÇÃO HOLÍSTICA E VALIDAÇÃO DE DOSE
# ==========================================
with aba_rotina:
    if banco_medicamentos:
        col_esq, col_dir = st.columns([1.2, 1])
        with col_esq:
            # Mostra o Nível de Risco Global
            if score_risco >= 3: st.error("📈 **Nível de Risco do Paciente: ALTO**")
            elif score_risco >= 1: st.warning("📊 **Nível de Risco do Paciente: MODERADO**")
            else: st.success("📉 **Nível de Risco do Paciente: BAIXO**")

            lista_remedios = [v["nome_apresentacao"] for v in banco_medicamentos.values()]
            sel = st.selectbox("Prescrever nova medicação:", ["(Selecione...)"] + lista_remedios)
            
            if idade_paciente_atual >= 60:
                st.info("🧓 **Atenção Geriátrica:** Considere ajuste de dose devido à redução do clearance renal/hepático.")
                
            if sel != "(Selecione...)":
                dados = next(v for v in banco_medicamentos.values() if v["nome_apresentacao"] == sel)
                with st.container(border=True):
                    st.markdown(f"### 💊 {dados['nome_apresentacao']}")
                    vias_bruto = dados.get("vias_permitidas", ["intravenosa"])
                    vias = vias_bruto if isinstance(vias_bruto, list) else [str(vias_bruto)]
                    st.caption(f"🛣️ Vias: {', '.join(vias).title()}")
                    
                    grave = [r for r in medicamentos_em_uso if any(x in r.lower() for x in [i.lower() for i in dados.get("interacoes_graves", [])])]
                    moderado = [r for r in medicamentos_em_uso if any(x in r.lower() for x in [i.lower() for i in dados.get("interacoes_moderadas", [])])]
                    
                    if grave: 
                        st.error(f"🛑 **GRAVE:** Risco severo de interação com {', '.join(grave)}")
                        score_risco += 3
                    elif moderado: 
                        st.warning(f"⚠️ **MODERADO:** Possível conflito com {', '.join(moderado)}")
                        score_risco += 1
                    else: st.success("✅ Perfil individual seguro.")
                    
                    if grave or moderado:
                        conflitos = grave + moderado
                        chave_risco = f"{dados['nome_apresentacao']}_{'_'.join(conflitos)}"
                        if chave_risco not in st.session_state['cache_pareceres']:
                            if model:
                                with st.spinner("🤖 Gerando parecer farmacológico..."):
                                    prompt_risco = f"Atue como farmacologista clínico. Explique em 1 parágrafo curto o risco da interação entre '{dados['nome_apresentacao']}' e: '{', '.join(conflitos)}'."
                                    try: st.session_state['cache_pareceres'][chave_risco] = model.generate_content(prompt_risco).text
                                    except: st.session_state['cache_pareceres'][chave_risco] = "Erro ao gerar explicação."
                            else: st.session_state['cache_pareceres'][chave_risco] = "Serviço de IA Offline."
                        st.info(f"**🤖 Parecer IA (1 para 1):**\n\n{st.session_state['cache_pareceres'][chave_risco]}")

                    st.divider()

                    # NOVA FEATURE: Revisão Holística da Prescrição
                    if medicamentos_em_uso:
                        chave_holistica = f"holistico_{dados['nome_apresentacao']}_{'_'.join(medicamentos_em_uso)}"
                        if st.button("🧠 Revisão Holística da Prescrição (IA)", use_container_width=True):
                            if chave_holistica not in st.session_state['cache_holistico']:
                                if model:
                                    with st.spinner("Analisando o quadro sistêmico completo..."):
                                        prompt_holistico = f"Paciente usa: {', '.join(medicamentos_em_uso)}. Nova medicação proposta: {dados['nome_apresentacao']}. Faça uma análise clínica HOLÍSTICA em 1 parágrafo identificando efeitos em cascata, sobrecarga renal/hepática ou interações complexas entre múltiplos fármacos."
                                        try: st.session_state['cache_holistico'][chave_holistica] = model.generate_content(prompt_holistico).text
                                        except: st.session_state['cache_holistico'][chave_holistica] = "Falha ao gerar revisão completa."
                            st.success(f"**Análise de Pacote Completo:**\n\n{st.session_state['cache_holistico'][chave_holistica]}")
                        st.divider()

                    unid_bruto = dados.get("unidade_medida", "ML")
                    unid = str(unid_bruto[0]).upper() if isinstance(unid_bruto, list) and unid_bruto else str(unid_bruto).upper()

                    # FEATURE 2: VALIDAÇÃO DE DOSE MÁXIMA
                    dose_maxima = float(dados.get("dose_maxima_diaria_mg", 0))

                    if dados.get("concentracao_mg_ml") is not None:
                        conc = float(dados["concentracao_mg_ml"])
                        if dados.get("dose_mg_kg") is not None:
                            dose = peso_paciente * float(dados["dose_mg_kg"])
                            st.info(f"⚖️ Dose base ({peso_paciente}kg): {dose}mg \n\n ➡️ **Administrar: {round(dose/conc, 2)} {unid}**")
                            if dose_maxima > 0 and dose > dose_maxima:
                                st.error(f"❌ **ERRO CRÍTICO:** Dose calculada ({dose}mg) ultrapassa a Dose Máxima Diária permitida ({dose_maxima}mg).")
                        else:
                            d_pres = st.number_input("Prescrição Médica (MG):", 0.0, value=float(conc))
                            if dose_maxima > 0 and d_pres > dose_maxima:
                                st.error(f"❌ **ERRO DE PRESCRIÇÃO:** A dose de {d_pres}mg ultrapassa o limite seguro de {dose_maxima}mg/dia para este fármaco.")
                            elif d_pres > 0 and conc > 0: 
                                st.info(f"➡️ **Administrar: {round(d_pres/conc, 2)} {unid}**")
                    else: st.warning("⚠️ Dados de concentração base incompletos.")
        with col_dir:
            if sel != "(Selecione...)":
                vias_str = ", ".join(vias).lower()
                if "intravenosa" in vias_str or "iv" in vias_str:
                    with st.container(border=True):
                        st.markdown("#### 🧮 Gotejamento e Infusão")
                        vol = st.number_input("Volume do Diluente (ml):", 0.0, 1000.0, 100.0)
                        un_t = st.radio("Correr em:", ["Horas", "Minutos"], horizontal=True)
                        tmp = st.number_input("Tempo:", 0.1, value=8.0)
                        if st.button("Calcular Vazão", use_container_width=True):
                            gts = math.ceil(vol/(tmp*3)) if un_t=="Horas" else math.ceil((vol*20)/tmp)
                            st.metric("Velocidade de Infusão", f"{gts} gts/min")
    else: st.info("O banco de medicamentos está vazio.")

# ==========================================
# ABA 3: PACIENTES (COM EDIÇÃO)
# ==========================================
with aba_pacientes:
    c_add_edit, c_del = st.columns(2)
    with c_add_edit:
        with st.container(border=True):
            st.markdown("#### 📝 Gestão de Prontuário (EHR)")
            modo_paciente = st.radio("Ação:", ["Nova Admissão", "Editar Prontuário"], horizontal=True)
            if modo_paciente == "Nova Admissão":
                n = st.text_input("Nome Completo do Paciente:")
                col_id, col_ps = st.columns(2)
                id_p = col_id.number_input("Idade:", 0, 120, 30)
                ps_p = col_ps.number_input("Peso (kg):", 1.0, 250.0, 70.0)
                lista_todos = [v["nome_apresentacao"] for v in banco_medicamentos.values()]
                meds = st.multiselect("Medicamentos de Uso Contínuo:", lista_todos)
                if st.button("Salvar Novo Prontuário", type="primary", use_container_width=True):
                    if n:
                        id_pac = n.lower().replace(" ", "_")
                        banco_pacientes[id_pac] = {"nome": n, "idade": id_p, "peso": ps_p, "uso_continuo": meds, "criado_por": st.session_state['usuario_logado']}
                        with open("Pacientes.json", "w", encoding="utf-8") as f: json.dump(banco_pacientes, f, indent=2, ensure_ascii=False)
                        st.success(f"✅ Prontuário criado!")
                        time.sleep(1)
                        st.rerun()
                    else: st.error("Preencha o nome do paciente.")
            else:
                if banco_pacientes:
                    p_edit = st.selectbox("Selecione o paciente para editar:", ["(Selecionar...)"] + [v["nome"] for v in banco_pacientes.values()])
                    if p_edit != "(Selecionar...)":
                        chave_edit = next(k for k,v in banco_pacientes.items() if v["nome"]==p_edit)
                        dados_edit = banco_pacientes[chave_edit]
                        n_edit = st.text_input("Nome:", value=dados_edit["nome"])
                        col_id_e, col_ps_e = st.columns(2)
                        id_edit = col_id_e.number_input("Idade:", 0, 120, int(dados_edit.get("idade", 30)))
                        ps_edit = col_ps_e.number_input("Peso (kg):", 1.0, 250.0, float(dados_edit.get("peso", 70.0)))
                        lista_todos = [v["nome_apresentacao"] for v in banco_medicamentos.values()]
                        meds_atuais = [m for m in dados_edit.get("uso_continuo", []) if m in lista_todos]
                        meds_edit = st.multiselect("Uso Contínuo:", lista_todos, default=meds_atuais)
                        if st.button("Atualizar Dados Clínicos", type="primary", use_container_width=True):
                            banco_pacientes[chave_edit].update({"nome": n_edit, "idade": id_edit, "peso": ps_edit, "uso_continuo": meds_edit, "atualizado_por": st.session_state['usuario_logado']})
                            with open("Pacientes.json", "w", encoding="utf-8") as f: json.dump(banco_pacientes, f, indent=2, ensure_ascii=False)
                            st.success(f"✅ Prontuário atualizado!")
                            time.sleep(1)
                            st.rerun()
                else: st.info("Nenhum paciente internado.")
    with c_del:
        with st.container(border=True):
            st.markdown("#### 🗑️ Alta Médica / Exclusão")
            if cargo == "Enfermeiro": st.error("🔒 Somente Médicos e ADMs podem conceder alta.")
            elif banco_pacientes:
                p_del = st.selectbox("Selecione o paciente para Alta:", ["(Selecionar...)"] + [v["nome"] for v in banco_pacientes.values()])
                if p_del != "(Selecionar...)" and st.button("Confirmar Alta", use_container_width=True):
                    ch_del = next(k for k,v in banco_pacientes.items() if v["nome"]==p_del)
                    del banco_pacientes[ch_del]
                    with open("Pacientes.json", "w", encoding="utf-8") as f: json.dump(banco_pacientes, f, indent=2, ensure_ascii=False)
                    st.success(f"✅ Alta realizada!")
                    time.sleep(1)
                    st.rerun()
            else: st.info("Nenhum paciente internado.")

# ==========================================
# ABA 4: SISTEMA 
# ==========================================
with aba_admin:
    st.markdown("### 🤖 Gestão da Farmácia Hospitalar")
    cad, rem = st.columns(2)
    with cad:
        with st.container(border=True):
            st.markdown("#### Importação Inteligente (IA)")
            st.caption("A IA fará o mapeamento farmacológico automático.")
            n_med = st.text_input("Princípio Ativo ou Medicamento:")
            if st.button("Mapear Literatura", type="primary", use_container_width=True) and n_med:
                if model:
                    with st.spinner(f"Consultando bases de dados..."):
                        # PROMPT MODIFICADO PARA INCLUIR DOSE MÁXIMA DIÁRIA
                        prompt = f"""Atue como o Farmacêutico Chefe de um hospital de alta complexidade no Brasil. 
Sua tarefa é mapear '{n_med}' e retornar APENAS um JSON PURO. Considere interações com medicamentos brasileiros comuns (ex: Dipirona).
NUNCA use classes (ex: 'AINEs'). Liste os princípios ativos.
Chaves obrigatórias: nome_apresentacao (string), vias_permitidas (lista), unidade_medida (string: ml/comprimido/ampola/gotas), alerta_iv (string/null), concentracao_mg_ml (float/null), dose_mg_kg (float/null), dose_maxima_diaria_mg (float com o limite máximo seguro em mg por dia, ou 0 se não aplicável), interacoes_graves (lista), interacoes_moderadas (lista)."""
                        try:
                            res = model.generate_content(prompt).text
                            dados_ia = json.loads(res[res.find('{'):res.rfind('}')+1])
                            if "nome_apresentacao" in dados_ia:
                                banco_medicamentos.update({n_med.lower().replace(' ', '_'): dados_ia})
                                with open("Database.json", "w", encoding="utf-8") as f: json.dump(banco_medicamentos, f, indent=2, ensure_ascii=False)
                                st.success("✅ Protocolo adicionado com parâmetros estendidos!")
                                time.sleep(1.5)
                                st.rerun()
                            else: st.error("❌ Medicamento não encontrado.")
                        except: st.error("❌ Erro de conexão ou formatação.")
                else: st.error("Serviço de IA Offline.")
    with rem:
        with st.container(border=True):
            st.markdown("#### 🗑️ Remover Item")
            if banco_medicamentos:
                m_del = st.selectbox("Selecione a medicação:", ["(Selecionar...)"] + [v["nome_apresentacao"] for v in banco_medicamentos.values()])
                if m_del != "(Selecionar...)" and st.button("Excluir", use_container_width=True):
                    ch_m_del = next(k for k,v in banco_medicamentos.items() if v["nome_apresentacao"]==m_del)
                    del banco_medicamentos[ch_m_del]
                    with open("Database.json", "w", encoding="utf-8") as f: json.dump(banco_medicamentos, f, indent=2, ensure_ascii=False)
                    st.success("🗑️ Protocolo removido.")
                    time.sleep(1)
                    st.rerun()

# ==========================================
# ABA 5: EQUIPE (SÓ ADM)
# ==========================================
if is_admin:
    with aba_equipe:
        st.markdown("### 🛡️ Administração de Usuários")
        u_add, u_del = st.columns(2)
        with u_add:
            with st.container(border=True):
                st.markdown("#### Criar Acesso Profissional")
                u_id = st.text_input("ID de Acesso:")
                u_nm = st.text_input("Nome Completo:")
                u_sn = st.text_input("Senha:", type="password")
                u_cg = st.selectbox("Nível:", ["Médico", "Enfermeiro", "ADM"])
                if st.button("Salvar Usuário", type="primary", use_container_width=True):
                    if u_id and u_nm and u_sn:
                        banco_usuarios[u_id] = {"nome": u_nm, "senha": u_sn, "cargo": u_cg}
                        with open("Usuarios.json", "w", encoding="utf-8") as f: json.dump(banco_usuarios, f, indent=2, ensure_ascii=False)
                        st.success("✅ Credencial criada!")
                        time.sleep(1)
                        st.rerun()
                    else: st.error("Preencha todos os campos.")
        with u_del:
            with st.container(border=True):
                st.markdown("#### Revogar Acesso")
                ids = [k for k in banco_usuarios.keys() if k != "admin"]
                if ids:
                    u_rem = st.selectbox("Selecione o usuário:", ["(Selecionar...)"] + ids)
                    if u_rem != "(Selecionar...)" and st.button("Revogar", use_container_width=True):
                        del banco_usuarios[u_rem]
                        with open("Usuarios.json", "w", encoding="utf-8") as f: json.dump(banco_usuarios, f, indent=2, ensure_ascii=False)
                        st.success("🚫 Acesso revogado.")
                        time.sleep(1)
                        st.rerun()
                else: st.info("Apenas o Administrador Master existe.")
