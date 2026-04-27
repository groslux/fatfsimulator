import streamlit as st
import google.generativeai as genai
import pycountry

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="FATF Simulator - One-Click Readiness", page_icon="⚖️", layout="wide")

# --- CUSTOM CSS ---
st.markdown("""
<style>
    .stButton>button { width: 100%; font-weight: bold; background-color: #0e1117; color: white; border: 1px solid #4a4a4a; }
    .stButton>button:hover { border-color: #ff4b4b; color: #ff4b4b; }
    .stChatMessage { border-radius: 10px; margin-bottom: 15px; }
</style>
""", unsafe_allow_html=True)

# --- COMPLETE FATF TAXONOMY ---
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

COMPLETE_SECTORS = [
    "Banks", 
    "Building Societies / Credit Unions",
    "Securities Broker-Dealers", 
    "Life Insurance Companies",
    "Money Value Transfer Services (MVTS)", 
    "Foreign Exchange / Currency Exchange",
    "Casinos (Physical, Internet, Ship-based)", 
    "Real Estate Agents",
    "Dealers in Precious Metals and Stones (DPMS)", 
    "Lawyers & Notaries",
    "Accountants", 
    "Trust & Company Service Providers (TCSPs)",
    "Virtual Asset Service Providers (VASPs)"
]

# Dynamically generate all global countries
ALL_COUNTRIES = sorted([country.name for country in pycountry.countries])

# --- AUTHENTICATION ---
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

# --- AI LOGIC ---
def generate_simulation(prompt):
    try:
        # Pulls the NEW API key from your secrets
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"API Error: Please ensure your API key is correctly placed in secrets.toml. Details: {str(e)}"

# --- MAIN APP ---
if check_password():
    st.title("🎮 FATF Mutual Evaluation Simulator")
    st.write("Select your parameters below and generate an on-site interview scenario in one click.")
    st.divider()

    # --- 1. CONFIGURATION BLOCK ---
    c1, c2, c3 = st.columns([1, 1, 2])
    with c1:
        # Default to a specific country if it exists, otherwise the first in the list
        default_idx = ALL_COUNTRIES.index("Luxembourg") if "Luxembourg" in ALL_COUNTRIES else 0
        selected_country = st.selectbox("Assessed Country", ALL_COUNTRIES, index=default_idx)
    with c2:
        selected_sector = st.selectbox("Targeted Sector", COMPLETE_SECTORS)
    with c3:
        selected_ios = st.multiselect("Immediate Outcome(s)", list(IO_TAXONOMY.keys()), default=["IO 3"])

    # --- 2. GENERATION TRIGGER ---
    if st.button("🚀 Launch FATF Interview Simulation"):
        if not selected_ios:
            st.error("Please select at least one Immediate Outcome.")
        else:
            with st.spinner("Connecting to Virtual Assessor and Advisor..."):
                io_descriptions = [f"{io} ({IO_TAXONOMY[io]})" for io in selected_ios]
                io_string = ", ".join(io_descriptions)

                # Prompt 1: The Assessor Challenge
                prompt_assessor = f"""
                You are a strict FATF assessor evaluating {selected_country}.
                The focus is the sector: '{selected_sector}' and the following Immediate Outcomes: {io_string}.
                Do a mental OSINT search on recent AML/CFT vulnerabilities for this sector in this country.
                Ask one highly specific, difficult 'On-site visit' question directed at the regulator (NCA).
                Demand proof of effectiveness (Outcomes), not just laws. Keep it under 4 sentences.
                """
                assessor_output = generate_simulation(prompt_assessor)

                # Prompt 2: The Strategic Advice
                prompt_advisor = f"""
                You are the NCA Strategic Advisor. The FATF assessor just asked the NCA this question: "{assessor_output}"
                Based on the FATF methodology for {io_string}, provide 3 bullet points on how to answer:
                1. What specific statistics/evidence to show.
                2. What outcome/effectiveness message to highlight.
                3. A defensive trap to avoid.
                Be direct and actionable. Do not invent confidential data.
                """
                advisor_output = generate_simulation(prompt_advisor)

                # Save to session state
                st.session_state.simulation_data = {
                    "assessor": assessor_output,
                    "advisor": advisor_output,
                    "context": f"{selected_country} | {selected_sector} | {', '.join(selected_ios)}"
                }

    # --- 3. RESULTS DISPLAY ---
    if "simulation_data" in st.session_state:
        st.divider()
        st.subheader(f"📌 Active Session: {st.session_state.simulation_data['context']}")
        
        with st.chat_message("user", avatar="🕵️"):
            st.markdown("**FATF ASSESSOR** (Lead Evaluator)")
            st.write(st.session_state.simulation_data["assessor"])
        
        with st.chat_message("assistant", avatar="💡"):
            st.markdown("**NCA STRATEGIC ADVISOR** (Your Internal Counsel)")
            st.write(st.session_state.simulation_data["advisor"])

        if st.button("Clear Session"):
            del st.session_state.simulation_data
            st.rerun()
