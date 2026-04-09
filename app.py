import streamlit as st
import requests
import google.generativeai as genai
import io
import speech_recognition as sr
from PIL import Image
import datetime
import PyPDF2
import json
from urllib.parse import quote

# ========== PAGE CONFIG ==========
st.set_page_config(page_title="KisanMitra", page_icon="🌾", layout="wide")

# ========== INITIALIZE SESSION STATE ==========
if "entered_app" not in st.session_state:
    st.session_state.entered_app = False

# ========== LANDING PAGE (full‑screen background, button at bottom) ==========
if not st.session_state.entered_app:
    st.markdown("""
    <style>
        /* Remove default padding */
        .main > div {
            padding: 0rem;
        }
        .stApp {
            background: linear-gradient(145deg, #2d6a4f, #1b4332) !important;
        }
        /* Full‑screen container with background image */
        .landing-wrapper {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-image: url('https://cdn.pixabay.com/photo/2016/11/14/04/08/farmer-1822530_640.jpg');
            background-size: cover;
            background-position: center;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            text-align: center;
            color: white;
            font-family: 'Inter', sans-serif;
            z-index: 999;
        }
        /* Dark overlay for better text contrast */
        .landing-wrapper::before {
            content: "";
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.4);
            z-index: -1;
        }
        .landing-title {
            font-size: 3rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
        }
        .landing-tagline {
            font-size: 1.5rem;
            font-weight: 500;
            margin-bottom: 3rem;
            text-shadow: 1px 1px 2px rgba(0,0,0,0.5);
        }
        /* Button container at bottom */
        .button-container {
            position: absolute;
            bottom: 80px;
            left: 0;
            right: 0;
            text-align: center;
        }
        .start-btn {
            background-color: #f4a261;
            color: #1b4332;
            border: none;
            border-radius: 60px;
            padding: 12px 32px;
            font-size: 1.2rem;
            font-weight: bold;
            cursor: pointer;
            transition: 0.2s;
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        }
        .start-btn:hover {
            background-color: #e76f51;
            transform: scale(1.02);
        }
    </style>
    <div class="landing-wrapper">
        <div class="landing-title">🌾 KisanMitra</div>
        <div class="landing-tagline">Har Kisan ka Digital Saathi</div>
        <div class="button-container">
            <button class="start-btn" onclick="document.getElementById('start_button').click();">Start Now</button>
        </div>
    </div>
    """, unsafe_allow_html=True)
    # Hidden Streamlit button triggered by the HTML button
    if st.button("Start Now", key="start_button", use_container_width=True, style="display:none;"):
        st.session_state.entered_app = True
        st.rerun()
    # Hide the visible Streamlit button (only the HTML button appears)
    st.markdown("<style>div[data-testid='column'] button[key='start_button'] { display: none; }</style>", unsafe_allow_html=True)
    st.stop()

# ========== MAIN APP BACKGROUND (earthy gradient) ==========
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(180deg, #f6f1e5 0%, #efe7d3 100%) !important;
        font-family: 'Inter', sans-serif;
        overflow: auto;
    }
    /* Sidebar earthy green */
    [data-testid="stSidebar"] {
        background: #d9c8a5 !important;
    }
    [data-testid="stSidebar"] * {
        color: #2f2516 !important;
    }
    .main > div {
        padding: 0rem 1rem;
    }
</style>
""", unsafe_allow_html=True)

# ========== PRODUCT HEADER ==========
st.markdown("""
<div style='background:#fffaf0;padding:0.8rem 1.2rem;border-radius:20px;
border:1px solid #dcc9a2;margin-bottom:1rem'>
    <h3 style='margin:0;color:#4a3f2b;'>🌾 KisanMitra</h3>
    <p style='margin:0;color:#6b5a3a;font-size:0.85rem;'>AI-powered smart farming assistant</p>
</div>
""", unsafe_allow_html=True)

# ---------- Load API Keys ----------
GEMINI_API_KEY = None
try:
    if "GEMINI_API_KEY" in st.secrets:
        GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
except:
    pass
if not GEMINI_API_KEY:
    try:
        from dotenv import load_dotenv
        import os
        load_dotenv()
        GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    except:
        pass
if not GEMINI_API_KEY:
    st.error("❌ Gemini API key missing.")
    st.stop()

GEMINI_API_KEY = GEMINI_API_KEY.strip().strip('"').strip("'")
available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
if not available_models:
    st.error("No models available.")
    st.stop()
MODEL_NAME = available_models[0]
st.info(f"Using model: {MODEL_NAME}")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(MODEL_NAME)
vision_model = genai.GenerativeModel(MODEL_NAME)

# ---------- Multilingual Dictionary ----------
SUPPORTED_LANGS = {"en": "English", "hi": "हिंदी"}
DEFAULT_LANGUAGE = "en"

if "language" not in st.session_state:
    st.session_state.language = DEFAULT_LANGUAGE

def t(key):
    translations = {
        "en": {
            "sidebar_title": "KisanMitra", "sidebar_lang": "Language", "sidebar_profile": "Farmer Profile",
            "sidebar_profile_placeholder": "Your details (crops, land, location)", "sidebar_history": "Conversation History",
            "sidebar_clear": "Clear History", "tab1": "🎤 Voice", "tab2": "💰 Market", "tab3": "🌤️ Weather",
            "tab4": "🧪 Soil", "tab5": "📝 Advice", "tab6": "🔄 Rotation", "tab7": "🚺 Women", "tab8": "📜 Schemes",
            "tab9": "🌾 KVK", "voice_header": "Ask by Voice", "voice_stop": "Stop Recording",
            "voice_stopped": "Recording stopped. Click 'Enable Recording' to ask again.", "voice_enable": "Enable Recording",
            "voice_placeholder": "Tap to record your question", "voice_transcribing": "Transcribing...",
            "voice_thinking": "Getting advice...", "voice_error": "Could not understand. Please speak clearly.",
            "voice_type_header": "Or type your question", "voice_type_placeholder": "Type here", "voice_ask_btn": "Ask",
            "market_header": "Mandi Prices", "market_info": "Live API ready – showing sample prices.",
            "market_commodity": "Commodity (e.g., Wheat, Rice)", "market_state": "State", "market_btn": "Get Price",
            "weather_header": "Weather & Alerts", "weather_gps_info": "📍 Use <strong>Use My Location</strong> and allow browser GPS.",
            "weather_or": "— OR —", "weather_city": "Enter district/city name", "weather_source": "Select weather source",
            "weather_manual": "Manual City", "weather_gps": "Current Location", "weather_btn": "Get Weather",
            "weather_refresh": "🔄 Refresh Weather", "weather_today": "Today", "weather_tomorrow": "Tomorrow",
            "weather_temp": "°C", "soil_header": "Soil Health Analysis", "soil_photo_option": "Option 1: Upload a photo of your soil",
            "soil_photo_btn": "Analyze Soil from Photo", "soil_pdf_option": "Option 2: Upload soil lab report (PDF)",
            "soil_pdf_btn": "Analyze PDF Report", "soil_manual_option": "Option 3: Enter test results manually",
            "soil_manual_btn": "Get Manual Advice", "personalized_header": "Personalized Farming Advice",
            "crop_damage_header": "🌾 Crop Damage Recovery (Heavy Rain / Waterlogging)", "crop_damage_crop": "Affected crop",
            "crop_damage_type": "Type of damage", "crop_damage_btn": "Get Recovery Advice",
            "personalized_warning": "Please fill your Farmer Profile in the sidebar first.",
            "personalized_question": "What specific advice do you need? (e.g., sowing time, pest control, fertilizer)",
            "personalized_btn": "Get Personalized Advice", "rotation_header": "Crop Rotation Advisor",
            "rotation_prev": "Previous crop grown", "rotation_next": "Crop you want to grow next", "rotation_btn": "Get Rotation Advice",
            "women_header": "Women Farmer Empowerment", "safety_tip": "Safety Tip of the Day", "read_tip": "Read Tip Aloud",
            "emergency_header": "Emergency & Helpline Numbers", "farming_ideas_header": "Small‑Scale Farming for Women",
            "govt_schemes_women": "Government Schemes for Women", "schemes_header": "Government Schemes for Farmers",
            "schemes_filter": "Filter by Category:", "kvk_header": "Krishi Vigyan Kendra (KVK)",
            "kvk_caption": "Find your nearest KVK centre and get expert agricultural support.",
            "kvk_district": "Enter your district name:", "kvk_btn": "Find KVK",
            "kvk_info": "KVK centres provide free soil testing, seed distribution, training, and crop‑specific advice.",
            "footer": "🌾 KisanMitra – Voice-First, Real-Time, Personalized Farming Companion | Jai Kisan!"
        },
        "hi": {
            "sidebar_title": "किसान मित्र", "sidebar_lang": "भाषा", "sidebar_profile": "किसान प्रोफ़ाइल",
            "sidebar_profile_placeholder": "आपका विवरण (फसलें, ज़मीन, स्थान)", "sidebar_history": "बातचीत इतिहास",
            "sidebar_clear": "इतिहास साफ़ करें", "tab1": "🎤 आवाज़", "tab2": "💰 मंडी", "tab3": "🌤️ मौसम",
            "tab4": "🧪 मिट्टी", "tab5": "📝 सलाह", "tab6": "🔄 फसल चक्र", "tab7": "🚺 महिला", "tab8": "📜 योजनाएँ",
            "tab9": "🌾 केवीके", "voice_header": "आवाज़ से पूछें", "voice_stop": "रिकॉर्डिंग बंद करें",
            "voice_stopped": "रिकॉर्डिंग बंद की गई। फिर से पूछने के लिए 'रिकॉर्डिंग सक्षम करें' पर क्लिक करें।",
            "voice_enable": "रिकॉर्डिंग सक्षम करें", "voice_placeholder": "अपना सवाल रिकॉर्ड करें",
            "voice_transcribing": "लिख रहा हूँ...", "voice_thinking": "जवाब दे रहा हूँ...",
            "voice_error": "समझ नहीं आया। कृपया साफ़ बोलें।", "voice_type_header": "या लिखकर पूछें",
            "voice_type_placeholder": "यहाँ लिखें", "voice_ask_btn": "पूछें", "market_header": "मंडी भाव",
            "market_info": "लाइव API तैयार – नमूना मूल्य दिखा रहे हैं।", "market_commodity": "फसल (जैसे, गेहूं, धान)",
            "market_state": "राज्य", "market_btn": "भाव देखें", "weather_header": "मौसम और अलर्ट",
            "weather_gps_info": "📍 <strong>मेरा स्थान उपयोग करें</strong> पर क्लिक करें और ब्राउज़र को अनुमति दें।",
            "weather_or": "— अथवा —", "weather_city": "जिला/शहर का नाम लिखें", "weather_source": "मौसम स्रोत चुनें",
            "weather_manual": "मैन्युअल शहर", "weather_gps": "वर्तमान स्थान", "weather_btn": "मौसम देखें",
            "weather_refresh": "🔄 मौसम ताज़ा करें", "weather_today": "आज", "weather_tomorrow": "कल", "weather_temp": "°C",
            "soil_header": "मिट्टी स्वास्थ्य जांच", "soil_photo_option": "विकल्प 1: मिट्टी की फोटो अपलोड करें",
            "soil_photo_btn": "फोटो से मिट्टी जांचें", "soil_pdf_option": "विकल्प 2: मिट्टी लैब रिपोर्ट (PDF) अपलोड करें",
            "soil_pdf_btn": "PDF रिपोर्ट जांचें", "soil_manual_option": "विकल्प 3: मैन्युअल रूप से मान दर्ज करें",
            "soil_manual_btn": "मैन्युअल सलाह लें", "personalized_header": "व्यक्तिगत खेती सलाह",
            "crop_damage_header": "🌾 फसल क्षति रिकवरी (भारी बारिश / जलभराव)", "crop_damage_crop": "प्रभावित फसल",
            "crop_damage_type": "क्षति का प्रकार", "crop_damage_btn": "रिकवरी सलाह लें",
            "personalized_warning": "कृपया पहले साइडबार में किसान प्रोफ़ाइल भरें।",
            "personalized_question": "आपको किस सलाह की ज़रूरत है? (जैसे, बुवाई का समय, कीट नियंत्रण, खाद)",
            "personalized_btn": "व्यक्तिगत सलाह लें", "rotation_header": "फसल चक्र सलाहकार",
            "rotation_prev": "पिछली उगाई गई फसल", "rotation_next": "अगली फसल जो आप उगाना चाहते हैं",
            "rotation_btn": "फसल चक्र सलाह लें", "women_header": "महिला किसान सशक्तिकरण",
            "safety_tip": "दिन की सुरक्षा टिप", "read_tip": "टिप सुनें", "emergency_header": "आपातकालीन एवं हेल्पलाइन नंबर",
            "farming_ideas_header": "महिलाओं के लिए छोटे पैमाने पर खेती के विचार",
            "govt_schemes_women": "महिला किसानों के लिए सरकारी योजनाएँ", "schemes_header": "किसानों के लिए सरकारी योजनाएँ",
            "schemes_filter": "श्रेणी से छाँटें:", "kvk_header": "कृषि विज्ञान केंद्र (केवीके)",
            "kvk_caption": "अपना निकटतम केवीके केंद्र खोजें और विशेषज्ञ कृषि सहायता प्राप्त करें।",
            "kvk_district": "अपने जिले का नाम लिखें:", "kvk_btn": "केवीके खोजें",
            "kvk_info": "केवीके केंद्र निःशुल्क मिट्टी परीक्षण, बीज वितरण, प्रशिक्षण और फसल-विशिष्ट सलाह प्रदान करते हैं।",
            "footer": "🌾 किसान मित्र – आवाज़-पहला, वास्तविक-समय, व्यक्तिगत खेती साथी | जय किसान!"
        }
    }
    return translations[st.session_state.get("language", DEFAULT_LANGUAGE)].get(key, key)

if "history" not in st.session_state: st.session_state.history = []
if "lang_pref" not in st.session_state: st.session_state.lang_pref = "English"
if "farmer_profile" not in st.session_state: st.session_state.farmer_profile = ""
if "stop_voice" not in st.session_state: st.session_state.stop_voice = False
if "weather_city_from_gps" not in st.session_state: st.session_state.weather_city_from_gps = None
if "last_weather_data" not in st.session_state: st.session_state.last_weather_data = None

# ---------- Sidebar ----------
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/1998/1998626.png", width=70)
    st.title(t("sidebar_title"))
    selected_lang = st.selectbox(t("sidebar_lang"), options=["en","hi"], format_func=lambda x: "English" if x=="en" else "हिंदी", index=0 if st.session_state.language=="en" else 1)
    if selected_lang != st.session_state.language:
        st.session_state.language = selected_lang
        st.session_state.lang_pref = "English" if selected_lang=="en" else "Hindi"
        st.rerun()
    st.caption(f"Current UI language: {'English' if st.session_state.language=='en' else 'हिंदी'}")
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

# ---------- Helper Functions ----------
def transcribe_audio(audio_bytes):
    try:
        recognizer = sr.Recognizer()
        with sr.AudioFile(io.BytesIO(audio_bytes)) as source:
            audio_data = recognizer.record(source)
        return recognizer.recognize_google(audio_data)
    except: return None

def detect_language(text):
    return "Hindi" if any('\u0900' <= c <= '\u097f' for c in text) else "English"

def speak_text(text, lang):
    if lang == "Hindi":
        js = f"""
        <script>
            var utterance = new SpeechSynthesisUtterance({json.dumps(text)});
            utterance.lang = 'hi-IN';
            var voices = window.speechSynthesis.getVoices();
            var hindiVoice = voices.find(voice => voice.lang === 'hi-IN');
            if (hindiVoice) utterance.voice = hindiVoice;
            window.speechSynthesis.speak(utterance);
        </script>
        """
    else:
        js = f'<script>var u=new SpeechSynthesisUtterance({json.dumps(text)}); u.lang="en-US"; window.speechSynthesis.speak(u);</script>'
    st.components.v1.html(js, height=0)

def get_ai_response(question, lang):
    detected = detect_language(question)
    force_lang = "Hindi. You MUST answer in Hindi using Devanagari script. No English words." if detected == "Hindi" else "English"
    prompt = f"""You are KisanMitra, a friendly expert farming assistant.
Response language: {force_lang}
Farmer asked: "{question}"
Give a short, practical, actionable answer (max 3 sentences). CRITICAL: Answer in the same language as the question."""
    try: return model.generate_content(prompt).text
    except Exception as e: return f"⚠️ AI error: {str(e)}"

def get_weather_forecast(city):
    return {
        "today": {"temp": 32, "humidity": 65, "condition": "Sunny", "advice": "Good for sowing."},
        "tomorrow": {"temp": 28, "humidity": 85, "condition": "Heavy rain expected", "advice": "Avoid spraying pesticides."}
    }

def get_weather_alert(forecast):
    cond = forecast["tomorrow"]["condition"].lower()
    hum = forecast["tomorrow"]["humidity"]
    if "heavy rain" in cond:
        return "red", ["⚠️ Heavy rain expected tomorrow! Harvest ripe crops immediately.", "🌾 Cover harvested crops with tarpaulin.", "🛑 Postpone fertiliser and pesticide spraying."]
    elif hum > 80:
        return "orange", ["💧 High humidity – risk of fungal diseases. Inspect crops.", "🔍 Apply organic fungicide if dry interval appears."]
    return "normal", ["✅ Weather suitable for normal farming activities."]

def get_mandi_price(commodity, state="Uttar Pradesh"):
    mock = {"wheat":2250,"rice":2180,"mustard":5650,"tomato":1800,"potato":1200,"onion":2500,"corn":2120,"chana":5200}
    price = mock.get(commodity.lower(), 2000)
    return {"commodity": commodity, "price": price, "market": "Sample Mandi (Live API ready)", "state": state, "source": "Mock data"}

def analyze_soil_image(image):
    prompt = """You are a soil expert. Analyze this soil image and provide:
    1. Estimated soil type (sandy, clay, loamy, etc.)
    2. General health indication (good, moderate, poor)
    3. Simple recommendation for improvement. Keep answer short."""
    try: return vision_model.generate_content([prompt, image]).text
    except: return "Error analyzing image."

def analyze_soil_pdf(pdf_bytes):
    try:
        reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
        text = "".join([page.extract_text() for page in reader.pages])
        if not text.strip(): return "Could not read text from PDF."
        return model.generate_content(f"Analyze this soil report and give recommendations: {text[:1500]}").text
    except: return "Error processing PDF."

def get_soil_advice(soil_data):
    try: return model.generate_content(f"Analyze soil: {soil_data}. Give short advice on fertilizer and pH correction.").text
    except: return "Unable to analyze soil data."

def get_personalized_advice(profile, question):
    try: return model.generate_content(f"Farmer profile: {profile}\nQuestion: {question}\nGive personalized, practical advice.").text
    except: return "AI temporarily unavailable."

def get_crop_damage_advice(crop, damage_type, lang):
    prompt = f"{crop} field damaged by {damage_type}. Give short recovery steps in {lang}: 1) Drain water 2) Fertiliser to apply 3) Disease prevention 4) When to replant. Keep under 100 words."
    try: return model.generate_content(prompt).text
    except: return "Unable to generate advice. Please consult local agriculture officer."

CROP_ROTATION = {
    "sugarcane": {"next_crops": ["wheat","mustard","potato"], "advice": "Sugarcane depletes nitrogen. Grow wheat or mustard with extra nitrogen.", "soil_condition": "Add 20% more nitrogen."},
    "wheat": {"next_crops": ["rice","maize","pulses"], "advice": "Wheat leaves residual phosphorus. Good for legumes.", "soil_condition": "Reduce DAP by 25%."},
    "rice": {"next_crops": ["wheat","mustard","vegetables"], "advice": "Rice depletes zinc. Apply zinc sulfate before next crop.", "soil_condition": "Zinc deficiency likely. Add organic matter."},
    "potato": {"next_crops": ["maize","onion","cabbage"], "advice": "Potato depletes potassium. Add potash for next crop.", "soil_condition": "Potassium low. Use NPK 20:20:20."},
    "tomato": {"next_crops": ["beans","peas","cucumber"], "advice": "Tomato susceptible to same pests. Rotate with legumes.", "soil_condition": "Good for nitrogen-fixing crops."}
}

def get_crop_rotation_advice(prev, next_c):
    p = prev.lower(); n = next_c.lower()
    if p in CROP_ROTATION:
        if n in CROP_ROTATION[p]["next_crops"]:
            return {"suitable": True, "advice": CROP_ROTATION[p]["advice"], "soil": CROP_ROTATION[p]["soil_condition"]}
        else:
            return {"suitable": False, "advice": f"{prev} to {next_c} not ideal. Recommended: {', '.join(CROP_ROTATION[p]['next_crops'])}", "soil": "Consider soil testing."}
    return {"suitable": True, "advice": "Crop rotation is good for soil health.", "soil": "Add compost before sowing."}

def chatbot_response(user_input, lang="English"):
    detected = detect_language(user_input)
    force_lang = "Hindi. You MUST answer in Hindi using Devanagari script. No English words." if detected == "Hindi" else "English"
    prompt = f"""You are a helpful farming assistant chatbot for KisanMitra.
Response language: {force_lang}
User says: "{user_input}"
Give a short, friendly, helpful answer (max 2 sentences). Keep it warm and encouraging.
CRITICAL: Answer in the same language as the user."""
    try: return model.generate_content(prompt).text
    except Exception as e: return f"⚠️ Error: {str(e)[:100]}"

def get_kvk_by_district(district):
    kvk_data = [
        {"district": "Lucknow", "center_name": "KVK, Lucknow", "head": "Dr. A. K. Singh", "contact": "+91-522-1234567", "email": "kvk.lucknow@icar.gov.in", "services": "Soil testing, seed production, organic farming training."},
        {"district": "Prayagraj", "center_name": "KVK, Naini", "head": "Dr. S. K. Sharma", "contact": "+91-532-1234567", "email": "kvk.naini@icar.gov.in", "services": "Integrated farming, vermicomposting, fruit preservation."},
        {"district": "Varanasi", "center_name": "KVK, Varanasi", "head": "Dr. R. K. Pandey", "contact": "+91-542-1234567", "email": "kvk.varanasi@icar.gov.in", "services": "Dairy management, aquaculture, mushroom."},
        {"district": "Bareilly", "center_name": "KVK, Bareilly", "head": "Dr. M. K. Sharma", "contact": "+91-581-1234567", "email": "kvk.bareilly@icar.gov.in", "services": "Wheat research, soil health cards, farm machinery."}
    ]
    for center in kvk_data:
        if center["district"].lower() == district.lower():
            return center
    return None

GPS_HTML = """
<div style="margin: 10px 0;">
    <button id="gps-btn" style="background:#7a5c2e; color:white; padding:10px 20px; border:none; border-radius:30px; cursor:pointer; font-size:16px;">📍 Use My Location</button>
    <p id="gps-status" style="margin-top:8px; font-size:0.85rem; color:#5c4b2f;"></p>
</div>
<form id="gps-form" method="post" action="">
    <input type="hidden" name="gps_lat" id="gps_lat">
    <input type="hidden" name="gps_lon" id="gps_lon">
</form>
<script>
    const btn = document.getElementById('gps-btn');
    const status = document.getElementById('gps-status');
    btn.onclick = function() {
        if (!navigator.geolocation) {
            status.innerText = "❌ GPS not supported by your browser.";
            return;
        }
        status.innerText = "📍 Requesting location... Please allow permission when the browser asks.";
        navigator.geolocation.getCurrentPosition(
            (position) => {
                const lat = position.coords.latitude;
                const lon = position.coords.longitude;
                document.getElementById('gps_lat').value = lat;
                document.getElementById('gps_lon').value = lon;
                document.getElementById('gps-form').submit();
                status.innerText = "✅ Location captured! Refreshing...";
            },
            (error) => {
                let msg = "❌ Location permission denied. ";
                if (error.code === 1) msg += "Tap the lock icon in address bar and allow location.";
                else if (error.code === 2) msg += "Location unavailable. Ensure GPS is on.";
                else msg += "Unknown error. Try again.";
                status.innerText = msg;
                console.error(error);
            },
            { enableHighAccuracy: true, timeout: 10000 }
        );
    };
</script>
"""

def get_city_from_coords(lat, lon):
    try:
        r = requests.get(f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=json", headers={'User-Agent':'KisanMitra'})
        return r.json().get('address', {}).get('city') or r.json().get('address', {}).get('town') or "Your Location"
    except: return "Your Location"

# ---------- SCHEMES DATA ----------
SCHEMES_DATA = {
    "schemes": [
        {"category": "Crop Insurance", "name": "Pradhan Mantri Fasal Bima Yojana", "description": "Low premium crop insurance (2% for Kharif, 1.5% for Rabi).", "link": "https://pmfby.gov.in/"},
        {"category": "Women Farmers", "name": "Mahila Kisan Sashaktikaran Pariyojana", "description": "Skill development and livelihood support for women farmers.", "link": "https://nrlm.gov.in/"},
        {"category": "Direct Income Support", "name": "PM-Kisan Samman Nidhi", "description": "₹6,000 per year income support.", "link": "https://pmkisan.gov.in/"},
        {"category": "Pension & Social Security", "name": "PM Kisan Maan Dhan Yojana", "description": "₹3,000 monthly pension after age 60.", "link": "https://maandhan.in/"},
        {"category": "Soil Health", "name": "Soil Health Card Scheme", "description": "Free soil testing and nutrient recommendations.", "link": "https://soilhealth.dac.gov.in/"}
    ]
}

# ========== FEATURE HIGHLIGHTS ==========
col1, col2, col3 = st.columns(3)
with col1:
    st.markdown("### 🌤️ Smart Weather")
    st.caption("Real-time alerts & farming advice")
with col2:
    st.markdown("### 🧪 Soil Intelligence")
    st.caption("Analyze soil via image or reports")
with col3:
    st.markdown("### 🎤 Voice Assistant")
    st.caption("Ask farming questions by voice")
st.divider()

# ---------- TABS ----------
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9 = st.tabs([
    "🎤 Voice Assistant",
    "💰 Market Prices",
    "🌤️ Weather Intelligence",
    "🧪 Soil Analysis",
    "📝 AI Advice",
    "🔄 Crop Rotation",
    "🚺 Women Empowerment",
    "📜 Government Schemes",
    "🌾 KVK Support"
])

# ----- TAB 1: VOICE -----
with tab1:
    st.header(t("voice_header"))
    if st.button(t("voice_stop"), key="stop_voice_btn"):
        st.session_state.stop_voice = True
        st.rerun()
    if st.session_state.stop_voice:
        st.info(t("voice_stopped"))
        if st.button(t("voice_enable"), key="enable_voice"):
            st.session_state.stop_voice = False
            st.rerun()
    else:
        audio_val = st.audio_input(t("voice_placeholder"), key="main_audio")
        if audio_val:
            with st.spinner(t("voice_transcribing")):
                text = transcribe_audio(audio_val.getvalue())
            if text:
                st.markdown(f'<div class="user-msg">🗣️ <strong>You:</strong> {text}</div>', unsafe_allow_html=True)
                with st.spinner("🤖 KisanMitra is thinking..."):
                    ans = get_ai_response(text, st.session_state.lang_pref)
                st.markdown(f'<div class="bot-msg">🤖 <strong>KisanMitra:</strong> {ans}</div>', unsafe_allow_html=True)
                st.session_state.history.append({"q": text, "a": ans})
                speak_text(ans, "Hindi" if detect_language(ans) == "Hindi" else "English")
            else:
                st.error(t("voice_error"))
    st.divider()
    st.subheader(t("voice_type_header"))
    txt_q = st.text_input(t("voice_type_placeholder"))
    if st.button(t("voice_ask_btn"), key="ask_text"):
        if txt_q:
            with st.spinner("🤖 KisanMitra is thinking..."):
                ans = get_ai_response(txt_q, st.session_state.lang_pref)
            st.markdown(f'<div class="user-msg">🗣️ <strong>You:</strong> {txt_q}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="bot-msg">🤖 <strong>KisanMitra:</strong> {ans}</div>', unsafe_allow_html=True)
            st.session_state.history.append({"q": txt_q, "a": ans})
            speak_text(ans, "Hindi" if detect_language(ans) == "Hindi" else "English")

# ----- TAB 2: MARKET -----
with tab2:
    st.header(t("market_header"))
    st.info(t("market_info"))
    col1, col2 = st.columns(2)
    with col1: commodity = st.text_input(t("market_commodity"))
    with col2: state = st.text_input(t("market_state"), "Uttar Pradesh")
    if st.button(t("market_btn")):
        if commodity:
            p = get_mandi_price(commodity, state)
            st.markdown(f"""
            <div style='background:#fffaf0;padding:1rem;border-radius:15px;border:1px solid #dcc9a2'>
            <h4 style='margin:0;'>🌾 {p['commodity']}</h4>
            <p style='margin:0;'>📍 {p['market']}, {p['state']}</p>
            <h3 style='margin-top:5px;'>₹ {p['price']} / quintal</h3>
            </div>
            """, unsafe_allow_html=True)
            st.caption(f"Source: {p['source']}")

# ----- TAB 3: WEATHER -----
with tab3:
    st.header(t("weather_header"))
    st.markdown(f'<div class="km-earth-card">{t("weather_gps_info")}</div>', unsafe_allow_html=True)
    st.markdown(GPS_HTML, unsafe_allow_html=True)
    st.caption(t("weather_or"))
    
    if "gps_lat" in st.query_params and "gps_lon" in st.query_params:
        lat = st.query_params.get("gps_lat")
        lon = st.query_params.get("gps_lon")
        try:
            lat = float(lat); lon = float(lon)
            city = get_city_from_coords(lat, lon)
            st.session_state.weather_city_from_gps = city
            st.success(f"📍 Location detected: {city}")
            st.query_params.clear()
            st.rerun()
        except:
            pass
    
    manual_city = st.text_input(t("weather_city"), "Lucknow")
    city = manual_city
    weather_source = st.radio(t("weather_source"), [t("weather_manual"), t("weather_gps")], horizontal=True)
    if weather_source == t("weather_gps"):
        if st.session_state.weather_city_from_gps:
            city = st.session_state.weather_city_from_gps
            st.info(f"Using GPS location: {city}")
        else:
            st.warning("Current location unavailable. Please click 'Use My Location' and allow GPS permission.")
    
    if st.button(t("weather_btn"), key="get_weather"):
        if weather_source == t("weather_gps") and not st.session_state.weather_city_from_gps:
            st.error("❌ GPS location not available. Turn on location and allow permission, then tap 'Use My Location'.")
        else:
            forecast = get_weather_forecast(city)
            st.session_state.last_weather_data = {"city": city, "forecast": forecast}
            st.rerun()
    
    if st.button(t("weather_refresh"), key="refresh_weather"):
        if weather_source == t("weather_gps") and not st.session_state.weather_city_from_gps:
            st.error("❌ GPS location not available. Turn on location and allow permission, then tap 'Use My Location'.")
        else:
            forecast = get_weather_forecast(city)
            st.session_state.last_weather_data = {"city": city, "forecast": forecast}
            st.rerun()
    
    if st.session_state.last_weather_data:
        data = st.session_state.last_weather_data
        forecast = data["forecast"]
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**{t('weather_today')}**")
            st.markdown(f"""
            <div class="km-earth-card">
            <b>🌡️ {forecast['today']['temp']}°C</b><br>
            {forecast['today']['condition']}<br>
            💡 {forecast['today']['advice']}
            </div>
            """, unsafe_allow_html=True)
        with col2:
            st.write(f"**{t('weather_tomorrow')}**")
            st.markdown(f"""
            <div class="km-earth-card">
            <b>🌡️ {forecast['tomorrow']['temp']}°C</b><br>
            {forecast['tomorrow']['condition']}<br>
            💡 {forecast['tomorrow']['advice']}
            </div>
            """, unsafe_allow_html=True)
        alert_level, advice_list = get_weather_alert(forecast)
        if alert_level == "red":
            st.error("🚨 **Severe Weather Alert!**")
        elif alert_level == "orange":
            st.warning("⚠️ **Weather Advisory**")
        for adv in advice_list:
            st.write(f"- {adv}")
    else:
        st.info("Click 'Get Weather' or 'Refresh Weather' to see forecast and alerts.")

# ----- TAB 4: SOIL -----
with tab4:
    st.header(t("soil_header"))
    st.subheader(t("soil_photo_option"))
    soil_img = st.file_uploader("", type=["jpg","jpeg","png"])
    if soil_img:
        image = Image.open(soil_img); st.image(image, width=200)
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
    st.subheader(t("crop_damage_header"))
    damage_crop = st.selectbox(t("crop_damage_crop"), ["Wheat", "Rice", "Pulses"])
    damage_type = st.selectbox(t("crop_damage_type"), ["Waterlogging", "Hailstorm", "Strong wind"])
    if st.button(t("crop_damage_btn"), key="recovery_btn"):
        advice = get_crop_damage_advice(damage_crop, damage_type, st.session_state.lang_pref)
        st.markdown(f'<div class="bot-msg">🌿 {advice}</div>', unsafe_allow_html=True)
    st.divider()
    if not st.session_state.farmer_profile:
        st.warning(t("personalized_warning"))
    else:
        question = st.text_area(t("personalized_question"))
        if st.button(t("personalized_btn")):
            if question:
                advice = get_personalized_advice(st.session_state.farmer_profile, question)
                st.markdown(f'<div class="bot-msg">🎯 {advice}</div>', unsafe_allow_html=True)

# ----- TAB 6: CROP ROTATION -----
with tab6:
    st.header(t("rotation_header"))
    col1, col2 = st.columns(2)
    with col1: previous_crop = st.selectbox(t("rotation_prev"), ["Sugarcane","Wheat","Rice","Potato","Tomato","Maize"])
    with col2: next_crop = st.selectbox(t("rotation_next"), ["Wheat","Mustard","Rice","Potato","Tomato","Maize","Pulses","Onion"])
    if st.button(t("rotation_btn")):
        adv = get_crop_rotation_advice(previous_crop, next_crop)
        if adv["suitable"]: st.success(f"✅ Good rotation choice!")
        else: st.warning(f"⚠️ {adv['advice']}")
        st.info(f"🌱 **Soil advice:** {adv['soil']}")
        with st.spinner("Getting detailed AI advice..."):
            prompt = f"Farmer grew {previous_crop} and wants to grow {next_crop}. Give soil management and fertilizer advice."
            detailed = model.generate_content(prompt)
            st.markdown(f'<div class="bot-msg">🤖 <strong>AI Suggestion:</strong><br>{detailed.text}</div>', unsafe_allow_html=True)

# ----- TAB 7: WOMEN EMPOWERMENT -----
with tab7:
    st.header(t("women_header"))
    safety_tips = [
        "🌾 Always inform a family member before going to the field alone.",
        "📞 Save local police and women’s helpline numbers on speed dial.",
        "👭 Form a group of women farmers in your village for mutual support.",
        "🌿 Keep a basic first‑aid kit in your farming bag.",
        "🚜 Learn about government schemes for women farmers – ask KisanMitra!"
    ]
    tip_idx = datetime.datetime.now().day % len(safety_tips)
    st.info(f"💡 **{t('safety_tip')}:** {safety_tips[tip_idx]}")
    if st.button(t("read_tip")):
        speak_text(safety_tips[tip_idx], "Hindi")
    st.divider()
    st.subheader(t("emergency_header"))
    contacts = {"Women Helpline (India)": "1091", "National Commission for Women": "7827170170", "Local Police": "100", "Women Farmer Support (MKSP)": "1800‑180‑1551"}
    for name, num in contacts.items():
        st.write(f"**{name}:** `{num}`")
    st.divider()
    st.subheader(t("farming_ideas_header"))
    ideas = {"🥬 Kitchen Garden": "Grow vegetables in small space. Low investment.", "🐔 Poultry": "Start with 10‑20 chicks. Eggs and meat provide income.", "🍄 Mushroom Cultivation": "Grows in dark sheds. High return in 30 days.", "🐄 Dairy (1‑2 cows)": "Daily milk income. Government subsidy available."}
    for idea, desc in ideas.items():
        with st.expander(idea):
            st.write(desc)
            if st.button(f"Ask KisanMitra about {idea}", key=f"ask_{idea}"):
                ans = get_ai_response(f"How to start {idea} as a woman farmer?", st.session_state.lang_pref)
                st.markdown(f'<div class="bot-msg">🤖 {ans}</div>', unsafe_allow_html=True)
    st.divider()
    st.subheader(t("govt_schemes_women"))
    women_schemes = [s for s in SCHEMES_DATA["schemes"] if s["category"] == "Women Farmers"]
    for s in women_schemes:
        with st.expander(s["name"]):
            st.write(s["description"])
            st.markdown(f"[🔗 Know More]({s['link']})")

# ----- TAB 8: SCHEMES -----
with tab8:
    st.header(t("schemes_header"))
    categories = sorted(list(set([s['category'] for s in SCHEMES_DATA['schemes']])))
    selected_cat = st.radio(t("schemes_filter"), ["All"] + categories, horizontal=True)
    filtered = SCHEMES_DATA['schemes']
    if selected_cat != "All": filtered = [s for s in filtered if s['category'] == selected_cat]
    cols = st.columns(2)
    for idx, scheme in enumerate(filtered):
        with cols[idx % 2]:
            with st.container(border=True):
                st.markdown(f"**{scheme['name']}**")
                st.caption(f"*Category: {scheme['category']}*")
                st.write(scheme['description'])
                st.markdown(f"[🔗 Know More]({scheme['link']})")

# ----- TAB 9: KVK -----
with tab9:
    st.header(t("kvk_header"))
    st.caption(t("kvk_caption"))
    district = st.text_input(t("kvk_district"), placeholder="e.g., Lucknow, Prayagraj, Bareilly")
    if st.button(t("kvk_btn"), use_container_width=True):
        kvk = get_kvk_by_district(district)
        if kvk:
            st.success(f"**{kvk['center_name']}**")
            st.markdown(f"**Head:** {kvk['head']}")
            st.markdown(f"**📞 Contact:** {kvk['contact']}")
            st.markdown(f"**📧 Email:** {kvk['email']}")
            st.markdown(f"**🛠️ Services offered:** {kvk['services']}")
        else:
            st.warning(f"No KVK data available for district: {district}. Please visit [ICAR KVK Portal](https://kvk.icar.gov.in/).")
    st.info(t("kvk_info"))

st.markdown("""
<div style='text-align:center;padding:0.8rem;color:#5c4b2f;font-size:0.9rem'>
✅ AI Powered &nbsp;&nbsp; | &nbsp;&nbsp; 🇮🇳 Built for Indian Farmers &nbsp;&nbsp; | &nbsp;&nbsp; 🌱 Data Driven
</div>
""", unsafe_allow_html=True)

# ----- FOOTER & CHATBOT -----
st.markdown("---")
st.caption(t("footer"))

with st.popover("💬 Help", use_container_width=False, help="Ask me about farming or using the app"):
    st.markdown("### KisanMitra Assistant")
    st.info("Ask me anything about farming or using the app.")
    if st.button("🔊 Play Welcome", key="play_help_greeting"):
        greeting = "नमस्ते! मैं आपकी क्या मदद कर सकता हूँ?"
        speak_text(greeting, "Hindi")
    
    audio_val = st.audio_input("Speak your question", key="chat_audio_popover")
    if audio_val:
        with st.spinner("Transcribing..."):
            text = transcribe_audio(audio_val.getvalue())
        if text:
            st.markdown(f"🗣️ **You:** {text}")
            with st.spinner("Thinking..."):
                ans = chatbot_response(text, st.session_state.lang_pref)
            st.success(f"🤖 **Answer:** {ans}")
            speak_text(ans, "Hindi" if detect_language(ans) == "Hindi" else "English")
        else:
            st.error("Could not understand audio.")
    text_q = st.text_input("Or type your question", key="chat_text_popover")
    if text_q:
        st.markdown(f"🗣️ **You:** {text_q}")
        with st.spinner("Thinking..."):
            ans = chatbot_response(text_q, st.session_state.lang_pref)
        st.success(f"🤖 **Answer:** {ans}")
        speak_text(ans, "Hindi" if detect_language(ans) == "Hindi" else "English")

with st.expander("🚀 Future Scope"):
    st.write("""
- 📱 Mobile app for rural accessibility  
- 🌐 Regional language expansion (10+ languages)  
- 📡 Live satellite + weather integration  
- 🛒 Direct farmer-to-market marketplace  
""")