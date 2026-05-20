import streamlit as st
import google.generativeai as genai
import json

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="FATF Assessor AI - Mutual Evaluation Simulator",
    page_icon="🕵️‍♂️",
    layout="wide"
)

# --- GEMINI API INITIALIZATION ---
# Retrieve the API key from Streamlit secrets (in production) or via the sidebar input
api_key = st.sidebar.text_input("Google AI Studio (Gemini) API Key", type="password")

if api_key:
    genai.configure(api_key=api_key)
else:
    st.sidebar.warning("Please enter your Gemini API key to run the application.")

# --- SESSION STATE INITIALIZATION ---
if "step" not in st.session_state:
    st.session_state.step = "setup"  # Possible steps: setup, interview, feedback
if "current_question" not in st.session_state:
    st.session_state.current_question = None
if "score" not in st.session_state:
    st.session_state.score = 0
if "total_questions" not in st.session_state:
    st.session_state.total_questions = 0
if "user_choice" not in st.session_state:
    st.session_state.user_choice = None

# --- AI CALL FUNCTION (WITH REAL-TIME WEB SEARCH) ---
def fetch_assessor_question(country, sector, focus):
    if not api_key:
        return None
    
    # Model configuration with Web Search (Grounding) enabled
    # and forcing the output format to JSON
    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        tools="google_search"  # Enables real-time search (press, national reports, etc.)
    )
    
    prompt = f"""
    You are a senior FATF (Financial Action Task Force) assessor conducting an On-Site Visit in the following country: {country}.
    You are specifically evaluating the following sector: {sector}.
    Your current main focus is: {focus}.

    CONTEXT AND OPERATIONAL RESEARCH:
    1. Conduct a real-time web search on regulatory news, recent financial scandals, FIU (Financial Intelligence Unit) reports, supervisory sanctions, or national/international press articles related to Anti-Money Laundering and Counter-Terrorist Financing (AML/CFT) for this specific country and sector.
    2. Identify a concrete vulnerability or a frequent criticism regarding Effectiveness or Technical Compliance.

    TASK:
    Generate an incisive and challenging question that you would ask the local authorities or professionals on-site.
    Then, provide 3 realistic response options (A, B, C) based strictly on public data or typical institutional postures.
    - One of the options MUST be the "ideal" response from the assessor's perspective (it provides evidence of effectiveness, statistics, or demonstrates proactive risk management).
    - The other two MUST be insufficient (e.g., too focused on paper-based laws without proof of implementation, or too defensive).

    RESPOND ONLY IN THE FOLLOWING JSON FORMAT (without any surrounding text, without ```json tags):
    {{
        "question": "The text of your assessor question, mentioning a specific fact or methodological requirement...",
        "options": {{
            "A": "Full text for option A",
            "B": "Full text for option B",
            "C": "Full text for option C"
        }},
        "correct_option": "A", 
        "explanation": "Detailed explanation of why this option is the best according to FATF effectiveness criteria.",
        "additional_data": "Real statistical data or complementary OSINT elements found during your web search for this country to enrich the answer."
    }}
    """
    
    try:
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        # Clean and parse the JSON
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

    if st.button("Start On-Site Interview 🚀", disabled=not api_key):
        with st.spinner("The assessor is consulting open sources and preparing their approach..."):
            question_data = fetch_assessor_question(country, sector, focus)
            if question_data:
                st.session_state.current_question = question_data
                st.session_state.step = "interview"
                st.session_state.user_choice = None
                st.rerun()

# --- STEP 2: THE INTERVIEW (QUESTION AND CHOICE) ---
elif st.session_state.step == "interview":
    q = st.session_state.current_question
    
    # Display the score at the top of the sidebar
    st.sidebar.metric("Compliance Score", f"{st.session_state.score}/{st.session_state.total_questions}")
    
    st.subheader("📍 Evaluation Session with the Assessor")
    
    # Assessor's dialogue box
    st.info(f"**FATF Assessor:** \n\n *\"{q['question']}\"*")
    
    st.write("---")
    st.write("**Choose your response strategy (based purely on public data):**")
    
    # Form to prevent unwanted reloads when clicking a radio button
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
    
    # Key Section: Injecting real data gathered from the Web by the AI
    st.markdown("### 🌐 Real-time OSINT and statistical elements found:")
    st.warning(q['additional_data'])
    
    st.write("---")
    
    col_nav1, col_nav2 = st.columns(2)
    with col_nav1:
        if st.button("Next Assessor Question ➡️"):
            with st.spinner("The assessor pivots to another angle..."):
                # Simulating continuity by running a new search with the same context
                question_data = fetch_assessor_question(
                    st.session_state.current_question.get('country', 'Luxembourg'),
                    st.session_state.current_question.get('sector', 'Private Banking'),
                    st.session_state.current_question.get('focus', 'Effectiveness')
                )
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
