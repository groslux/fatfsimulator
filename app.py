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

# --- 4. REAL-TIME OSINT FUNCTION (DUCKDUCKGO) ---
def fetch_realtime_news(country, sector):
    """Effectue une recherche silencieuse sur le web pour trouver des actualités récentes."""
    # On crée une requête ciblée pour dénicher les problèmes
    query = f"{country} {sector} (money laundering OR AML OR compliance OR fraud OR FATF OR sanction)"
    news_snippets = []
    news_context_for_ai = ""
    
    try:
        with DDGS() as ddgs:
            # On récupère les 3 meilleurs résultats
            results = list(ddgs.text(query, max_results=3))
            if results:
                news_context_for_ai = "REAL-TIME WEB SEARCH RESULTS (Use these to challenge the user):\n"
                for r in results:
                    news_context_for_ai += f"- Title: {r['title']}\n  Snippet: {r['body']}\n  URL: {r['href']}\n\n"
                    news_snippets.append({"title": r['title'], "url": r['href'], "snippet": r['body']})
    except Exception as e:
        # Si la recherche échoue (ex: rate limit), on retourne un contexte vide
        pass 
        
    return news_context_for_ai, news_snippets

# --- 5. ENRICHED AI CALL WITH DYNAMIC MODEL SELECTION & PYTHON SHUFFLING ---
def fetch_assessor_question(country, sector, eval_type, specific_focus):
    
    # 1. On lance d'abord la recherche OSINT
    news_text_for_ai, raw_news_list = fetch_realtime_news(country, sector)
    
    # 2. Configuration de l'IA
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
    
    # 3. Le Prompt enrichi avec l'actualité en temps réel
    prompt = f"""
    You are a highly demanding senior FATF assessor conducting an On-Site Visit based strictly on the official FATF Methodology.
    Evaluated Country: {country}.
    Sector: {sector}.
    Evaluation Type: {eval_type}.
    Specific Focus: {specific_focus}.

    {news_text_for_ai}

    CONTEXT & MINDSET:
    You do not just ask generic questions. You base your questions on simulated "desktop research" AND the real-time web search results provided above (if any). If there are recent negative press articles or sanctions in the search results, YOU MUST confront the user about them.

    CRITICAL ANTI-HALLUCINATION RULE: 
    Do NOT invent specific numbers inside the response options. The options must focus on qualitative methodologies or demonstrable actions.

    TASK:
    Generate a comprehensive assessment scenario in strict JSON format. You must provide:
    1. The core issue (from the FATF methodology) you are targeting.
    2. A simulated list of documents you "read" to prepare.
    3. The main challenging question (incorporating the real-time news if relevant).
    4. ONE explicitly correct answer (correct_answer).
    5. TWO realistic but incorrect answers (incorrect_answers).
    6. A detailed explanation of why the correct option satisfies the FATF standards.
    7. "statistical_insight": Provide a realistic, domain-specific statistic or typology for this country/sector.
    8. "statistical_source": Explicitly state the name of the official document or report where you found this statistic.
    9. "sources": An array of highly relevant methodology sources with clickable URLs.
    10. 2 or 3 follow-up questions the assessment team would logically ask.

    RESPOND EXCLUSIVELY IN THE FOLLOWING EXACT JSON STRUCTURE:
    {{
        "core_issue": "Specific core issue or sub-criterion targeted...",
        "documents_analyzed": ["Document 1", "Document 2"],
        "question": "The main, challenging question from the assessor...",
        "correct_answer": "The perfectly compliant/effective response text...",
        "incorrect_answers": [
            "Realistic but flawed response 1...",
            "Realistic but flawed response 2..."
        ],
        "explanation": "Detailed explanation citing the FATF methodology...",
        "statistical_insight": "Real historical data or established typological trend...",
        "statistical_source": "Name of the report or document backing up the statistical insight...",
        "sources": [
            {{"title": "FATF Methodology", "url": "https://www.fatf-gafi.org/en/publications/Mutualevaluations/Fatf-methodology.html"}}
        ],
        "follow_up_questions": ["Follow-up question 1?", "Follow-up question 2?"]
    }}
    """
    
    try:
        response = model.generate_content(prompt)
        clean_text = response.text.replace('```json', '').replace('```', '').strip()
        data = json.loads(clean_text)
        
        # PYTHON SHUFFLING LOGIC
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
            
        # On attache les vrais articles de presse trouvés pour les afficher dans l'UI
        data['realtime_news'] = raw_news_list
            
        return data
        
    except Exception as e:
        st.error(f"Error communicating with AI: {e}")
        return None

# --- 6. UI: HOME & DESIGN ---
st.title("⚖️ FATF Assessor AI - Professional Simulator")
st.write("Train against a rigorous AI assessor utilizing the full FATF methodology, complete with real-time OSINT and qualitative challenges.")

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
        with st.spinner("The assessment team is analyzing the NRA, scraping real-time press articles, and preparing their core questions..."):
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
    
    with st.sidebar.expander("📚 Assessor's Desktop Research & OSINT", expanded=True):
        st.write("**Methodology Focus:**")
        st.caption(f"{st.session_state.current_context['specific_focus']}")
        st.write("**Core Issue Evaluated:**")
        st.caption(f"{q.get('core_issue', 'N/A')}")
        
        # NOUVEAU : Affichage des actualités en temps réel trouvées
        if q.get('realtime_news'):
            st.markdown("---")
            st.write("🚨 **Real-Time Press Articles Analyzed:**")
            for news in q.get('realtime_news', []):
                st.markdown(f"- [{news['title']}]({news['url']})")
                st.caption(f"_{news['snippet'][:150]}..._")
            st.markdown("---")

        st.write("**Documents Analyzed Prior to Visit:**")
        for doc in q.get('documents_analyzed', []):
            st.markdown(f"- {doc}")

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
        st.success(f"✅ **Strong Posture!** You selected Option {user_choice}.")
    else:
        st.error(f"❌ **Weak Posture.** You selected Option {user_choice}. The expected answer was **{q['correct_option']}**.")
        
    st.markdown(f"### 💡 FATF Methodology Analysis:\n{q['explanation']}")
    
    st.warning(f"**📉 Statistical / Typological Reality Check:**\n\n{q.get('statistical_insight', 'N/A')}\n\n*Source: {q.get('statistical_source', 'Knowledge Base')}*")
    
    st.markdown("### 🗣️ Anticipated Follow-Up Questions from the Assessment Team:")
    for fq in q.get('follow_up_questions', []):
        st.markdown(f"> *\"{fq}\"*")
        
    if q.get('sources'):
        st.write("---")
        st.markdown("### 🔗 Reference Material")
        for source in q.get('sources', []):
            st.markdown(f"🌐 [{source.get('title', 'Reference Document')}]({source.get('url', '#')})")
        
    st.write("---")
    
    col_nav1, col_nav2 = st.columns(2)
    with col_nav1:
        if st.button("Next Question on this Topic ➡️", use_container_width=True):
            with st.spinner("The assessor scrapes the latest news and consults their notes for the next angle..."):
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
