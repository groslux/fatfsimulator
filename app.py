import streamlit as st
import google.generativeai as genai

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="FATF Simulator - NCA Readiness", page_icon="⚖️", layout="wide")

# --- CUSTOM CSS ---
st.markdown("""
<style>
    .reportview-container { background: #f0f2f6; }
    .stChatMessage { border-radius: 15px; margin-bottom: 10px; }
</style>
""", unsafe_allow_html=True)

# --- FATF OFFICIAL TAXONOMY ---
IO_TAXONOMY = {
    "IO 1": "Risk, Policy and Coordination",
    "IO 2": "International Cooperation",
    "IO 3": "Supervision",
    "IO 4": "Preventive Measures",
    "IO 5": "Legal Persons and Arrangements",
    "IO 6": "Financial Intelligence",
    "IO 7": "ML Investigation and Prosecution",
    "IO 8": "Confiscation",
    "IO 9": "TF Investigation and Prosecution",
    "IO 10": "TF Preventive Measures and Financial Sanctions",
    "IO 11": "PF Financial Sanctions"
}

SECTOR_TAXONOMY = [
    "Banks", "Money Value Transfer Services (MVTS)", "VASPs (Crypto-assets)", 
    "Life Insurance", "Casinos & Gambling", "Real Estate Agents", 
    "Dealers in Precious Metals and Stones (DPMS)", "Lawyers & Notaries", 
    "Trust & Company Service Providers (TCSPs)", "Accountants"
]

# --- AUTHENTICATION SYSTEM ---
def check_password():
    if "auth" not in st.session_state:
        st.session_state["auth"] = False
    
    if not st.session_state["auth"]:
        st.title("🛡️ FATF Simulator - Secure Access")
        with st.form("login_form"):
            pwd = st.text_input("NCA Network Password", type="password")
            if st.form_submit_button("Login"):
                if pwd == "AMLNetwork":
                    st.session_state["auth"] = True
                    st.rerun()
                else:
                    st.error("Access denied. Incorrect password.")
        return False
    return True

# --- AI SIMULATION LOGIC ---
def get_simulation_response(prompt):
    try:
        # Retrieve the API key from Streamlit secrets
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        
        # Using the standard, stable model name
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        # If flash fails, fallback to the older stable pro model automatically
        try:
            fallback_model = genai.GenerativeModel('gemini-pro')
            response = fallback_model.generate_content(prompt)
            return response.text
        except Exception as fallback_error:
            return f"Connection error with the virtual assessor. Primary error: {str(e)}. Fallback error: {str(fallback_error)}"

# --- MAIN INTERFACE ---
if check_password():
    st.sidebar.title("🎮 FATF Simulator v1.0")
    st.sidebar.markdown("---")
    
    app_mode = st.sidebar.selectbox("Select Module", ["Configuration", "Active Simulation", "Methodology Guide"])

    if app_mode == "Configuration":
        st.header("🎯 Mutual Evaluation Preparation")
        st.write("Configure the inspection scenario. The AI will generate a challenge based on OSINT and the FATF methodology.")
        
        with st.container():
            col1, col2 = st.columns(2)
            with col1:
                country = st.selectbox("Assessed Country", ["Luxembourg", "France", "United Kingdom", "Singapore", "United States", "UAE"])
                sector = st.selectbox("Targeted Sector", SECTOR_TAXONOMY)
            with col2:
                io_key = st.selectbox("Immediate Outcome (IO)", list(IO_TAXONOMY.keys()))
                io_desc = IO_TAXONOMY[io_key]
                st.info(f"**Focus:** {io_desc}")

        if st.button("🚀 Start Assessor Interview"):
            st.session_state.current_scenario = {
                "country": country,
                "sector": sector,
                "io": io_key,
                "io_desc": io_desc
            }
            
            # Prompt for the Assessor (The Challenger)
            prompt_assessor = f"""
            You are a strict and rigorous FATF assessor. You are evaluating the country {country} on {io_key} ({io_desc}).
            Your focus is the following sector: {sector}.
            Conduct a mental OSINT search regarding recent AML/CFT risks, scandals, or typologies in this country for this sector.
            Ask a very precise, technical, and slightly challenging 'On-site visit' question to the NCA representative. 
            Demand evidence of effectiveness (statistics, examples of enforcement), not just legislative framework.
            Keep your answer short (maximum 4 sentences) and direct.
            """
            st.session_state.assessor_q = get_simulation_response(prompt_assessor)
            
            # Prompt for the Advisor (The Strategist)
            prompt_advisor = f"""
            You are the strategic advisor for the National Competent Authority (NCA). The FATF assessor just asked this question: '{st.session_state.assessor_q}'.
            Analyze the question strictly through the lens of the FATF methodology for {io_key}. 
            Provide 3 tactical tips on how the NCA representative should answer:
            1. What specific statistical data or evidence should they prepare?
            2. What key message should they deliver to demonstrate 'effectiveness' (Outcomes)?
            3. What trap or defensive stance should they avoid in their response?
            Do not provide or ask for actual confidential information. Be professional and actionable.
            """
            st.session_state.advisor_tips = get_simulation_response(prompt_advisor)
            
            st.session_state.step = "active"
            st.rerun()

    elif app_mode == "Active Simulation":
        if "current_scenario" not in st.session_state:
            st.warning("Please configure a scenario first in the 'Configuration' tab.")
        else:
            scen = st.session_state.current_scenario
            st.subheader(f"Session: {scen['country']} | {scen['io']} | {scen['sector']}")
            
            # Display Assessor Output
            with st.chat_message("user", avatar="🕵️"):
                st.markdown("**FATF ASSESSOR** (Lead Evaluator)")
                st.write(st.session_state.assessor_q)
            
            st.markdown("---")
            
            # Display Advisor Output
            with st.chat_message("assistant", avatar="💡"):
                st.markdown("**NCA ADVISOR** (Strategic Counsel)")
                st.write(st.session_state.advisor_tips)
                
            if st.button("🔄 Generate Next Question"):
                del st.session_state.current_scenario
                st.rerun()

    elif app_mode == "Methodology Guide":
        st.header("📚 Methodology Reference")
        selected_io = st.selectbox("Consult an Immediate Outcome", list(IO_TAXONOMY.keys()))
        st.write(f"### {selected_io} : {IO_TAXONOMY[selected_io]}")
        st.info("According to the FATF Methodology, this IO evaluates whether the system is achieving the expected results (Outcomes). Effectiveness is measured by concrete results, not just technical compliance (laws on the books).")

# --- FOOTER ---
st.sidebar.markdown("---")
st.sidebar.caption("Sovereign Readiness Tool - FATF Simulator v1.0")
