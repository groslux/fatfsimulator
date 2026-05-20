import streamlit as st
import google.generativeai as genai
import json

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(
    page_title="GAFI Assessor AI - Simulateur d'Évaluation Mutuelle",
    page_icon="🕵️‍♂️",
    layout="wide"
)

# --- INITIALISATION DE L'API GEMINI ---
# On récupère la clé API soit depuis les secrets de Streamlit (production), soit graphiquement
api_key = st.sidebar.text_input("Clé API Google AI Studio (Gemini)", type="password")

if api_key:
    genai.configure(api_key=api_key)
else:
    st.sidebar.warning("Veuillez saisir votre clé API Gemini pour faire fonctionner l'application.")

# --- INITIALISATION DES ÉTATS DE SESSION ---
if "step" not in st.session_state:
    st.session_state.step = "setup"  # Éapes possibles : setup, interview, feedback
if "current_question" not in st.session_state:
    st.session_state.current_question = None
if "score" not in st.session_state:
    st.session_state.score = 0
if "total_questions" not in st.session_state:
    st.session_state.total_questions = 0
if "user_choice" not in st.session_state:
    st.session_state.user_choice = None

# --- FONCTION D'APPEL À L'IA (AVEC RECHERCHE WEB EN TEMPS RÉEL) ---
def fetch_assessor_question(country, sector, focus):
    if not api_key:
        return None
    
    # Configuration du modèle avec Recherche Web activée (Grounding)
    # et forçage du format de sortie en JSON
    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        tools="google_search"  # Active la recherche en temps réel (presse, rapports nationaux...)
    )
    
    prompt = f"""
    Tu es un évaluateur (assessor) senior du GAFI lors d'une visite sur place (On-Site Visit) dans le pays suivant : {country}.
    Tu évalues spécifiquement le secteur suivant : {sector}.
    Ton focus principal actuel est : {focus}.

    CONTEXTE ET RECHERCHE OPÉRATIONNELLE :
    1. Fais une recherche en ligne en temps réel sur l'actualité réglementaire, les récents scandales financiers, les rapports de la CRF (Renseignement financier), les sanctions du superviseur ou les articles de presse nationale/internationale liés au blanchiment d'argent (BC/FT) pour ce pays et ce secteur spécifique.
    2. Identifie une vulnérabilité concrète ou une critique fréquente concernant l'efficacité (Effectiveness) ou la conformité technique (Technical Compliance).

    TACHE :
    Génère une question incisive et challengeante que tu poserais aux autorités ou aux professionnels sur place.
    Propose ensuite 3 options de réponses réalistes (A, B, C) basées uniquement sur des données publiques ou des postures institutionnelles types.
    - L'une des options doit être la réponse "idéale" du point de vue de l'évaluateur (elle apporte des preuves d'efficacité, des statistiques ou démontre une gestion du risque proactive).
    - Les deux autres doivent être insuffisantes (ex: trop axées sur la loi papier sans preuve d'application, ou trop défensives).

    RÉPONDRE UNIQUEMENT SOUS LE FORMAT JSON SUIVANT (sans aucun autre texte autour, sans balise ```json) :
    {{
        "question": "Le texte de ta question d'évaluateur, mentionnant un fait ou une exigence méthodologique précise...",
        "options": {{
            "A": "Texte complet de l'option A",
            "B": "Texte complet de l'option B",
            "C": "Texte complet de l'option C"
        }},
        "correct_option": "A", 
        "explanation": "L'explication détaillée de pourquoi cette option est la meilleure selon les critères d'efficacité du GAFI.",
        "additional_data": "Données statistiques réelles ou éléments OSINT complémentaires trouvés lors de ta recherche sur le web pour ce pays pour enrichir la réponse."
    }}
    """
    
    try:
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        # Nettoyage et parsing du JSON
        data = json.loads(response.text)
        return data
    except Exception as e:
        st.error(f"Erreur lors de la génération : {e}")
        return None

# --- ACCUEIL ET DESIGN ---
st.title("🕵️‍♂️ GAFI Assessor AI - Simulateur d'Évaluation")
st.write("Défendez l'efficacité de votre dispositif de supervision face à un évaluateur du GAFI utilisant l'OSINT en temps réel.")

# --- ÉTAPE 1 : CONFIGURATION DU CONTEXTE ---
if st.session_state.step == "setup":
    st.subheader("Configuration de la Simulation")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        country = st.selectbox("Pays évalué", ["Luxembourg", "France", "Suisse", "Malte", "Émirats Arabes Unis", "Royaume-Uni"])
    with col2:
        sector = st.selectbox("Secteur de Supervision", ["Banques Privées / Gestion de Fortune", "Prestataires de Services d'Actifs Numériques (PSAN)", "Immobilier de Luxe", "Fiduciaires / TCSP", "Secteur des Jeux & Casinos"])
    with col3:
        focus = st.selectbox("Objectif d'Évaluation (GAFI)", ["Effectiveness - Efficacité Réelle (Immediate Outcomes 3 & 4)", "Technical Compliance - Arsenal Législatif (Recommandations du GAFI)"])

    if st.button("Démarrer l'Entretien On-Site 🚀", disabled=not api_key):
        with st.spinner("L'évaluateur consulte les sources ouvertes et prépare son attaque..."):
            question_data = fetch_assessor_question(country, sector, focus)
            if question_data:
                st.session_state.current_question = question_data
                st.session_state.step = "interview"
                st.session_state.user_choice = None
                st.rerun()

# --- ÉTAPE 2 : L'ENTRETIEN (LA QUESTION ET LE CHOIX) ---
elif st.session_state.step == "interview":
    q = st.session_state.current_question
    
    # Affichage du score en haut
    st.sidebar.metric("Score de Conformité", f"{st.session_state.score}/{st.session_state.total_questions}")
    
    st.subheader("📍 Session d'évaluation face à l'Assessor")
    
    # Boîte de dialogue de l'évaluateur
    st.info(f"**Évaluateur du GAFI :** \n\n *\"{q['question']}\"*")
    
    st.write("---")
    st.write("**Choisissez votre stratégie de réponse (uniquement basée sur des données publiques) :**")
    
    # Formulaire pour éviter les rechargements intempestifs lors du clic sur un radio bouton
    with st.form(key="qcm_form"):
        options_formates = {
            f"A: {q['options']['A']}": "A",
            f"B: {q['options']['B']}": "B",
            f"C: {q['options']['C']}": "C"
        }
        choix = st.radio("Options :", list(options_formates.keys()), index=0)
        submit_button = st.form_submit_state = st.form_submit_button(label="Soumettre la réponse officielle 📝")
        
        if submit_button:
            st.session_state.user_choice = options_formates[choix]
            st.session_state.step = "feedback"
            st.session_state.total_questions += 1
            if st.session_state.user_choice == q['correct_option']:
                st.session_state.score += 1
            st.rerun()

# --- ÉTAPE 3 : LE FEEDBACK ET LES STATISTIQUES RECHERCHÉES ---
elif st.session_state.step == "feedback":
    q = st.session_state.current_question
    choix_utilisateur = st.session_state.user_choice
    est_correct = choix_utilisateur == q['correct_option']
    
    st.sidebar.metric("Score de Conformité", f"{st.session_state.score}/{st.session_state.total_questions}")
    
    st.subheader("📊 Débriefing de l'Évaluateur")
    
    if est_correct:
        st.success(f"✅ **Bonne Posture !** Vous avez choisi l'Option {choix_utilisateur}.")
    else:
        st.error(f"❌ **Posture Fragile.** Vous avez choisi l'Option {choix_utilisateur}. L'option attendue était la **{q['correct_option']}**.")
        
    st.markdown(f"### 💡 Analyse du GAFI :\n{q['explanation']}")
    
    # Section Clé : Injection des données réelles glanées sur le Web par l'IA
    st.markdown("### 🌐 Éléments statistiques et OSINT trouvés en temps réel :")
    st.warning(q['additional_data'])
    
    st.write("---")
    
    col_nav1, col_nav2 = st.columns(2)
    with col_nav1:
        if st.button("Prochaine Question de l'Assessor ➡️"):
            with st.spinner("L'évaluateur rebondit sur un autre angle..."):
                # On simule la continuité en relançant une recherche avec le même contexte
                # Dans une version avancée, on pourrait passer l'historique au prompt
                question_data = fetch_assessor_question(
                    st.session_state.current_question.get('country', 'Luxembourg'),
                    st.session_state.current_question.get('sector', 'Banques Privées'),
                    st.session_state.current_question.get('focus', 'Effectiveness')
                )
                if question_data:
                    st.session_state.current_question = question_data
                    st.session_state.step = "interview"
                    st.session_state.user_choice = None
                    st.rerun()
                    
    with col_nav2:
        if st.button("Modifier les paramètres / Quitter 🛑"):
            st.session_state.step = "setup"
            st.session_state.current_question = None
            st.session_state.score = 0
            st.session_state.total_questions = 0
            st.rerun()
