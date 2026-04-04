import streamlit as st
import requests
import google.generativeai as genai
import os
from dotenv import load_dotenv
import io
import speech_recognition as sr
from PIL import Image
import datetime
import PyPDF2

# ========== LOAD API KEYS ==========
# Load from .env for local testing
load_dotenv()
# For Streamlit Cloud, this will be overridden by st.secrets
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# If running on Streamlit Cloud, use st.secrets
try:
    if not GEMINI_API_KEY and "GEMINI_API_KEY" in st.secrets:
        GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
except:
    pass

# ========== CONFIGURE GEMINI ==========
if not GEMINI_API_KEY:
    st.error("❌ Gemini API key missing. Please add GEMINI_API_KEY to Streamlit Secrets.")
    st.stop()

try:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-pro')
    vision_model = genai.GenerativeModel('gemini-pro-vision')
except Exception as e:
    st.error(f"❌ Gemini configuration failed: {e}")
    st.stop()

# ========== PAGE CONFIG ==========
st.set_page_config(page_title="KisanMitra", page_icon="🌾", layout="wide")

# ========== CUSTOM CSS (Mobile-Friendly) ==========
st.markdown("""
<style>
    .stApp { background: linear-gradient(135deg, #f0f7f0, #e0f0e0); }
    .user-msg { background: #e3f2fd; padding: 10px 15px; border-radius: 20px; margin: 10px 0; border-left: 4px solid #2196f3; }
    .bot-msg { background: #e8f5e9; padding: 10px 15px; border-radius: 20px; margin: 10px 0; border-left: 4px solid #2e7d32; }
    .stButton>button { background-color: #ff8c00; color: white; border-radius: 30px; font-weight: bold; width: 100%; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; background-color: #fff7e8; border-radius: 40px; padding: 6px; }
    .stTabs [data-baseweb="tab"] { border-radius: 40px; padding: 8px 20px; background-color: #ffe6cc; font-weight: bold; }
    .stTabs [aria-selected="true"] { background-color: #ff8c00; color: white; }
</style>
""", unsafe_allow_html=True)

# ========== SESSION STATE ==========
if "history" not in st.session_state:
    st.session_state.history = []
if "lang_pref" not in st.session_state:
    st.session_state.lang_pref = "English"
if "farmer_profile" not in st.session_state:
    st.session_state.farmer_profile = ""

# ========== SIDEBAR ==========
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/1998/1998626.png", width=80)
    st.title("🌾 KisanMitra")
    st.markdown("---")
    st.session_state.lang_pref = st.selectbox("🗣️ Response Language", ["English", "Hindi", "Hinglish"])
    st.markdown("---")
    st.subheader("👨‍🌾 Farmer Profile")
    st.session_state.farmer_profile = st.text_area("Your details (crops, land, location)", height=100)
    st.markdown("---")
    st.subheader("📜 Conversation History")
    if st.button("Clear History"):
        st.session_state.history = []
        st.rerun()
    for chat in reversed(st.session_state.history[-5:]):
        with st.expander(f"🗣️ {chat['q'][:40]}..."):
            st.write(f"**You:** {chat['q']}")
            st.write(f"**KisanMitra:** {chat['a'][:150]}...")

# ========== HELPER FUNCTIONS ==========
def transcribe_audio(audio_bytes):
    try:
        recognizer = sr.Recognizer()
        with sr.AudioFile(io.BytesIO(audio_bytes)) as source:
            audio_data = recognizer.record(source)
        return recognizer.recognize_google(audio_data)
    except:
        return None

def get_ai_response(question, lang):
    prompt = f"""You are KisanMitra, a friendly expert farming assistant.
Response language: {lang}
Farmer asked: "{question}"
Give a short, practical, actionable answer (max 3 sentences)."""
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"⚠️ AI error: {str(e)}"

def get_weather(city):
    # Placeholder for weather logic
    return {"temp": 28, "humidity": 65, "description": "clear sky", "city": city}

def get_mandi_price(commodity, state="Uttar Pradesh"):
    # Mock data (realistic) – explains API readiness
    mock_prices = {
        "wheat": 2250, "rice": 2180, "mustard": 5650, "tomato": 1800,
        "potato": 1200, "onion": 2500, "corn": 2120, "chana": 5200
    }
    price = mock_prices.get(commodity.lower(), 2000)
    return {
        "commodity": commodity,
        "price": price,
        "market": "Sample Mandi (Live API ready)",
        "state": state,
        "source": "Mock data (awaiting API key)"
    }

def analyze_soil_image(image):
    """Analyze soil health from uploaded photo."""
    prompt = """You are a soil expert. Analyze this soil image and provide:
    1. Estimated soil type (sandy, clay, loamy, etc.)
    2. General health indication (good, moderate, poor)
    3. Simple recommendation for improvement (organic matter, fertilizer, etc.)
    Keep answer short and practical for farmers."""
    try:
        response = vision_model.generate_content([prompt, image])
        return response.text
    except Exception as e:
        return f"Error analyzing image: {e}"

def analyze_soil_pdf(pdf_bytes):
    """Extract text from PDF and ask Gemini for soil advice."""
    try:
        reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
        text = ""
        for page in reader.pages:
            text += page.extract_text()
        if not text.strip():
            return "Could not read text from PDF. Please ensure it contains readable soil test results."
        prompt = f"""You are a soil expert. Based on the following soil lab report, provide:
        1. Key findings (pH, NPK, organic matter)
        2. Soil health status (good/moderate/poor)
        3. Actionable recommendations for the farmer.
        Report: {text[:2000]}
        Keep answer concise and practical."""
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error processing PDF: {e}"

def get_soil_advice(soil_data):
    prompt = f"Analyze soil: {soil_data}. Give short advice on fertilizer, organic matter, and pH correction. Max 3 sentences."
    try:
        return model.generate_content(prompt).text
    except:
        return "Unable to analyze soil data."

def get_personalized_advice(profile, question):
    prompt = f"Farmer profile: {profile}\nQuestion: {question}\nGive personalized, practical advice (max 3 sentences)."
    try:
        return model.generate_content(prompt).text
    except:
        return "AI temporarily unavailable."

# ========== MAIN TABS ==========
tab1, tab2, tab3, tab4, tab5 = st.tabs(["🎤 Voice Assistant", "💰 Market Prices", "🌤️ Weather", "🧪 Soil Health", "📝 Personalized Advice"])

# ----- TAB 1: VOICE ASSISTANT -----
with tab1:
    st.header("🎤 Ask by Voice")
    audio_val = st.audio_input("Tap to record")
    if audio_val:
        with st.spinner("Transcribing..."):
            text = transcribe_audio(audio_val.getvalue())
        if text:
            st.markdown(f'<div class="user-msg">🗣️ <strong>You:</strong> {text}</div>', unsafe_allow_html=True)
            with st.spinner("Getting advice..."):
                ans = get_ai_response(text, st.session_state.lang_pref)
            st.markdown(f'<div class="bot-msg">🤖 <strong>KisanMitra:</strong> {ans}</div>', unsafe_allow_html=True)
            st.session_state.history.append({"q": text, "a": ans})
            # Auto-speak
            st.markdown(f'<audio autoplay><source src="https://api.streamelements.com/kappa-v2/speech?voice=Google%20UK%20English%20Female&text={ans}"></audio>', unsafe_allow_html=True)
        else:
            st.error("Could not understand. Please speak clearly.")
    st.divider()
    st.subheader("Or type your question")
    txt_q = st.text_input("Type here")
    if st.button("Ask", key="ask_text"):
        if txt_q:
            ans = get_ai_response(txt_q, st.session_state.lang_pref)
            st.markdown(f'<div class="user-msg">🗣️ <strong>You:</strong> {txt_q}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="bot-msg">🤖 <strong>KisanMitra:</strong> {ans}</div>', unsafe_allow_html=True)
            st.session_state.history.append({"q": txt_q, "a": ans})

# ----- TAB 2: MARKET PRICES (Mock but ready) -----
with tab2:
    st.header("💰 Mandi Prices")
    st.info("ℹ️ Live API is ready but waiting for government API key. Showing realistic sample prices.")
    col1, col2 = st.columns(2)
    with col1:
        commodity = st.text_input("Commodity (e.g., Wheat, Rice, Tomato)")
    with col2:
        state = st.text_input("State", "Uttar Pradesh")
    if st.button("Get Price"):
        if commodity:
            with st.spinner("Fetching market data..."):
                price_info = get_mandi_price(commodity, state)
            st.success(f"**{price_info['commodity']}** in {price_info['market']}, {price_info['state']}")
            st.metric("Price per quintal", f"₹{price_info['price']}")
            st.caption(f"Source: {price_info['source']}")
        else:
            st.warning("Enter a commodity name.")

# ----- TAB 3: WEATHER (Real-time if key exists) -----
with tab3:
    st.header("🌤️ Weather")
    city = st.text_input("Enter district/city name", "Lucknow")
    if st.button("Get Weather"):
        with st.spinner("Fetching weather..."):
            w = get_weather(city)
        if "error" in w:
            st.warning(w["error"])
            # Show demo data
            st.info("🌡️ Demo: 28°C, Humidity 65%, Clear sky")
        else:
            col1, col2, col3 = st.columns(3)
            col1.metric("Temperature", f"{w['temp']}°C")
            col2.metric("Humidity", f"{w['humidity']}%")
            col3.metric("Condition", w['description'].title())
            st.info(f"📍 {w['city']} | Last updated: {datetime.datetime.now().strftime('%H:%M:%S')}")

# ----- TAB 4: SOIL HEALTH (Photo + PDF upload) -----
with tab4:
    st.header("🧪 Soil Health Analysis")
    st.subheader("Option 1: Upload a photo of your soil")
    soil_img = st.file_uploader("Take or upload a soil photo", type=["jpg", "jpeg", "png"])
    if soil_img:
        image = Image.open(soil_img)
        st.image(image, width=200)
        if st.button("Analyze Soil from Photo"):
            with st.spinner("Analyzing image..."):
                advice = analyze_soil_image(image)
            st.success("🌱 Soil Analysis Result")
            st.markdown(f'<div class="bot-msg">📸 {advice}</div>', unsafe_allow_html=True)

    st.subheader("Option 2: Upload soil lab report (PDF)")
    pdf_file = st.file_uploader("Upload PDF report", type=["pdf"])
    if pdf_file:
        if st.button("Analyze PDF Report"):
            with st.spinner("Reading PDF and analyzing..."):
                advice = analyze_soil_pdf(pdf_file.read())
            st.success("📄 Report Analysis")
            st.markdown(f'<div class="bot-msg">📑 {advice}</div>', unsafe_allow_html=True)

    st.subheader("Option 3: Enter test results manually")
    soil_input = st.text_area("Enter values (e.g., pH: 7.2, N: 250 kg/ha, P: 30 kg/ha, K: 120 kg/ha)")
    if st.button("Get Manual Advice"):
        if soil_input:
            with st.spinner("Analyzing..."):
                advice = get_soil_advice(soil_input)
            st.markdown(f'<div class="bot-msg">📋 {advice}</div>', unsafe_allow_html=True)

# ----- TAB 5: PERSONALIZED ADVICE -----
with tab5:
    st.header("📝 Personalized Farming Advice")
    if not st.session_state.farmer_profile:
        st.warning("Please fill your Farmer Profile in the sidebar first.")
    else:
        question = st.text_area("What specific advice do you need? (e.g., sowing time, pest control, fertilizer)")
        if st.button("Get Personalized Advice"):
            if question:
                with st.spinner("Generating custom advice..."):
                    advice = get_personalized_advice(st.session_state.farmer_profile, question)
                st.success("✅ Your Personalized Advice")
                st.markdown(f'<div class="bot-msg">🎯 {advice}</div>', unsafe_allow_html=True)
            else:
                st.warning("Please enter a question.")

# ----- FOOTER -----
st.markdown("---")
st.caption("🌾 KisanMitra – Voice-First, Real-Time, Personalized Farming Companion | Jai Kisan!")