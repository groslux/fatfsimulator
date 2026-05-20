import streamlit as st
import google.generativeai as genai
import json

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="FATF Assessor AI - Mutual Evaluation Simulator",
    page_icon="🕵️‍♂️",
    layout="wide"
)

# --- AUTHENTICATION (MOT DE PASSE) ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

# Si l'utilisateur n'est pas authentifié, on affiche l'écran de connexion et on bloque la suite
if not st.session_state.authenticated:
    st.title("🔒 Restricted Access")
    st.write("Welcome to the FATF Assessor AI. Please enter the password to continue.")
    
    pwd = st.text_input("Password:", type="password")
    
    if st.button("Login"):
        if pwd == "FATF2026":
            st.session_state.authenticated = True
            st.rerun()  # Recharge la page pour afficher l'application
        else:
            st.error("❌ Incorrect password.")
            
    st.stop()  # Empêche l'exécution du reste du code tant que le mot de passe n'est pas bon

# =====================================================================
# LA SUITE DU CODE NE S'EXÉCUTE QUE SI LE MOT DE PASSE EST CORRECT
# =====================================================================

# --- GEMINI API INITIALIZATION (VIA SECRETS) ---
try:
    # L'application cherche la clé dans le coffre-fort Streamlit
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
except KeyError:
    st.error("❌ ERROR: The API key 'GEMINI_API_KEY' is missing from Streamlit secrets.")
    st.info("Please configure your secrets before running the application.")
    st.stop()

# --- SESSION STATE INITIALIZATION ---
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
    st.session_state.current_context = {"country": "", "sector": "", "focus": ""}

# --- AI CALL FUNCTION (WITH REAL-TIME WEB SEARCH) ---
def fetch_assessor_question(country, sector, focus):
    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        tools="google_search"
    )
    
    prompt = f"""
    You are a senior FATF assessor conducting an On-Site Visit based strictly on the FATF Methodology for assessing technical compliance and effectiveness.
    Evaluated Country: {country}.
    Sector: {sector}.
    Evaluation Focus: {focus}.

    CONTEXT AND OPERATIONAL RESEARCH (Google Search):
    1. Search the web for recent data, FIU annual reports, supervisory activity, sanctions, or press coverage related to AML/CFT for this sector in {country}.
    2. Extract concrete statistics (e.g., number of STRs filed, onsite inspections conducted, total fines issued) or specific typologies to use in your assessment.

    TASK:
    1. Select a specific FATF Recommendation (if Technical Compliance) or a specific Immediate Outcome and its underlying Core Issue (if Effectiveness).
    2. Generate an incisive question challenging the local authorities or professionals on that exact methodological point, using the real-world data you found to corner them.
    3. Provide 3 realistic response options (A, B, C) using public data constraints.
       - The correct option MUST demonstrate effectiveness (e.g., outcomes, mitigations, statistics) or technical compliance according to the FATF text.
       - The incorrect options should represent common failings (e.g., relying solely on legislation without implementation, or citing irrelevant data).

    RESPOND ONLY IN THE FOLLOWING JSON FORMAT (without any surrounding text, without ```json tags):
    {{
        "fatf_reference": "Explicit citation of the FATF standard used (e.g., 'Immediate Outcome 4, Core Issue 4.2' or 'Recommendation 10 - CDD').",
        "question": "The assessor's question, embedding the specific FATF requirement and the real-world vulnerability or data point you found.",
        "options": {{
            "A": "Full text for option A",
            "B": "Full text for option B",
            "C": "Full text for option C"
        }},
        "correct_option": "A", 
        "explanation": "Detailed explanation of why this option aligns best with the cited FATF methodology, explaining why the other postures fail the mutual evaluation standards.",
        "additional_data": "Specific numbers, statistics, or open-source intelligence (OSINT) facts found during your web search to back up the assessor's challenge."
    }}
    """
    
    try:
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        data = json.loads(response.text)
        return data
    except Exception as e:
        st.error(f"Generation error: {e}")
        return None

# --- HOME & DESIGN ---
st.title("🕵️‍♂️ FATF Assessor AI - Evaluation Simulator")
st.write("Defend the effectiveness of your supervisory framework against a FATF assessor utilizing real-time OSINT.")

# --- STEP 1: CONTEXT SETUP ---
if st.session_state.step == "setup":
    st.subheader("Simulation Setup")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        country = st.selectbox("Evaluated Country", ["Luxembourg", "France", "Switzerland", "Malta", "United Arab Emirates", "United Kingdom"])
    with col2:
        sector = st.selectbox("Supervisory Sector", ["Private Banking / Wealth Management", "Virtual Asset Service Providers (VASPs)", "Luxury Real Estate", "Trust and Company Service Providers (TCSPs)", "Gaming & Casino Sector"])
    with col3:
        focus = st.selectbox("Evaluation Focus (FATF)", ["Effectiveness (Immediate Outcomes 3 & 4)", "Technical Compliance (FATF Recommendations)"])

    if st.button("Start On-Site Interview 🚀"):
        with st.spinner("The assessor is consulting open sources and preparing their approach..."):
            st.session_state.current_context = {"country": country, "sector": sector, "focus": focus}
            
            question_data = fetch_assessor_question(country, sector, focus)
            if question_data:
                st.session_state.current_question = question_data
                st.session_state.step = "interview"
                st.session_state.user_choice = None
                st.rerun()

# --- STEP 2: THE INTERVIEW (QUESTION AND CHOICE) ---
elif st.session_state.step == "interview":
    q = st.session_state.current_question
    
    st.sidebar.metric("Compliance Score", f"{st.session_state.score}/{st.session_state.total_questions}")
    st.subheader("📍 Evaluation Session with the Assessor")
    st.caption(f"📘 **FATF Methodology Reference:** {q.get('fatf_reference', 'N/A')}")
    st.info(f"**FATF Assessor:** \n\n *\"{q['question']}\"*")
    st.write("---")
    st.write("**Choose your response strategy (based purely on public data):**")
    
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

# --- STEP 3: FEEDBACK AND RESEARCHED STATISTICS ---
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
        
    st.markdown(f"### 💡 FATF Analysis:\n{q['explanation']}")
    st.markdown("### 🌐 Real-time OSINT and statistical elements found:")
    st.warning(q['additional_data'])
    st.write("---")
    
    col_nav1, col_nav2 = st.columns(2)
    with col_nav1:
        if st.button("Next Assessor Question ➡️"):
            with st.spinner("The assessor pivots to another angle..."):
                ctx = st.session_state.current_context
                question_data = fetch_assessor_question(ctx['country'], ctx['sector'], ctx['focus'])
                
                if question_data:
                    st.session_state.current_question = question_data
                    st.session_state.step = "interview"
                    st.session_state.user_choice = None
                    st.rerun()
                    
    with col_nav2:
        if st.button("Modify Settings / Quit 🛑"):
            st.session_state.step = "setup"
            st.session_state.current_question = None
            st.session_state.score = 0
            st.session_state.total_questions = 0
            st.rerun()
