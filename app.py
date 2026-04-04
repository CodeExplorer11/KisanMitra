import streamlit as st
import requests
import google.generativeai as genai
import os
from dotenv import load_dotenv
import io
import speech_recognition as sr
from PIL import Image
import datetime

# ========== LOAD API KEYS ==========
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")
MANDI_API_KEY = os.getenv("MANDI_API_KEY")

# ========== CONFIGURE GEMINI ==========
if not GEMINI_API_KEY:
    st.error("❌ Gemini API key missing. Add it to Secrets.")
    st.stop()
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-pro')
vision_model = genai.GenerativeModel('gemini-pro-vision')

# ========== PAGE CONFIG ==========
st.set_page_config(page_title="KisanMitra", page_icon="🌾", layout="wide")

# ========== CUSTOM CSS ==========
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
        return f"⚠️ Error: {str(e)}"

def get_weather(city):
    if not WEATHER_API_KEY:
        return {"error": "Weather API key missing"}
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_API_KEY}&units=metric"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            return {
                "temp": data['main']['temp'],
                "humidity": data['main']['humidity'],
                "description": data['weather'][0]['description'],
                "city": data['name']
            }
        else:
            return {"error": f"City not found: {city}"}
    except:
        return {"error": "Network error"}

def get_mandi_price(commodity, state="Uttar Pradesh"):
    if not MANDI_API_KEY:
        # Fallback mock data (still looks professional)
        mock_prices = {
            "wheat": 2250, "rice": 2180, "mustard": 5650, "tomato": 1800, "potato": 1200
        }
        price = mock_prices.get(commodity.lower(), 2000)
        return {"commodity": commodity, "price": price, "market": "Local Mandi", "state": state, "source": "Estimated (API key missing)"}
    # Real API call (you need to find the correct resource ID)
    resource_id = "9ef84268-d588-465a-a308-a864a43d0070"
    url = f"https://api.data.gov.in/resource/{resource_id}?api-key={MANDI_API_KEY}&format=json&limit=10"
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
        records = data.get('records', [])
        for rec in records:
            if commodity.lower() in rec.get('commodity', '').lower():
                return {"commodity": rec['commodity'], "price": rec.get('modal_price', 'N/A'), "market": rec.get('market', 'N/A'), "state": rec.get('state', 'N/A'), "source": "Live"}
        return {"error": f"No data for {commodity}"}
    except:
        return {"error": "API request failed"}

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

# ----- TAB 2: MARKET PRICES (REAL-TIME) -----
with tab2:
    st.header("💰 Real-Time Mandi Prices")
    col1, col2 = st.columns(2)
    with col1:
        commodity = st.text_input("Commodity (e.g., Wheat, Rice, Tomato)")
    with col2:
        state = st.text_input("State", "Uttar Pradesh")
    if st.button("Get Live Price"):
        if commodity:
            with st.spinner("Fetching from data.gov.in..."):
                price_info = get_mandi_price(commodity, state)
            if "error" in price_info:
                st.error(price_info["error"])
            else:
                st.success(f"**{price_info['commodity']}** in {price_info.get('market', 'mandi')}, {price_info['state']}")
                st.metric("Price per quintal", f"₹{price_info['price']}")
                st.caption(f"Source: {price_info.get('source', 'Live data')}")
        else:
            st.warning("Enter a commodity name.")

# ----- TAB 3: WEATHER (REAL-TIME) -----
with tab3:
    st.header("🌤️ Real-Time Weather")
    city = st.text_input("Enter district/city name", "Lucknow")
    if st.button("Get Weather"):
        with st.spinner("Fetching from OpenWeatherMap..."):
            w = get_weather(city)
        if "error" in w:
            st.error(w["error"])
        else:
            col1, col2, col3 = st.columns(3)
            col1.metric("Temperature", f"{w['temp']}°C")
            col2.metric("Humidity", f"{w['humidity']}%")
            col3.metric("Condition", w['description'].title())
            st.info(f"📍 {w['city']} | Last updated: {datetime.datetime.now().strftime('%H:%M:%S')}")

# ----- TAB 4: SOIL HEALTH -----
with tab4:
    st.header("🧪 Soil Health Analysis")
    soil_input = st.text_area("Enter soil test results (e.g., pH: 7.2, Nitrogen: 250 kg/ha, Phosphorus: 30 kg/ha, Potassium: 120 kg/ha)")
    if st.button("Get Soil Advice"):
        if soil_input:
            with st.spinner("Analyzing with AI..."):
                advice = get_soil_advice(soil_input)
            st.success("🌱 Soil Health Recommendation")
            st.markdown(f'<div class="bot-msg">📋 {advice}</div>', unsafe_allow_html=True)
        else:
            st.warning("Please enter soil data.")

# ----- TAB 5: PERSONALIZED ADVICE -----
with tab5:
    st.header("📝 Personalized Farming Advice")
    if not st.session_state.farmer_profile:
        st.warning("Please fill your Farmer Profile in the sidebar first.")
    else:
        question = st.text_area("What specific advice do you need? (e.g., best sowing time, pest control, fertilizer schedule)")
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