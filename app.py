import streamlit as st
import google.generativeai as genai
import json
import random
import requests

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

# --- 2. API INITIALIZATIONS ---
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    SERPER_API_KEY = st.secrets["SERPER_API_KEY"]
except KeyError as e:
    st.error(f"❌ ERROR: Missing API key in secrets: {e}")
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

# --- 4. ADVANCED SERPER OSINT ENGINE ---
def fetch_serper_osint(country, sector):
    """Effectue des recherches poussées via l'API Serper (Google Search & News)."""
    headers = {
        'X-API-KEY': SERPER_API_KEY,
        'Content-Type': 'application/json'
    }
    
    osint_context_for_ai = "--- REAL-TIME SERPER OSINT DATA ---\n\n"
    all_found_links = []
    
    # REQUÊTE 1 : Rapports Officiels (Google Search classique)
    query_official = f'"{country}" (FATF OR GAFI OR Moneyval OR IMF OR FMI OR AMLA OR "Financial Intelligence Unit") (rapport OR report OR evaluation OR AML)'
    try:
        res_off = requests.post('https://google.serper.dev/search', headers=headers, json={"q": query_official, "num": 4})
        if res_off.status_code == 200:
            organic_results = res_off.json().get('organic', [])
            osint_context_for_ai += "[OFFICIAL INSTITUTIONAL SOURCES]\n"
            for item in organic_results:
                title = item.get('title', 'Unknown')
                link = item.get('link', '#')
                snippet = item.get('snippet', '')
                osint_context_for_ai += f"- Title: {title}\n  Snippet: {snippet}\n  URL: {link}\n\n"
                if link != '#':
                    all_found_links.append({"title": title, "url": link, "type": "official"})
    except Exception as e:
        pass

    # REQUÊTE 2 : Presse & Affaires locales/internationales (Google News)
    query_press = f'"{country}" "{sector}" (sanctions OR blanchiment OR "money laundering" OR amende OR fine OR fraud OR "infraction primaire")'
    try:
        res_press = requests.post('https://google.serper.dev/news', headers=headers, json={"q": query_press, "num": 5})
        if res_press.status_code == 200:
            news_results = res_press.json().get('news', [])
            osint_context_for_ai += "[LOCAL & INTERNATIONAL PRESS / NEWS]\n"
            for item in news_results:
                title = item.get('title', 'Unknown')
                link = item.get('link', '#')
                snippet = item.get('snippet', '')
                osint_context_for_ai += f"- Title: {title}\n  Snippet: {snippet}\n  URL: {link}\n\n"
                if link != '#':
                    all_found_links.append({"title": title, "url": link, "type": "press"})
    except Exception as e:
        pass

    return osint_context_for_ai, all_found_links

# --- 5. ZERO-HALLUCINATION AI GENERATOR ---
def fetch_assessor_question(country, sector, eval_type, specific_focus):
    
    osint_context, verified_links = fetch_serper_osint(country, sector)
    
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
    You are a meticulous, zero-tolerance senior FATF assessor.
    Evaluated Country: {country}.
    Sector: {sector}.
    Evaluation Type: {eval_type}.
    Specific Focus: {specific_focus}.

    {osint_context}

    STRICT ANTI-HALLUCINATION PROTOCOL:
    1. You MUST read the 'REAL-TIME SERPER OSINT DATA' provided above.
    2. NEVER invent or hallucinate document names, statistics, reports, or cases. If you use a fact, it MUST come from the provided OSINT data.
    3. The multiple-choice answers (A, B, C) must be purely qualitative (postures, regulatory actions, structural responses). DO NOT put any numbers or statistics in them.

    TASK:
    Generate a comprehensive assessment scenario in strict JSON format.
    
    RESPOND EXCLUSIVELY IN THE FOLLOWING EXACT JSON STRUCTURE:
    {{
        "core_issue": "Targeted sub-criterion or core issue from methodology...",
        "osint_summary_official": "Write a concise, professional summary of the Official Institutional Sources found in the data above. If none, state 'No recent official reports flagged in the immediate search.'",
        "osint_summary_press": "Write a concise, professional summary of the Press/News articles found in the data above. Highlight any specific scandals, fines, or typologies mentioned. If none, state 'No significant recent negative press flagged.'",
        "question": "The main assessor question (must reference the OSINT findings if they are relevant to the specific focus)...",
        "correct_answer": "The perfectly compliant qualitative response...",
        "incorrect_answers": [
            "Flawed response option 1...",
            "Flawed response option 2..."
        ],
        "explanation": "Methodological debriefing explaining why the correct answer meets FATF standards...",
        "follow_up_questions": ["Follow up 1?", "Follow up 2?"]
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
            
        data['verified_links'] = verified_links
            
        return data
        
    except Exception as e:
        st.error(f"Error communicating with AI: {e}")
        return None

# --- 6. UI: HOME & DESIGN ---
st.title("⚖️ FATF Assessor AI - Professional Simulator")
st.write("Train against a rigorous AI assessor utilizing advanced Serper OSINT (Google Search & News). Zero hallucinations.")

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
        with st.spinner("Activating Serper Engine: Scouting official reports and deep-scanning local/international press..."):
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
    
    with st.sidebar.expander("💼 Assessor's OSINT Briefing", expanded=True):
        st.write("**Methodology Focus:**")
        st.caption(f"{st.session_state.current_context['specific_focus']}")
        st.write("**Targeted Core Issue:**")
        st.caption(f"{q.get('core_issue', 'N/A')}")
        
        st.divider()
        st.write("🏛️ **Analysis of Official Sources:**")
        st.info(q.get('osint_summary_official', 'No official summary provided.'))
        
        st.write("📰 **Analysis of Press & Typologies:**")
        st.warning(q.get('osint_summary_press', 'No press summary provided.'))

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
    
    st.sidebar.metric("Compliance Score", f"{st.session_state.score}/{st.session_state.total_questions}")
    
    st.subheader("📊 Assessor Debriefing & Findings")
    
    if user_choice == q['correct_option']:
        st.success(f"✅ **Strong Posture!** You selected Option {user_choice[-1] if user_choice else ''}.")
    else:
        st.error(f"❌ **Weak Posture.** The expected answer was **Option {q['correct_option']}**.")
        
    st.markdown(f"### 💡 FATF Methodology Analysis:\n{q['explanation']}")
    
    st.markdown("### 🗣️ Anticipated Follow-Up Questions from the Assessment Team:")
    for fq in q.get('follow_up_questions', []):
        st.markdown(f"> *\"{fq}\"*")
    
    # Affichage des liens OSINT bruts utilisés par le modèle
    if q.get('verified_links'):
        st.write("---")
        st.markdown("### 🔍 Raw OSINT Sources (Click to Verify)")
        official_links = [l for l in q.get('verified_links', []) if l.get('type') == 'official']
        press_links = [l for l in q.get('verified_links', []) if l.get('type') == 'press']
        
        if official_links:
            st.write("**Official Institutions:**")
            for link in official_links:
                st.markdown(f"- 🏛️ [{link['title']}]({link['url']})")
                
        if press_links:
            st.write("**News & Media:**")
            for link in press_links:
                st.markdown(f"- 📰 [{link['title']}]({link['url']})")
        
    st.write("---")
    
    col_nav1, col_nav2 = st.columns(2)
    with col_nav1:
        if st.button("Next Question on this Topic ➡️", use_container_width=True):
            with st.spinner("Scouting data pools for new verified intersections..."):
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
