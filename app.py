import streamlit as st
import google.generativeai as genai
import json
import re

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

# --- 1. AUTHENTICATION (PASSWORD) ---
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

# --- 4. DYNAMIC MODEL SELECTION & AI CALL ---
def fetch_assessor_question(country, sector, eval_type, specific_focus):
    
    # DYNAMIC SEARCH: Ask Google which models are actually allowed for your API key
    selected_model_name = "models/gemini-1.5-flash" # Default fallback
    try:
        valid_models = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                valid_models.append(m.name)
                
        if valid_models:
            # Prioritize 1.5-flash, then 1.5-pro, then 1.0-pro, then whatever is available
            for preferred in ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-1.0-pro', 'gemini-pro']:
                matches = [name for name in valid_models if preferred in name]
                if matches:
                    selected_model_name = matches[0]
                    break
            else:
                selected_model_name = valid_models[0] # Grab the first working model if priorities fail
    except Exception as e:
        st.warning("Could not list models dynamically, attempting fallback...")

    # Initialize the model with the guaranteed working name
    model = genai.GenerativeModel(model_name=selected_model_name)
    
    prompt = f"""
    You are a highly demanding senior FATF assessor conducting an On-Site Visit based strictly on the official FATF Methodology.
    Evaluated Country: {country}.
    Sector: {sector}.
    Evaluation Type: {eval_type}.
    Specific Focus: {specific_focus}.

    CONTEXT:
    Draw upon your extensive knowledge of AML/CFT typologies, known vulnerabilities for this specific sector, and the general risk profile of {country}.

    TASK:
    1. Generate an incisive and challenging question directly targeting the core issues of {specific_focus}.
    2. Ground the question in realistic scenarios, statistics, or common regulatory failings relevant to the chosen sector and country.
    3. Provide 3 realistic response options (A, B, C) that a country's representative might give.
       - The CORRECT option must demonstrate true {eval_type} according to the FATF text (e.g., proactive risk management, proven outcomes, or perfect legal alignment).
       - The INCORRECT options should represent common FATF evaluation failings (e.g., relying solely on legislation without implementation, lack of resources, defensive but empty statements).

    RESPOND EXCLUSIVELY IN VALID JSON FORMAT. Do not include Markdown blocks (like ```json). Just the raw JSON object:
    {{
        "fatf_reference": "{specific_focus}",
        "question": "The assessor's specific, challenging question...",
        "options": {{
            "A": "Option A text",
            "B": "Option B text",
            "C": "Option C text"
        }},
        "correct_option": "A", 
        "explanation": "Detailed explanation citing the FATF methodology on why this option is correct.",
        "additional_data": "A realistic example of a statistic, typology, or known risk relevant to this scenario."
    }}
    """
    
    try:
        response = model.generate_content(prompt)
        # Manually clean up any markdown the model might accidentally include
        clean_text = response.text.replace('```json', '').replace('```', '').strip()
        data = json.loads(clean_text)
        return data
        
    except Exception as e:
        st.error(f"Error communicating with AI: {e}")
        st.info(f"Diagnostique: Le modèle utilisé était '{selected_model_name}'. Vérifiez que votre API Key a les droits sur ce modèle.")
        if 'response' in locals() and hasattr(response, 'text'):
             with st.expander("Voir la réponse brute de l'IA (Debug)"):
                 st.write(response.text)
        return None

# --- 5. UI: HOME & DESIGN ---
st.title("⚖️ FATF Assessor AI - Professional Simulator")
st.write("Train against a rigorous AI assessor utilizing the full FATF methodology.")

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
        with st.spinner("The assessor is reviewing the methodology and preparing the scenario..."):
            
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
    st.subheader("📍 On-Site Interview Session")
    st.caption(f"📘 **Methodology Focus:** {q.get('fatf_reference', 'N/A')}")
    
    st.info(f"**FATF Assessor:** \n\n *\"{q['question']}\"*")
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
    st.subheader("📊 Assessor Debriefing")
    
    if is_correct:
        st.success(f"✅ **Strong Posture!** You selected Option {user_choice}.")
    else:
        st.error(f"❌ **Weak Posture.** You selected Option {user_choice}. The expected option was **{q['correct_option']}**.")
        
    st.markdown(f"### 💡 FATF Methodology Analysis:\n{q['explanation']}")
    st.markdown("### 🌐 Contextual Insight:")
    st.warning(q['additional_data'])
    st.write("---")
    
    col_nav1, col_nav2 = st.columns(2)
    with col_nav1:
        if st.button("Next Question on this Topic ➡️", use_container_width=True):
            with st.spinner("The assessor pivots to another angle..."):
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
