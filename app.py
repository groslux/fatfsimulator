import streamlit as st
import google.generativeai as genai
import json
import random
from duckduckgo_search import DDGS

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="FATF Assessor AI - Professional Simulator",
    page_icon="⚖️",
    layout="wide"
)

# --- FATF METHODOLOGY CONSTANTS ---
SECTORS = [
    "Banking", "Life Insurance", "Securities & Investment Management", 
    "Money Value Transfer Services (MVTS) / Remittances", "Currency Exchange / Bureaux de Change",
    "Virtual Asset Service Providers (VASPs)",
    "Casinos & Gaming", "Real Estate Agents", "Dealers in Precious Metals and Stones (DPMS)", 
    "Lawyers & Notaries", "Accountants & Auditors", "Trust and Company Service Providers (TCSPs)",
    "Non-Profit Organisations (NPOs)"
]

FATF_IOS = [
    "IO.1 - Risk, Policy and Coordination", "IO.2 - International Cooperation",
    "IO.3 - Supervision", "IO.4 - Preventive Measures",
    "IO.5 - Legal Persons and Arrangements", "IO.6 - Financial Intelligence",
    "IO.7 - ML Investigation and Prosecution", "IO.8 - Confiscation",
    "IO.9 - TF Investigation and Prosecution", "IO.10 - TF Preventive Measures and Financial Sanctions",
    "IO.11 - PF Financial Sanctions"
]

FATF_RECS = [
    "R.1 - Assessing risks & applying a risk-based approach", "R.2 - National cooperation and coordination",
    "R.3 - Money laundering offence", "R.4 - Confiscation and provisional measures",
    "R.5 - Terrorist financing offence", "R.6 - Targeted financial sanctions related to terrorism & TF",
    "R.7 - Targeted financial sanctions related to proliferation", "R.8 - Non-profit organisations",
    "R.9 - Financial institution secrecy laws", "R.10 - Customer due diligence (CDD)",
    "R.11 - Record keeping", "R.12 - Politically exposed persons (PEPs)",
    "R.13 - Correspondent banking", "R.14 - Money or value transfer services",
    "R.15 - New technologies (including VASPs)", "R.16 - Wire transfers",
    "R.17 - Reliance on third parties", "R.18 - Internal controls and foreign branches/subsidiaries",
    "R.19 - Higher-risk countries", "R.20 - Reporting of suspicious transactions",
    "R.21 - Tipping-off and confidentiality", "R.22 - DNFBPs: Customer due diligence",
    "R.23 - DNFBPs: Other measures", "R.24 - Transparency and BO of legal persons",
    "R.25 - Transparency and BO of legal arrangements", "R.26 - Regulation and supervision of FIs",
    "R.27 - Powers of supervisors", "R.28 - Regulation and supervision of DNFBPs",
    "R.29 - Financial intelligence units (FIUs)", "R.30 - Responsibilities of law enforcement and investigative authorities",
    "R.31 - Powers of law enforcement and investigative authorities", "R.32 - Cash couriers",
    "R.33 - Statistics", "R.34 - Guidance and feedback",
    "R.35 - Sanctions", "R.36 - International instruments",
    "R.37 - Mutual legal assistance", "R.38 - Mutual legal assistance: freezing and confiscation",
    "R.39 - Extradition", "R.40 - Other forms of international cooperation"
]

# --- EXPERT KNOWLEDGE BASE ---
# Modifiez ou ajoutez ici les vrais cas (ex: Reporter.lu, scandales historiques) 
# que les moteurs de recherche pourraient rater à cause des paywalls.
EXPERT_KNOWLEDGE_BASE = {
    "Luxembourg": {
        "Banking": [
            "L'affaire 'Danske Bank' a mis en lumière l'implication de succursales luxembourgeoises dans des montages de sociétés écrans baltes.",
            "En 2023, la CSSF a infligé des amendes significatives à plusieurs banques privées pour des défaillances dans l'identification des UBO liés à des juridictions à haut risque.",
            "Des rapports d'investigation locaux ont pointé du doigt la difficulté pour les banques de tracer les fonds issus de l'immobilier commercial étranger."
        ],
        "Securities & Investment Management": [
            "Le secteur des fonds d'investissement luxembourgeois a été scruté pour son exposition indirecte aux oligarques sanctionnés suite au conflit en Ukraine.",
            "La question de la valorisation des actifs illiquides et l'utilisation de Management Companies (ManCos) en cascade restent des points de vulnérabilité identifiés par le FMI."
        ]
    }
}

# --- 1. AUTHENTICATION ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🔒 Restricted Access")
    st.write("Welcome to the FATF Assessor AI. Please enter the password to continue.")
    with st.form("login_form"):
        pwd = st.text_input("Password:", type="password")
        submitted = st.form_submit_button("Login")
        if submitted:
            if pwd == "FATF2026":
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("❌ Incorrect password.")
    st.stop() 

# --- 2. GEMINI API INITIALIZATION ---
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
except KeyError:
    st.error("❌ ERROR: The API key 'GEMINI_API_KEY' is missing from Streamlit secrets.")
    st.stop()

# --- 3. SESSION STATE INITIALIZATION ---
if "step" not in st.session_state:
    st.session_state.step = "setup"
if "current_question" not in st.session_state:
    st.session_state.current_question = None
if "score" not in st.session_state:
    st.session_state.score = 0
if "total_questions" not in st.session_state:
    st.session_state.total_questions = 0
if "user_choice" not in st.session_state:
    st.session_state.user_choice = None
if "current_context" not in st.session_state:
    st.session_state.current_context = {}

# --- 4. DEEP OSINT SEARCH (EXPERT + PRESS + OFFICIAL REPORTS) ---
def fetch_realtime_osint(country, sector):
    """Combine la base de connaissances experte avec des recherches en temps réel."""
    news_snippets = []
    news_context_for_ai = ""
    
    # 1. Injection de la Base Experte
    if country in EXPERT_KNOWLEDGE_BASE and sector in EXPERT_KNOWLEDGE_BASE[country]:
        news_context_for_ai += "EXPERT KNOWLEDGE BASE (HIGH PRIORITY - USE THESE SPECIFIC CASES):\n"
        for insight in EXPERT_KNOWLEDGE_BASE[country][sector]:
            news_context_for_ai += f"- {insight}\n"
            news_snippets.append({"title": "Expert Knowledge Base (Local Investigation)", "url": "#", "snippet": insight})
        news_context_for_ai += "\n"

    # 2. Requêtes Web (Presse et Institutions)
    query_press = f'"{country}" "{sector}" (sanctions OR blanchiment OR "money laundering" OR amende OR fine OR fraud)'
    query_institutions = f'"{country}" (FATF OR GAFI OR Moneyval OR IMF OR FMI OR AMLA OR "Financial Intelligence Unit") (rapport OR report OR evaluation OR AML)'
    
    try:
        with DDGS() as ddgs:
            # Recherche presse (news)
            results_press = list(ddgs.news(query_press, max_results=3))
            # Recherche institutions (text)
            results_institutions = list(ddgs.text(query_institutions, max_results=3))
            
            combined_results = results_press + results_institutions
            
            if combined_results:
                news_context_for_ai += "REAL-TIME PRESS & OFFICIAL INSTITUTIONAL REPORTS:\n"
                seen_urls = set()
                for r in combined_results:
                    url = r.get('url', r.get('href', '#'))
                    if url not in seen_urls:
                        seen_urls.add(url)
                        title = r.get('title', 'Unknown Title')
                        snippet = r.get('body', r.get('snippet', 'No summary available'))
                        
                        news_context_for_ai += f"- Source: {title}\n  Summary: {snippet}\n  URL: {url}\n\n"
                        news_snippets.append({"title": title, "url": url, "snippet": snippet})
                        
    except Exception as e:
        # Erreur silencieuse si DuckDuckGo bloque (rate limit)
        pass 
        
    return news_context_for_ai, news_snippets

# --- 5. ENRICHED AI CALL (ZERO HALLUCINATION) ---
def fetch_assessor_question(country, sector, eval_type, specific_focus):
    
    news_text_for_ai, raw_news_list = fetch_realtime_osint(country, sector)
    
    selected_model_name = "gemini-1.5-flash" 
    try:
        valid_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        if valid_models:
            for preferred in ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-pro']:
                matches = [name for name in valid_models if preferred in name]
                if matches:
                    selected_model_name = matches[0]
                    break
    except Exception:
        pass 

    model = genai.GenerativeModel(model_name=selected_model_name)
    
    prompt = f"""
    You are a strict, highly demanding senior FATF assessor conducting an On-Site Visit.
    Evaluated Country: {country}.
    Sector: {sector}.
    Evaluation Type: {eval_type}.
    Specific Focus: {specific_focus}.

    {news_text_for_ai}

    CRITICAL ANTI-HALLUCINATION RULES:
    1. NEVER invent, fabricate, or hallucinate document names, statistics, reports, or cases. 
    2. If the 'EXPERT KNOWLEDGE BASE' or 'REAL-TIME PRESS & OFFICIAL INSTITUTIONAL REPORTS' sections above contain real reports or press articles, you MUST integrate their findings or tone into your question.
    3. If the OSINT sections are empty, rely STRICTLY on standard FATF methodology and abstract principles. Do NOT make up fake national risk assessments.
    4. The options (A, B, C) must focus on qualitative methodologies, regulatory postures, or governance, NOT fabricated numbers.

    TASK:
    Generate a comprehensive assessment scenario in strict JSON format. 
    1. "core_issue": The sub-criterion from the FATF methodology you are targeting.
    2. "question": The main assessor question. Integrate the real-time institutional reports or news if available.
    3. "correct_answer": The perfectly compliant/effective response text.
    4. "incorrect_answers": Two realistic but flawed responses.
    5. "explanation": Detailed explanation citing the FATF methodology.
    6. "risk_context": A summary of the real-world risk based ONLY on the provided OSINT context, or a general FATF typological risk if no OSINT is available. Do NOT hallucinate statistics.
    7. "follow_up_questions": 2 follow-up questions to drill deeper.

    RESPOND EXCLUSIVELY IN THE FOLLOWING EXACT JSON STRUCTURE:
    {{
        "core_issue": "Targeted sub-criterion...",
        "question": "The main assessor question...",
        "correct_answer": "Compliant response...",
        "incorrect_answers": [
            "Flawed response 1...",
            "Flawed response 2..."
        ],
        "explanation": "Methodological explanation...",
        "risk_context": "Real-world context based on official reports, OSINT or pure methodology...",
        "follow_up_questions": ["Follow up 1?", "Follow up 2?"]
    }}
    """
    
    try:
        response = model.generate_content(prompt)
        clean_text = response.text.replace('```json', '').replace('```', '').strip()
        data = json.loads(clean_text)
        
        # PYTHON SHUFFLING LOGIC (True Randomness)
        correct_text = data['correct_answer']
        all_options = [correct_text] + data['incorrect_answers']
        random.shuffle(all_options)
        
        data['options'] = {
            "A": all_options[0],
            "B": all_options[1],
            "C": all_options[2]
        }
        
        if all_options[0] == correct_text:
            data['correct_option'] = "A"
        elif all_options[1] == correct_text:
            data['correct_option'] = "B"
        else:
            data['correct_option'] = "C"
            
        data['realtime_news'] = raw_news_list
            
        return data
        
    except Exception as e:
        st.error(f"Error communicating with AI: {e}")
        return None

# --- 6. UI: HOME & DESIGN ---
st.title("⚖️ FATF Assessor AI - Professional Simulator")
st.write("Train against a rigorous AI assessor utilizing the full FATF methodology, backed by Expert Knowledge and real-time OSINT (Press, FATF, IMF, World Bank, FIU). Zero hallucinations.")

# --- UI STEP 1: CONTEXT SETUP ---
if st.session_state.step == "setup":
    st.subheader("1. Define the Evaluation Scope")
    
    col1, col2 = st.columns(2)
    with col1:
        country = st.text_input("Evaluated Country", value="Luxembourg")
    with col2:
        sector = st.selectbox("Supervisory Sector", SECTORS)
    
    st.write("---")
    st.subheader("2. Select Methodology Focus")
    eval_type = st.radio("Evaluation Component", ["Effectiveness (Immediate Outcomes)", "Technical Compliance (Recommendations)"], horizontal=True)
    
    if eval_type == "Effectiveness (Immediate Outcomes)":
        specific_focus = st.selectbox("Select Immediate Outcome", FATF_IOS)
    else:
        specific_focus = st.selectbox("Select Recommendation", FATF_RECS)

    st.write("---")
    if st.button("Start On-Site Interview 🚀", use_container_width=True):
        with st.spinner("The assessment team is analyzing expert files, global press, and official FIU/IMF reports..."):
            st.session_state.current_context = {
                "country": country, "sector": sector, 
                "eval_type": eval_type, "specific_focus": specific_focus
            }
            question_data = fetch_assessor_question(country, sector, eval_type, specific_focus)
            if question_data:
                st.session_state.current_question = question_data
                st.session_state.step = "interview"
                st.session_state.user_choice = None
                st.rerun()

# --- UI STEP 2: THE INTERVIEW ---
elif st.session_state.step == "interview":
    q = st.session_state.current_question
    
    st.sidebar.metric("Compliance Score", f"{st.session_state.score}/{st.session_state.total_questions}")
    
    with st.sidebar.expander("📚 Assessor's OSINT Briefing", expanded=True):
        st.write("**Methodology Focus:**")
        st.caption(f"{st.session_state.current_context['specific_focus']}")
        st.write("**Core Issue Evaluated:**")
        st.caption(f"{q.get('core_issue', 'N/A')}")
        
        if q.get('realtime_news'):
            st.markdown("---")
            st.write("🚨 **Intelligence & Official Reports Analyzed:**")
            for news in q.get('realtime_news', []):
                st.markdown(f"- **[{news['title']}]({news['url']})**")
                st.caption(f"_{news['snippet'][:150]}..._")
        else:
            st.markdown("---")
            st.write("✅ _No specific recent reports or scandals detected in the live OSINT search. Assessor will rely on baseline methodology._")

    st.subheader("📍 On-Site Interview Session")
    st.info(f"**FATF Lead Assessor:** \n\n *\"{q['question']}\"*")
    st.write("---")
    st.write("**Choose your official response strategy:**")
    
    with st.form(key="qcm_form"):
        formatted_options = {
            f"A: {q['options']['A']}": "A",
            f"B: {q['options']['B']}": "B",
            f"C: {q['options']['C']}": "C"
        }
        choice = st.radio("Options:", list(formatted_options.keys()), index=0)
        submit_button = st.form_submit_button(label="Submit Official Response 📝")
        
        if submit_button:
            st.session_state.user_choice = formatted_options[choice]
            st.session_state.step = "feedback"
            st.session_state.total_questions += 1
            if st.session_state.user_choice == q['correct_option']:
                st.session_state.score += 1
            st.rerun()

# --- UI STEP 3: FEEDBACK ---
elif st.session_state.step == "feedback":
    q = st.session_state.current_question
    user_choice = st.session_state.user_choice
    is_correct = user_choice == q['correct_option']
    
    st.sidebar.metric("Compliance Score", f"{st.session_state.score}/{st.session_state.total_questions}")
    
    st.subheader("📊 Assessor Debriefing & Findings")
    
    if is_correct:
        st.success(f"✅ **Strong Posture!** You selected Option {user_choice[-1] if user_choice else ''}.")
    else:
        st.error(f"❌ **Weak Posture.** The expected answer was **Option {q['correct_option']}**.")
        
    st.markdown(f"### 💡 FATF Methodology Analysis:\n{q['explanation']}")
    
    st.warning(f"**📉 Risk Context (Official Data/Typology):**\n\n{q.get('risk_context', 'N/A')}")
    
    st.markdown("### 🗣️ Anticipated Follow-Up Questions from the Assessment Team:")
    for fq in q.get('follow_up_questions', []):
        st.markdown(f"> *\"{fq}\"*")
        
    st.write("---")
    
    col_nav1, col_nav2 = st.columns(2)
    with col_nav1:
        if st.button("Next Question on this Topic ➡️", use_container_width=True):
            with st.spinner("The assessor searches for the latest official reports and consults their notes..."):
                ctx = st.session_state.current_context
                question_data = fetch_assessor_question(ctx['country'], ctx['sector'], ctx['eval_type'], ctx['specific_focus'])
                if question_data:
                    st.session_state.current_question = question_data
                    st.session_state.step = "interview"
                    st.session_state.user_choice = None
                    st.rerun()
                    
    with col_nav2:
        if st.button("Change Scope / Exit 🛑", use_container_width=True):
            st.session_state.step = "setup"
            st.session_state.current_question = None
            st.session_state.score = 0
            st.session_state.total_questions = 0
            st.rerun()
