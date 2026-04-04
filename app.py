import streamlit as st
import requests
import google.generativeai as genai
import io
import speech_recognition as sr
from PIL import Image
import datetime
import PyPDF2

# ========== PAGE CONFIG (MUST BE FIRST) ==========
st.set_page_config(page_title="KisanMitra", page_icon="🌾", layout="wide")

# ========== LOAD API KEYS ==========
GEMINI_API_KEY = None

# Method 1: Streamlit Cloud Secrets
try:
    if "GEMINI_API_KEY" in st.secrets:
        GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
        st.success("✅ API key loaded from Streamlit Secrets")
except:
    pass

# Method 2: Environment variable (local testing)
if not GEMINI_API_KEY:
    try:
        from dotenv import load_dotenv
        import os
        load_dotenv()
        GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
        if GEMINI_API_KEY:
            st.info("📝 API key loaded from .env file")
    except:
        pass

# ========== VALIDATE API KEY ==========
if not GEMINI_API_KEY:
    st.error("❌ Gemini API key missing. Please add GEMINI_API_KEY to Streamlit Secrets.")
    st.stop()

# Clean the key
GEMINI_API_KEY = GEMINI_API_KEY.strip().strip('"').strip("'")

# ========== CONFIGURE GEMINI (UPDATED MODEL NAMES) ==========
try:
    genai.configure(api_key=GEMINI_API_KEY)
    
    # List available models to verify (optional, for debugging)
    # for m in genai.list_models():
    #     if 'generateContent' in m.supported_generation_methods:
    #         st.write(m.name)
    
    # Use the correct model names (updated from gemini-pro)
    model = genai.GenerativeModel('gemini-2.0-flash')
    vision_model = genai.GenerativeModel('gemini-2.0-flash')
    
    # Test the API key with a simple call
    test_response = model.generate_content("Say 'API key works'")
    
    if test_response and test_response.text:
        st.success("✅ Gemini API connected successfully!")
    else:
        st.error("❌ API key validation failed.")
        st.stop()
        
except Exception as e:
    st.error(f"❌ Gemini configuration failed: {e}")
    st.info("💡 Make sure your API key is correct and has no extra spaces.")
    st.stop()

# ========== MULTILINGUAL SUPPORT ==========
SUPPORTED_LANGS = {
    "en": "English",
    "hi": "हिंदी",
}

DEFAULT_LANGUAGE = "en"

TEXTS = {
    "en": {
        "app_title": "🌾 KisanMitra",
        "app_caption": "Your Voice Farming Companion",
        "sidebar_title": "🌾 KisanMitra",
        "sidebar_lang": "🗣️ Response Language",
        "sidebar_profile": "👨‍🌾 Farmer Profile",
        "sidebar_profile_placeholder": "Your details (crops, land, location)",
        "sidebar_history": "📜 Conversation History",
        "sidebar_clear": "Clear History",
        "tab1": "🎤 Voice Assistant",
        "tab2": "💰 Market Prices",
        "tab3": "🌤️ Weather",
        "tab4": "🧪 Soil Health",
        "tab5": "📝 Personalized Advice",
        "voice_header": "🎤 Ask by Voice",
        "voice_placeholder": "Tap to record your question",
        "voice_transcribing": "Transcribing...",
        "voice_thinking": "Getting advice...",
        "voice_error": "Could not understand. Please speak clearly.",
        "voice_type_header": "Or type your question",
        "voice_type_placeholder": "Type here",
        "voice_ask_btn": "Ask",
        "market_header": "💰 Mandi Prices",
        "market_info": "ℹ️ Live API is ready but waiting for government API key. Showing realistic sample prices.",
        "market_commodity": "Commodity (e.g., Wheat, Rice, Tomato)",
        "market_state": "State",
        "market_btn": "Get Price",
        "weather_header": "🌤️ Weather",
        "weather_city": "Enter district/city name",
        "weather_btn": "Get Weather",
        "soil_header": "🧪 Soil Health Analysis",
        "soil_photo_option": "Option 1: Upload a photo of your soil",
        "soil_photo_btn": "Analyze Soil from Photo",
        "soil_pdf_option": "Option 2: Upload soil lab report (PDF)",
        "soil_pdf_btn": "Analyze PDF Report",
        "soil_manual_option": "Option 3: Enter test results manually",
        "soil_manual_btn": "Get Manual Advice",
        "personalized_header": "📝 Personalized Farming Advice",
        "personalized_warning": "Please fill your Farmer Profile in the sidebar first.",
        "personalized_question": "What specific advice do you need? (e.g., sowing time, pest control, fertilizer)",
        "personalized_btn": "Get Personalized Advice",
        "footer": "🌾 KisanMitra – Voice-First, Real-Time, Personalized Farming Companion | Jai Kisan!"
    },
    "hi": {
        "app_title": "🌾 किसान मित्र",
        "app_caption": "आपका आवाज़ी खेती साथी",
        "sidebar_title": "🌾 किसान मित्र",
        "sidebar_lang": "🗣️ जवाब की भाषा",
        "sidebar_profile": "👨‍🌾 किसान प्रोफ़ाइल",
        "sidebar_profile_placeholder": "आपका विवरण (फसलें, ज़मीन, स्थान)",
        "sidebar_history": "📜 बातचीत इतिहास",
        "sidebar_clear": "इतिहास साफ़ करें",
        "tab1": "🎤 आवाज़ सहायक",
        "tab2": "💰 मंडी भाव",
        "tab3": "🌤️ मौसम",
        "tab4": "🧪 मिट्टी स्वास्थ्य",
        "tab5": "📝 व्यक्तिगत सलाह",
        "voice_header": "🎤 आवाज़ से पूछें",
        "voice_placeholder": "अपना सवाल रिकॉर्ड करें",
        "voice_transcribing": "लिख रहा हूँ...",
        "voice_thinking": "जवाब दे रहा हूँ...",
        "voice_error": "समझ नहीं आया। कृपया साफ़ बोलें।",
        "voice_type_header": "या लिखकर पूछें",
        "voice_type_placeholder": "यहाँ लिखें",
        "voice_ask_btn": "पूछें",
        "market_header": "💰 मंडी भाव",
        "market_info": "ℹ️ लाइव API तैयार है, सरकारी API कुंजी का इंतज़ार है। नमूना मूल्य दिखा रहे हैं।",
        "market_commodity": "फसल (जैसे, गेहूं, धान, टमाटर)",
        "market_state": "राज्य",
        "market_btn": "भाव देखें",
        "weather_header": "🌤️ मौसम",
        "weather_city": "जिला/शहर का नाम लिखें",
        "weather_btn": "मौसम देखें",
        "soil_header": "🧪 मिट्टी स्वास्थ्य जांच",
        "soil_photo_option": "विकल्प 1: मिट्टी की फोटो अपलोड करें",
        "soil_photo_btn": "फोटो से मिट्टी जांचें",
        "soil_pdf_option": "विकल्प 2: मिट्टी लैब रिपोर्ट (PDF) अपलोड करें",
        "soil_pdf_btn": "PDF रिपोर्ट जांचें",
        "soil_manual_option": "विकल्प 3: मैन्युअल रूप से मान दर्ज करें",
        "soil_manual_btn": "मैन्युअल सलाह लें",
        "personalized_header": "📝 व्यक्तिगत खेती सलाह",
        "personalized_warning": "कृपया पहले साइडबार में किसान प्रोफ़ाइल भरें।",
        "personalized_question": "आपको किस सलाह की ज़रूरत है? (जैसे, बुवाई का समय, कीट नियंत्रण, खाद)",
        "personalized_btn": "व्यक्तिगत सलाह लें",
        "footer": "🌾 किसान मित्र – आवाज़-पहला, वास्तविक-समय, व्यक्तिगत खेती साथी | जय किसान!"
    }
}

def t(key):
    lang = st.session_state.get("language", DEFAULT_LANGUAGE)
    return TEXTS.get(lang, TEXTS[DEFAULT_LANGUAGE]).get(key, key)

if "language" not in st.session_state:
    st.session_state.language = DEFAULT_LANGUAGE
if "history" not in st.session_state:
    st.session_state.history = []
if "lang_pref" not in st.session_state:
    st.session_state.lang_pref = "English"
if "farmer_profile" not in st.session_state:
    st.session_state.farmer_profile = ""

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

# ========== SIDEBAR ==========
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/1998/1998626.png", width=80)
    st.title(t("sidebar_title"))
    st.markdown("---")
    
    selected_lang = st.selectbox(
        t("sidebar_lang"),
        options=list(SUPPORTED_LANGS.keys()),
        format_func=lambda x: SUPPORTED_LANGS[x],
        index=list(SUPPORTED_LANGS.keys()).index(st.session_state.language)
    )
    if selected_lang != st.session_state.language:
        st.session_state.language = selected_lang
        st.session_state.lang_pref = "English" if st.session_state.language == "en" else "Hindi"
        st.rerun()
    
    st.markdown("---")
    st.subheader(t("sidebar_profile"))
    st.session_state.farmer_profile = st.text_area("", value=st.session_state.farmer_profile, placeholder=t("sidebar_profile_placeholder"), height=100)
    st.markdown("---")
    st.subheader(t("sidebar_history"))
    if st.button(t("sidebar_clear")):
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
    return {"temp": 28, "humidity": 65, "description": "clear sky", "city": city}

def get_mandi_price(commodity, state="Uttar Pradesh"):
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
    prompt = """You are a soil expert. Analyze this soil image and provide:
    1. Estimated soil type (sandy, clay, loamy, etc.)
    2. General health indication (good, moderate, poor)
    3. Simple recommendation for improvement
    Keep answer short."""
    try:
        response = vision_model.generate_content([prompt, image])
        return response.text
    except Exception as e:
        return f"Error analyzing image: {e}"

def analyze_soil_pdf(pdf_bytes):
    try:
        reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
        text = ""
        for page in reader.pages:
            text += page.extract_text()
        if not text.strip():
            return "Could not read text from PDF."
        prompt = f"Analyze this soil report and give recommendations: {text[:1500]}"
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error processing PDF: {e}"

def get_soil_advice(soil_data):
    prompt = f"Analyze soil: {soil_data}. Give short advice on fertilizer and pH correction."
    try:
        return model.generate_content(prompt).text
    except:
        return "Unable to analyze soil data."

def get_personalized_advice(profile, question):
    prompt = f"Farmer profile: {profile}\nQuestion: {question}\nGive personalized, practical advice."
    try:
        return model.generate_content(prompt).text
    except:
        return "AI temporarily unavailable."

# ========== MAIN TABS ==========
tab1, tab2, tab3, tab4, tab5 = st.tabs([t("tab1"), t("tab2"), t("tab3"), t("tab4"), t("tab5")])

# ----- TAB 1: VOICE ASSISTANT -----
with tab1:
    st.header(t("voice_header"))
    audio_val = st.audio_input(t("voice_placeholder"))
    if audio_val:
        with st.spinner(t("voice_transcribing")):
            text = transcribe_audio(audio_val.getvalue())
        if text:
            st.markdown(f'<div class="user-msg">🗣️ <strong>You:</strong> {text}</div>', unsafe_allow_html=True)
            with st.spinner(t("voice_thinking")):
                ans = get_ai_response(text, st.session_state.lang_pref)
            st.markdown(f'<div class="bot-msg">🤖 <strong>KisanMitra:</strong> {ans}</div>', unsafe_allow_html=True)
            st.session_state.history.append({"q": text, "a": ans})
        else:
            st.error(t("voice_error"))
    st.divider()
    st.subheader(t("voice_type_header"))
    txt_q = st.text_input(t("voice_type_placeholder"))
    if st.button(t("voice_ask_btn"), key="ask_text"):
        if txt_q:
            ans = get_ai_response(txt_q, st.session_state.lang_pref)
            st.markdown(f'<div class="user-msg">🗣️ <strong>You:</strong> {txt_q}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="bot-msg">🤖 <strong>KisanMitra:</strong> {ans}</div>', unsafe_allow_html=True)
            st.session_state.history.append({"q": txt_q, "a": ans})

# ----- TAB 2: MARKET PRICES -----
with tab2:
    st.header(t("market_header"))
    st.info(t("market_info"))
    col1, col2 = st.columns(2)
    with col1:
        commodity = st.text_input(t("market_commodity"))
    with col2:
        state = st.text_input(t("market_state"), "Uttar Pradesh")
    if st.button(t("market_btn")):
        if commodity:
            price_info = get_mandi_price(commodity, state)
            st.success(f"**{price_info['commodity']}** in {price_info['market']}, {price_info['state']}")
            st.metric("Price per quintal", f"₹{price_info['price']}")
            st.caption(f"Source: {price_info['source']}")

# ----- TAB 3: WEATHER -----
with tab3:
    st.header(t("weather_header"))
    city = st.text_input(t("weather_city"), "Lucknow")
    if st.button(t("weather_btn")):
        w = get_weather(city)
        col1, col2, col3 = st.columns(3)
        col1.metric("Temperature", f"{w['temp']}°C")
        col2.metric("Humidity", f"{w['humidity']}%")
        col3.metric("Condition", w['description'].title())

# ----- TAB 4: SOIL HEALTH -----
with tab4:
    st.header(t("soil_header"))
    st.subheader(t("soil_photo_option"))
    soil_img = st.file_uploader("", type=["jpg", "jpeg", "png"])
    if soil_img:
        image = Image.open(soil_img)
        st.image(image, width=200)
        if st.button(t("soil_photo_btn")):
            with st.spinner("Analyzing..."):
                advice = analyze_soil_image(image)
            st.markdown(f'<div class="bot-msg">📸 {advice}</div>', unsafe_allow_html=True)
    st.subheader(t("soil_pdf_option"))
    pdf_file = st.file_uploader("", type=["pdf"])
    if pdf_file:
        if st.button(t("soil_pdf_btn")):
            with st.spinner("Reading PDF..."):
                advice = analyze_soil_pdf(pdf_file.read())
            st.markdown(f'<div class="bot-msg">📑 {advice}</div>', unsafe_allow_html=True)
    st.subheader(t("soil_manual_option"))
    soil_input = st.text_area("")
    if st.button(t("soil_manual_btn")):
        if soil_input:
            advice = get_soil_advice(soil_input)
            st.markdown(f'<div class="bot-msg">📋 {advice}</div>', unsafe_allow_html=True)

# ----- TAB 5: PERSONALIZED ADVICE -----
with tab5:
    st.header(t("personalized_header"))
    if not st.session_state.farmer_profile:
        st.warning(t("personalized_warning"))
    else:
        question = st.text_area(t("personalized_question"))
        if st.button(t("personalized_btn")):
            if question:
                advice = get_personalized_advice(st.session_state.farmer_profile, question)
                st.markdown(f'<div class="bot-msg">🎯 {advice}</div>', unsafe_allow_html=True)

# ----- FOOTER -----
st.markdown("---")
st.caption(t("footer"))