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
if "selected_feature" not in st.session_state:
    st.session_state.selected_feature = None

# ========== LANDING PAGE (fixed image URL) ==========
if not st.session_state.entered_app:
    st.markdown("""
    <style>
        .main > div { padding: 0rem; }
        .stApp { background: linear-gradient(145deg, #2d6a4f, #1b4332) !important; }
        .landing-wrapper {
            position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background-image: url("https://seedballs.in/cdn/shop/articles/farmers_day.jpg?v%3D1766078534%26width%3D500&tbnid=RlsNKxP2FS9MqM&vet=1&imgrefurl=https://seedballs.in/blogs/blog/farmers-day-a-powerful-tribute-to-the-heroes-who-feed-the-world?srsltid%3DAfmBOopnwkDKXlplhKwnEADvnfam6_i_f2Sn9o2cIoE2-xl-FURpeHvw&docid=76GBYt0Qf-3NPM&w=500&h=750&hl=en-IN&source=sh/x/im/m1/4&kgs=075546ed03e1bd58&utm_source=sh/x/im/m1/4");
            background-size: cover; background-position: center;
            display: flex; flex-direction: column; justify-content: center; align-items: center;
            text-align: center; color: white; font-family: 'Inter', sans-serif; z-index: 999;
        }
        .landing-wrapper::before {
            content: ""; position: absolute; top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(0,0,0,0.4); z-index: -1;
        }
        .landing-title { font-size: 3rem; font-weight: 700; margin-bottom: 0.5rem; text-shadow: 2px 2px 4px rgba(0,0,0,0.5); }
        .landing-tagline { font-size: 1.5rem; font-weight: 500; margin-bottom: 3rem; text-shadow: 1px 1px 2px rgba(0,0,0,0.5); }
        .stButton { position: fixed; bottom: 80px; left: 0; right: 0; text-align: center; z-index: 1000; }
        .stButton > button {
            background-color: #f4a261; color: #1b4332; border: none; border-radius: 60px;
            padding: 12px 32px; font-size: 1.2rem; font-weight: bold; width: auto; min-width: 200px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.2); transition: 0.2s;
        }
        .stButton > button:hover { background-color: #e76f51; transform: scale(1.02); }
    </style>
    <div class="landing-wrapper">
        <div class="landing-title">🌾 KisanMitra</div>
        <div class="landing-tagline">Har Kisan ka Digital Saathi</div>
    </div>
    """, unsafe_allow_html=True)
    if st.button("Start Now", use_container_width=False):
        st.session_state.entered_app = True
        st.rerun()
    st.stop()

# ========== MAIN APP BACKGROUND ==========
st.markdown("""
<style>
    .stApp { background: linear-gradient(180deg, #e8f5e9 0%, #c8e6c9 100%) !important; font-family: 'Inter', sans-serif; overflow: auto; }
    [data-testid="stSidebar"] { background: #d9c8a5 !important; }
    [data-testid="stSidebar"] * { color: #2f2516 !important; }
    .main > div { padding: 0rem 1rem; }
    .km-earth-card { background: #fffaf0; border: 1px solid #dcc9a2; border-radius: 18px; padding: 0.8rem 1rem; margin-bottom: 1rem; }
    .user-msg, .bot-msg { background: white; border-radius: 20px; padding: 0.8rem; margin: 0.8rem 0; border-left: 5px solid #7a5c2e; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }
    /* Style for feature cards (when using buttons) – not used in new grid, but keep */
    .stButton > button {
        background-color: #f1f8e9 !important;
        border: 1px solid #a5d6a7 !important;
        border-radius: 20px !important;
        padding: 1rem 0.5rem !important;
        height: auto !important;
        white-space: normal !important;
        color: #2e7d32 !important;
        font-weight: normal !important;
        transition: 0.2s;
    }
    .stButton > button:hover {
        background-color: #e8f5e9 !important;
        transform: translateY(-4px);
        box-shadow: 0 8px 20px rgba(0,0,0,0.1);
    }
</style>
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
            "sidebar_clear": "Clear History",
            "dashboard_title": "🌾 KisanMitra",
            "dashboard_subtitle": "AI-powered smart farming assistant",
            "choose_service": "🌟 Choose a Service",
            "voice_title": "Voice Assistant", "voice_desc": "Ask farming questions by voice",
            "market_title": "Market Prices", "market_desc": "Live mandi rates",
            "weather_title": "Weather Intelligence", "weather_desc": "Forecast & alerts",
            "soil_title": "Soil Analysis", "soil_desc": "Upload photo or PDF",
            "advice_title": "AI Advice", "advice_desc": "Personalized recommendations",
            "rotation_title": "Crop Rotation", "rotation_desc": "Plan your next crop",
            "women_title": "Women Empowerment", "women_desc": "Schemes & safety",
            "schemes_title": "Govt Schemes", "schemes_desc": "All government schemes",
            "kvk_title": "KVK Support", "kvk_desc": "Find nearest KVK",
            "nabard_title": "NABARD & RRB", "nabard_desc": "Loans & banking",
            "back_button": "← Back to Dashboard",
            "footer": "🌾 KisanMitra – Your Voice Farming Companion",
            "voice_header": "Ask by Voice", "voice_stop": "Stop Recording",
            "voice_stopped": "Recording stopped. Click 'Enable Recording' to ask again.",
            "voice_enable": "Enable Recording", "voice_placeholder": "Tap to record your question",
            "voice_transcribing": "Transcribing...", "voice_thinking": "Getting advice...",
            "voice_error": "Could not understand. Please speak clearly.",
            "voice_type_header": "Or type your question", "voice_type_placeholder": "Type here",
            "voice_ask_btn": "Ask",
            "market_header": "Mandi Prices", "market_info": "Live API ready – showing sample prices.",
            "market_commodity": "Commodity (e.g., Wheat, Rice)", "market_state": "State", "market_btn": "Get Price",
            "weather_header": "Weather & Alerts", "weather_gps_info": "📍 Use 'Use My Location' and allow browser GPS.",
            "weather_or": "— OR —", "weather_city": "Enter district/city name", "weather_source": "Select weather source",
            "weather_manual": "Manual City", "weather_gps": "Current Location", "weather_btn": "Get Weather",
            "weather_refresh": "Refresh Weather", "weather_today": "Today", "weather_tomorrow": "Tomorrow",
            "soil_header": "Soil Health Analysis", "soil_photo_option": "Option 1: Upload a photo of your soil",
            "soil_photo_btn": "Analyze Soil from Photo", "soil_pdf_option": "Option 2: Upload soil lab report (PDF)",
            "soil_pdf_btn": "Analyze PDF Report", "soil_manual_option": "Option 3: Enter test results manually",
            "soil_manual_btn": "Get Manual Advice",
            "personalized_header": "Personalized Farming Advice",
            "crop_damage_header": "🌾 Crop Damage Recovery (Heavy Rain / Waterlogging)",
            "crop_damage_crop": "Affected crop", "crop_damage_type": "Type of damage",
            "crop_damage_btn": "Get Recovery Advice", "personalized_warning": "Please fill your Farmer Profile in the sidebar first.",
            "personalized_question": "What specific advice do you need? (e.g., sowing time, pest control, fertilizer)",
            "personalized_btn": "Get Personalized Advice",
            "rotation_header": "Crop Rotation Advisor", "rotation_prev": "Previous crop grown",
            "rotation_next": "Crop you want to grow next", "rotation_btn": "Get Rotation Advice",
            "rotation_suitable": "✅ Good rotation choice!", "rotation_unsuitable": "⚠️ {advice}",
            "soil_advice_label": "🌱 Soil advice: {soil}",
            "women_header": "Women Farmer Empowerment", "safety_tip_label": "Safety Tip of the Day",
            "read_tip": "Read Tip Aloud", "emergency_header": "Emergency & Helpline Numbers",
            "farming_ideas_header": "Small‑Scale Farming for Women",
            "govt_schemes_women": "Government Schemes for Women",
            "schemes_header": "Government Schemes for Farmers", "schemes_filter": "Filter by Category:",
            "kvk_header": "Krishi Vigyan Kendra (KVK)", "kvk_caption": "Find your nearest KVK centre and get expert agricultural support.",
            "kvk_district": "Enter your district name:", "kvk_btn": "Find KVK",
            "kvk_info": "KVK centres provide free soil testing, seed distribution, training, and crop‑specific advice.",
            "nabard_header": "🏦 NABARD & Regional Rural Banks (RRB)", "nabard_caption": "Empowering rural India with credit, schemes, and local banking support.",
            "nabard_ai_title": "🤖 Find Schemes for You (AI-Powered)", "nabard_ai_desc": "Tell us about your farm – we'll recommend relevant NABARD schemes and RRB services.",
            "nabard_crop": "Main crop(s)", "nabard_land": "Land size (acres)", "nabard_location": "State/District",
            "nabard_submit": "Get Personalized Advice", "nabard_schemes_title": "📚 NABARD Schemes (Categorised)",
            "nabard_kcc_title": "💰 Kisan Credit Card & Loan Benefits", "nabard_kcc_desc": "Covers all cultivation expenses. Visit any bank or RRB.",
            "nabard_loan_amount": "Loan amount (₹)", "nabard_saving": "Yearly Saving (approx)",
            "nabard_rrb_title": "🏦 Regional Rural Banks (RRBs)", "nabard_rrb_desc": "Find RRB contacts by state (example data).",
            "nabard_select_state": "Select state", "nabard_show_rrb": "Show Example RRB",
            "nabard_updates": "🔔 Live Updates & Grievance",
            "future_scope": "🚀 Future Scope",
        },
        "hi": {
            "sidebar_title": "किसान मित्र", "sidebar_lang": "भाषा", "sidebar_profile": "किसान प्रोफ़ाइल",
            "sidebar_profile_placeholder": "आपका विवरण (फसलें, ज़मीन, स्थान)", "sidebar_history": "बातचीत इतिहास",
            "sidebar_clear": "इतिहास साफ़ करें",
            "dashboard_title": "🌾 किसान मित्र",
            "dashboard_subtitle": "एआई-संचालित स्मार्ट खेती सहायक",
            "choose_service": "🌟 सेवा चुनें",
            "voice_title": "आवाज़ सहायक", "voice_desc": "आवाज़ से खेती के सवाल पूछें",
            "market_title": "मंडी भाव", "market_desc": "लाइव मंडी दरें",
            "weather_title": "मौसम जानकारी", "weather_desc": "पूर्वानुमान और अलर्ट",
            "soil_title": "मिट्टी विश्लेषण", "soil_desc": "फोटो या PDF अपलोड करें",
            "advice_title": "एआई सलाह", "advice_desc": "व्यक्तिगत सिफारिशें",
            "rotation_title": "फसल चक्र", "rotation_desc": "अगली फसल की योजना बनाएं",
            "women_title": "महिला सशक्तिकरण", "women_desc": "योजनाएं और सुरक्षा",
            "schemes_title": "सरकारी योजनाएँ", "schemes_desc": "सभी सरकारी योजनाएँ",
            "kvk_title": "केवीके सहायता", "kvk_desc": "निकटतम केवीके खोजें",
            "nabard_title": "नाबार्ड और आरआरबी", "nabard_desc": "ऋण और बैंकिंग",
            "back_button": "← डैशबोर्ड पर वापस",
            "footer": "🌾 किसान मित्र – आपका आवाज़ी खेती साथी",
            "voice_header": "आवाज़ से पूछें", "voice_stop": "रिकॉर्डिंग बंद करें",
            "voice_stopped": "रिकॉर्डिंग बंद की गई। फिर से पूछने के लिए 'रिकॉर्डिंग सक्षम करें' पर क्लिक करें।",
            "voice_enable": "रिकॉर्डिंग सक्षम करें", "voice_placeholder": "अपना सवाल रिकॉर्ड करें",
            "voice_transcribing": "लिख रहा हूँ...", "voice_thinking": "जवाब दे रहा हूँ...",
            "voice_error": "समझ नहीं आया। कृपया साफ़ बोलें।",
            "voice_type_header": "या लिखकर पूछें", "voice_type_placeholder": "यहाँ लिखें", "voice_ask_btn": "पूछें",
            "market_header": "मंडी भाव", "market_info": "लाइव API तैयार – नमूना मूल्य दिखा रहे हैं।",
            "market_commodity": "फसल (जैसे, गेहूं, धान)", "market_state": "राज्य", "market_btn": "भाव देखें",
            "weather_header": "मौसम और अलर्ट", "weather_gps_info": "📍 'मेरा स्थान उपयोग करें' का उपयोग करें और ब्राउज़र को अनुमति दें।",
            "weather_or": "— अथवा —", "weather_city": "जिला/शहर का नाम लिखें", "weather_source": "मौसम स्रोत चुनें",
            "weather_manual": "मैन्युअल शहर", "weather_gps": "वर्तमान स्थान", "weather_btn": "मौसम देखें",
            "weather_refresh": "मौसम ताज़ा करें", "weather_today": "आज", "weather_tomorrow": "कल",
            "soil_header": "मिट्टी स्वास्थ्य जांच", "soil_photo_option": "विकल्प 1: मिट्टी की फोटो अपलोड करें",
            "soil_photo_btn": "फोटो से मिट्टी जांचें", "soil_pdf_option": "विकल्प 2: मिट्टी लैब रिपोर्ट (PDF) अपलोड करें",
            "soil_pdf_btn": "PDF रिपोर्ट जांचें", "soil_manual_option": "विकल्प 3: मैन्युअल रूप से मान दर्ज करें",
            "soil_manual_btn": "मैन्युअल सलाह लें",
            "personalized_header": "व्यक्तिगत खेती सलाह",
            "crop_damage_header": "🌾 फसल क्षति रिकवरी (भारी बारिश / जलभराव)",
            "crop_damage_crop": "प्रभावित फसल", "crop_damage_type": "क्षति का प्रकार",
            "crop_damage_btn": "रिकवरी सलाह लें", "personalized_warning": "कृपया पहले साइडबार में किसान प्रोफ़ाइल भरें।",
            "personalized_question": "आपको किस सलाह की ज़रूरत है? (जैसे, बुवाई का समय, कीट नियंत्रण, खाद)",
            "personalized_btn": "व्यक्तिगत सलाह लें",
            "rotation_header": "फसल चक्र सलाहकार", "rotation_prev": "पिछली उगाई गई फसल",
            "rotation_next": "अगली फसल जो आप उगाना चाहते हैं", "rotation_btn": "फसल चक्र सलाह लें",
            "rotation_suitable": "✅ अच्छा फसल चक्र विकल्प!", "rotation_unsuitable": "⚠️ {advice}",
            "soil_advice_label": "🌱 मिट्टी सलाह: {soil}",
            "women_header": "महिला किसान सशक्तिकरण", "safety_tip_label": "दिन की सुरक्षा टिप",
            "read_tip": "टिप सुनें", "emergency_header": "आपातकालीन एवं हेल्पलाइन नंबर",
            "farming_ideas_header": "महिलाओं के लिए छोटे पैमाने पर खेती के विचार",
            "govt_schemes_women": "महिला किसानों के लिए सरकारी योजनाएँ",
            "schemes_header": "किसानों के लिए सरकारी योजनाएँ", "schemes_filter": "श्रेणी से छाँटें:",
            "kvk_header": "कृषि विज्ञान केंद्र (केवीके)", "kvk_caption": "अपना निकटतम केवीके केंद्र खोजें और विशेषज्ञ कृषि सहायता प्राप्त करें।",
            "kvk_district": "अपने जिले का नाम लिखें:", "kvk_btn": "केवीके खोजें",
            "kvk_info": "केवीके केंद्र निःशुल्क मिट्टी परीक्षण, बीज वितरण, प्रशिक्षण और फसल-विशिष्ट सलाह प्रदान करते हैं।",
            "nabard_header": "🏦 नाबार्ड और क्षेत्रीय ग्रामीण बैंक (RRB)", "nabard_caption": "ग्रामीण भारत को ऋण, योजनाओं और स्थानीय बैंकिंग समर्थन से सशक्त बनाना।",
            "nabard_ai_title": "🤖 अपने लिए योजनाएँ खोजें (AI-संचालित)", "nabard_ai_desc": "अपने खेत के बारे में बताएं – हम आपको प्रासंगिक नाबार्ड योजनाओं और आरआरबी सेवाओं की सिफारिश करेंगे।",
            "nabard_crop": "मुख्य फसल(ें)", "nabard_land": "भूमि का आकार (एकड़)", "nabard_location": "राज्य/जिला",
            "nabard_submit": "व्यक्तिगत सलाह लें", "nabard_schemes_title": "📚 नाबार्ड योजनाएँ (वर्गीकृत)",
            "nabard_kcc_title": "💰 किसान क्रेडिट कार्ड और ऋण लाभ", "nabard_kcc_desc": "सभी खेती खर्चों को कवर करता है। किसी भी बैंक या RRB पर जाएं।",
            "nabard_loan_amount": "ऋण राशि (₹)", "nabard_saving": "अनुमानित वार्षिक बचत",
            "nabard_rrb_title": "🏦 क्षेत्रीय ग्रामीण बैंक (RRBs)", "nabard_rrb_desc": "राज्य के अनुसार RRB संपर्क खोजें (उदाहरण डेटा)।",
            "nabard_select_state": "राज्य चुनें", "nabard_show_rrb": "उदाहरण RRB दिखाएं",
            "nabard_updates": "🔔 लाइव अपडेट और शिकायत",
            "future_scope": "🚀 भविष्य का दायरा",
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

# ---------- Helper Functions (unchanged) ----------
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

# ========== FEATURE FUNCTIONS ==========
def feature_voice_assistant():
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
                with st.spinner(t("voice_thinking")):
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
            ans = get_ai_response(txt_q, st.session_state.lang_pref)
            st.markdown(f'<div class="user-msg">🗣️ <strong>You:</strong> {txt_q}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="bot-msg">🤖 <strong>KisanMitra:</strong> {ans}</div>', unsafe_allow_html=True)
            st.session_state.history.append({"q": txt_q, "a": ans})
            speak_text(ans, "Hindi" if detect_language(ans) == "Hindi" else "English")

def feature_market_prices():
    st.header(t("market_header"))
    st.info(t("market_info"))
    col1, col2 = st.columns(2)
    with col1: commodity = st.text_input(t("market_commodity"))
    with col2: state = st.text_input(t("market_state"), "Uttar Pradesh")
    if st.button(t("market_btn")):
        if commodity:
            p = get_mandi_price(commodity, state)
            st.success(f"**{p['commodity']}** in {p['market']}, {p['state']}")
            st.metric("Price per quintal", f"₹{p['price']}")
            st.caption(f"Source: {p['source']}")

def feature_weather():
    st.header(t("weather_header"))
    st.markdown(f'<div class="km-earth-card">{t("weather_gps_info")}</div>', unsafe_allow_html=True)
    st.markdown(GPS_HTML, unsafe_allow_html=True)
    st.caption(t("weather_or"))
    if "gps_lat" in st.query_params and "gps_lon" in st.query_params:
        lat = st.query_params.get("gps_lat"); lon = st.query_params.get("gps_lon")
        try:
            lat = float(lat); lon = float(lon)
            city = get_city_from_coords(lat, lon)
            st.session_state.weather_city_from_gps = city
            st.success(f"📍 Location detected: {city}")
            st.query_params.clear()
            st.rerun()
        except: pass
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
            st.error("❌ GPS location not available.")
        else:
            forecast = get_weather_forecast(city)
            st.session_state.last_weather_data = {"city": city, "forecast": forecast}
            st.rerun()
    if st.button(t("weather_refresh"), key="refresh_weather"):
        if weather_source == t("weather_gps") and not st.session_state.weather_city_from_gps:
            st.error("❌ GPS location not available.")
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
            st.markdown(f"🌡️ {forecast['today']['temp']}°C, {forecast['today']['condition']}<br>💡 {forecast['today']['advice']}", unsafe_allow_html=True)
        with col2:
            st.write(f"**{t('weather_tomorrow')}**")
            st.markdown(f"🌡️ {forecast['tomorrow']['temp']}°C, {forecast['tomorrow']['condition']}<br>💡 {forecast['tomorrow']['advice']}", unsafe_allow_html=True)
        alert_level, advice_list = get_weather_alert(forecast)
        if alert_level == "red":
            st.error("🚨 Severe Weather Alert!")
        elif alert_level == "orange":
            st.warning("⚠️ Weather Advisory")
        for adv in advice_list:
            st.write(f"- {adv}")

def feature_soil_health():
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

def feature_personalized_advice():
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

def feature_crop_rotation():
    st.header(t("rotation_header"))
    col1, col2 = st.columns(2)
    with col1: previous_crop = st.selectbox(t("rotation_prev"), ["Sugarcane","Wheat","Rice","Potato","Tomato","Maize"])
    with col2: next_crop = st.selectbox(t("rotation_next"), ["Wheat","Mustard","Rice","Potato","Tomato","Maize","Pulses","Onion"])
    if st.button(t("rotation_btn")):
        adv = get_crop_rotation_advice(previous_crop, next_crop)
        if adv["suitable"]:
            st.success(t("rotation_suitable"))
        else:
            st.warning(t("rotation_unsuitable").format(advice=adv['advice']))
        st.info(t("soil_advice_label").format(soil=adv['soil']))
        with st.spinner("Getting detailed AI advice..."):
            prompt = f"Farmer grew {previous_crop} and wants to grow {next_crop}. Give soil management and fertilizer advice."
            detailed = model.generate_content(prompt)
            st.markdown(f'<div class="bot-msg">🤖 AI Suggestion:<br>{detailed.text}</div>', unsafe_allow_html=True)

def feature_women_empowerment():
    st.header(t("women_header"))
    safety_tips = [
        "🌾 Always inform a family member before going to the field alone.",
        "📞 Save local police and women’s helpline numbers on speed dial.",
        "👭 Form a group of women farmers in your village for mutual support.",
        "🌿 Keep a basic first‑aid kit in your farming bag.",
        "🚜 Learn about government schemes for women farmers – ask KisanMitra!"
    ]
    tip_idx = datetime.datetime.now().day % len(safety_tips)
    st.info(f"💡 **{t('safety_tip_label')}:** {safety_tips[tip_idx]}")
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

def feature_government_schemes():
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

def feature_kvk():
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

def feature_nabard():
    st.header(t("nabard_header"))
    st.caption(t("nabard_caption"))
    with st.expander(t("nabard_ai_title"), expanded=False):
        st.markdown(t("nabard_ai_desc"))
        with st.form("nabard_form"):
            col1, col2 = st.columns(2)
            with col1: crop_adv = st.text_input(t("nabard_crop"), placeholder="e.g., Wheat, Rice")
            with col2: land_adv = st.text_input(t("nabard_land"), placeholder="e.g., 2, 5")
            location_adv = st.text_input(t("nabard_location"), placeholder="e.g., Uttar Pradesh")
            submitted = st.form_submit_button(t("nabard_submit"))
            if submitted:
                with st.spinner("Analyzing schemes..."):
                    prompt = f"""Based on farmer profile: crops={crop_adv}, land={land_adv}, location={location_adv}. Recommend relevant NABARD schemes (KCC, Interest Subvention, MKSP, AMI, FPO) and RRB services. Keep short."""
                    try:
                        response = model.generate_content(prompt)
                        st.success("**AI Recommendation:**")
                        st.markdown(f'<div class="bot-msg">🤖 {response.text}</div>', unsafe_allow_html=True)
                    except: st.error("AI error.")
    with st.expander(t("nabard_schemes_title"), expanded=False):
        nabard_schemes = {
            "Credit & Loans": [{"name": "Kisan Credit Card (KCC)", "desc": "Flexible credit for cultivation.", "link": "https://www.nabard.org/content.aspx?id=566"}],
            "Interest Subvention": [{"name": "Interest Subvention Scheme", "desc": "Short‑term loans at 7% interest.", "link": "https://www.nabard.org/auth/writereaddata/File/Interest%20Subvention%20Scheme.pdf"}],
            "Women Farmers": [{"name": "Mahila Kisan Sashaktikaran Pariyojana (MKSP)", "desc": "Skill development for women.", "link": "https://nrlm.gov.in/"}]
        }
        for cat, schemes in nabard_schemes.items():
            st.subheader(cat)
            for sch in schemes:
                st.markdown(f"**{sch['name']}** – {sch['desc']} [🔗]({sch['link']})")
    with st.expander(t("nabard_kcc_title"), expanded=False):
        st.subheader("Kisan Credit Card (KCC)")
        st.markdown(t("nabard_kcc_desc"))
        loan_amt = st.number_input(t("nabard_loan_amount"), min_value=10000, max_value=300000, step=10000, value=100000)
        yearly_saving = (loan_amt * 2) / 100
        st.metric(t("nabard_saving"), f"₹{yearly_saving:,.2f}")
    with st.expander(t("nabard_rrb_title"), expanded=False):
        st.markdown(t("nabard_rrb_desc"))
        state_rrb = st.selectbox(t("nabard_select_state"), ["Uttar Pradesh", "Bihar", "Madhya Pradesh"])
        if st.button(t("nabard_show_rrb")):
            if state_rrb == "Uttar Pradesh":
                st.success("Prathama UP Gramin Bank – 1800‑180‑1234")
            elif state_rrb == "Bihar":
                st.success("Dakshin Bihar Gramin Bank – 0612-2221234")
            else:
                st.success("Madhyanchal Gramin Bank – 0755-2551234")
    with st.expander(t("nabard_updates"), expanded=False):
        st.markdown("[NABARD WhatsApp Channel](https://wa.me/91XXXXXXXXXX?text=Join) | [NIVARAN Portal](https://www.nabard.org/content.aspx?id=607)")

# ========== DASHBOARD (HTML/CSS Grid – forces 2 columns on mobile) ==========
def show_dashboard():
    st.markdown(f"""
    <div style='background:#e8f5e9;padding:0.8rem 1.2rem;border-radius:20px;
    border:1px solid #a5d6a7;margin-bottom:1rem'>
        <h3 style='margin:0;color:#2e7d32;'>{t('dashboard_title')}</h3>
        <p style='margin:0;color:#558b2f;font-size:0.85rem;'>{t('dashboard_subtitle')}</p>
    </div>
    """, unsafe_allow_html=True)
    st.markdown(f"### {t('choose_service')}")
    
    features = [
        (t("voice_title"), "🎤", t("voice_desc"), "voice"),
        (t("market_title"), "💰", t("market_desc"), "market"),
        (t("weather_title"), "🌤️", t("weather_desc"), "weather"),
        (t("soil_title"), "🧪", t("soil_desc"), "soil"),
        (t("advice_title"), "📝", t("advice_desc"), "advice"),
        (t("rotation_title"), "🔄", t("rotation_desc"), "rotation"),
        (t("women_title"), "🚺", t("women_desc"), "women"),
        (t("schemes_title"), "📜", t("schemes_desc"), "schemes"),
        (t("kvk_title"), "🌾", t("kvk_desc"), "kvk"),
        (t("nabard_title"), "🏦", t("nabard_desc"), "nabard"),
    ]
    
    # Build HTML grid – 2 columns, auto rows
    grid_html = '<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.8rem;">'
    for title, icon, desc, key in features:
        # Create a clickable card that sets a URL parameter
        grid_html += f'''
        <a href="?feature={key}" style="text-decoration: none;">
            <div style="background:#f1f8e9; border:1px solid #a5d6a7; border-radius:20px; padding:1rem 0.5rem; text-align:center; cursor:pointer; transition:0.2s;">
                <div style="font-size:2rem;">{icon}</div>
                <div style="font-weight:600; margin:0.5rem 0 0.2rem; color:#2e7d32;">{title}</div>
                <div style="font-size:0.75rem; color:#558b2f;">{desc}</div>
            </div>
        </a>
        '''
    grid_html += '</div>'
    st.markdown(grid_html, unsafe_allow_html=True)
    st.markdown("---")
    st.caption(t("footer"))

# ========== MAIN FLOW (with query parameter handling) ==========
# Check if a feature was selected via URL parameter
if "feature" in st.query_params:
    selected = st.query_params["feature"]
    if selected in ["voice", "market", "weather", "soil", "advice", "rotation", "women", "schemes", "kvk", "nabard"]:
        st.session_state.selected_feature = selected
        # Clear the URL parameter to avoid re‑selection on refresh
        st.query_params.clear()

if st.session_state.selected_feature is None:
    show_dashboard()
else:
    feature_map = {
        "voice": feature_voice_assistant,
        "market": feature_market_prices,
        "weather": feature_weather,
        "soil": feature_soil_health,
        "advice": feature_personalized_advice,
        "rotation": feature_crop_rotation,
        "women": feature_women_empowerment,
        "schemes": feature_government_schemes,
        "kvk": feature_kvk,
        "nabard": feature_nabard,
    }
    if st.button(t("back_button"), use_container_width=False):
        st.session_state.selected_feature = None
        st.rerun()
    feature_map[st.session_state.selected_feature]()

# ========== FLOATING CHATBOT ==========
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

with st.expander(t("future_scope")):
    st.write("""
- 📱 Mobile app for rural accessibility  
- 🌐 Regional language expansion (10+ languages)  
- 📡 Live satellite + weather integration  
- 🛒 Direct farmer-to-market marketplace  
""")