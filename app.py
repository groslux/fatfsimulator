import streamlit as st
import google.generativeai as genai
import json

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

# --- 4. ENRICHED AI CALL WITH DYNAMIC MODEL SELECTION ---
def fetch_assessor_question(country, sector, eval_type, specific_focus):
    
    # DYNAMIC SEARCH: Ask Google which models are actually allowed for your API key
    selected_model_name = "gemini-pro" # Ultimate fallback
    try:
        valid_models = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                valid_models.append(m.name)
                
        if valid_models:
            # Prioritize models: flash first, then pro versions
            for preferred in ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-pro']:
                matches = [name for name in valid_models if preferred in name]
                if matches:
                    selected_model_name = matches[0]
                    break
    except Exception:
        pass # Silently proceed with fallback if listing fails

    model = genai.GenerativeModel(model_name=selected_model_name)
    
    prompt = f"""
    You are a highly demanding senior FATF assessor conducting an On-Site Visit based strictly on the official FATF Methodology.
    Evaluated Country: {country}.
    Sector: {sector}.
    Evaluation Type: {eval_type}.
    Specific Focus: {specific_focus}.

    CONTEXT & MINDSET:
    You do not just ask generic questions. You base your questions on simulated "desktop research" you conducted before arriving on-site. You are looking for concrete statistics, implementation proof, and clear mitigation of specific typologies relevant to {country}.

    TASK:
    Generate a comprehensive assessment scenario in strict JSON format. You must provide:
    1. The core issue (from the FATF methodology) you are targeting.
    2. A simulated list of documents you "read" to prepare (e.g., NRA 2024, FIU Annual Report, mutual evaluation of a neighboring country, specific press articles).
    3. The main challenging question.
    4. Three response options (A, B, C) where only one demonstrates true effectiveness or compliance.
    5. A detailed explanation of why the correct option satisfies the FATF standards.
    6. Concrete statistical insights or typologies that back up your assessment.
    7. 2 or 3 follow-up questions the assessment team would logically ask right after this discussion to drill deeper.

    RESPOND EXCLUSIVELY IN THE FOLLOWING EXACT JSON STRUCTURE (No markdown tags, just raw JSON):
    {{
        "core_issue": "Specific core issue or sub-criterion targeted...",
        "documents_analyzed": ["Document 1", "Document 2", "Document 3"],
        "question": "The main, challenging question from the assessor...",
        "options": {{
            "A": "Option A text",
            "B": "Option B text",
            "C": "Option C text"
        }},
        "correct_option": "A",
        "explanation": "Detailed explanation citing the FATF methodology...",
        "statistical_insight": "A realistic, domain-specific statistic or typology (e.g., 'In 2023, only 2% of STRs led to a conviction...').",
        "follow_up_questions": ["Follow-up question 1?", "Follow-up question 2?"]
    }}
    """
    
    try:
        response = model.generate_content(prompt)
        # Clean up any potential markdown wrappers around the JSON
        clean_text = response.text.replace('```json', '').replace('```', '').strip()
        data = json.loads(clean_text)
        return data
    except Exception as e:
        st.error(f"Error communicating with AI: {e}")
        st.info(f"Model tried: {selected_model_name}")
        return None

# --- 5. UI: HOME & DESIGN ---
st.title("⚖️ FATF Assessor AI - Professional Simulator")
st.write("Train against a rigorous AI assessor utilizing the full FATF methodology, complete with simulated desktop research and statistical challenges.")

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
        with st.spinner("The assessment team is analyzing the NRA, FIU reports, and preparing their core questions..."):
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
    
    # Display the Assessor's background research
    with st.sidebar.expander("📚 Assessor's Desktop Research", expanded=True):
        st.write("**Methodology Focus:**")
        st.caption(f"{st.session_state.current_context['specific_focus']}")
        st.write("**Core Issue Evaluated:**")
        st.caption(f"{q.get('core_issue', 'N/A')}")
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
    
    # Enriched Statistical Feedback
    st.warning(f"**📉 Statistical / Typological Reality Check:**\n\n{q.get('statistical_insight', 'N/A')}")
    
    # The Follow-up Questions (Crucial for FATF prep)
    st.markdown("### 🗣️ Anticipated Follow-Up Questions from the Assessment Team:")
    for fq in q.get('follow_up_questions', []):
        st.markdown(f"> *\"{fq}\"*")
        
    st.write("---")
    
    col_nav1, col_nav2 = st.columns(2)
    with col_nav1:
        if st.button("Next Question on this Topic ➡️", use_container_width=True):
            with st.spinner("The assessor consults their notes for the next angle..."):
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
