import streamlit as st
import requests
import google.generativeai as genai
import io
import speech_recognition as sr
from PIL import Image
import datetime
import PyPDF2
import json

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

# ========== CONFIGURE GEMINI (FINAL) ==========
try:
    genai.configure(api_key=GEMINI_API_KEY)
    
    # Use a model from your available list
    MODEL_NAME = "models/gemini-3.1-flash-lite-preview"
    
    model = genai.GenerativeModel(MODEL_NAME)
    vision_model = genai.GenerativeModel(MODEL_NAME)
    
    # Quick test
    test_response = model.generate_content("Say 'OK'")
    if test_response:
        st.success("✅ Gemini API ready!")
    else:
        st.error("❌ Model test failed.")
        st.stop()
        
except Exception as e:
    st.error(f"❌ Gemini error: {e}")
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
if "chat_listen" not in st.session_state:
    st.session_state.chat_listen = False
if "chat_query" not in st.session_state:
    st.session_state.chat_query = ""
if "popover_query" not in st.session_state:
    st.session_state.popover_query = ""

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

def get_weather_forecast(city):
    return {
        "today": {
            "temp": 32, "humidity": 65, "condition": "Sunny",
            "suitable": True, "advice": "Good day for sowing."
        },
        "tomorrow": {
            "temp": 28, "humidity": 80, "condition": "Light rain expected",
            "suitable": False, "advice": "Avoid spraying pesticides."
        }
    }

def get_farming_advice_for_weather(weather_data):
    advice = []
    if weather_data["temp"] > 35:
        advice.append("🌡️ High heat: Water crops early morning.")
    if weather_data["humidity"] > 75:
        advice.append("💧 High humidity: Watch for fungal diseases.")
    if "rain" in weather_data["condition"].lower():
        advice.append("☔ Rain expected: Harvest ripe crops today.")
    if weather_data["temp"] < 15:
        advice.append("❄️ Cold alert: Protect young plants.")
    return advice if advice else ["✅ Weather suitable for normal farming."]

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

# Crop rotation
CROP_ROTATION = {
    "sugarcane": {"next_crops": ["wheat", "mustard", "potato"], "advice": "Sugarcane depletes nitrogen. Grow wheat or mustard with extra nitrogen.", "soil_condition": "Phosphorus levels adequate. Add 20% more nitrogen."},
    "wheat": {"next_crops": ["rice", "maize", "pulses"], "advice": "Wheat leaves residual phosphorus. Good for legumes.", "soil_condition": "Reduce DAP by 25%."},
    "rice": {"next_crops": ["wheat", "mustard", "vegetables"], "advice": "Rice depletes zinc. Apply zinc sulfate before next crop.", "soil_condition": "Zinc deficiency likely. Add organic matter."},
    "potato": {"next_crops": ["maize", "onion", "cabbage"], "advice": "Potato depletes potassium. Add potash for next crop.", "soil_condition": "Potassium low. Use NPK 20:20:20."},
    "tomato": {"next_crops": ["beans", "peas", "cucumber"], "advice": "Tomato susceptible to same pests. Rotate with legumes.", "soil_condition": "Good for nitrogen-fixing crops."}
}

def get_crop_rotation_advice(previous_crop, next_crop):
    prev = previous_crop.lower()
    next_c = next_crop.lower()
    if prev in CROP_ROTATION:
        if next_c in CROP_ROTATION[prev]["next_crops"]:
            return {"suitable": True, "advice": CROP_ROTATION[prev]["advice"], "soil": CROP_ROTATION[prev]["soil_condition"]}
        else:
            return {"suitable": False, "advice": f"{previous_crop} to {next_crop} is not ideal. Recommended: {', '.join(CROP_ROTATION[prev]['next_crops'])}", "soil": "Consider soil testing."}
    return {"suitable": True, "advice": "Crop rotation is good for soil health.", "soil": "Add compost before sowing."}

# Chatbot response (must be defined before use)
def chatbot_response(user_input, lang="English"):
    prompt = f"""You are a helpful farming assistant chatbot for KisanMitra.
Response language: {lang}
User says: "{user_input}"
Give a short, friendly, helpful answer (max 2 sentences). Keep it warm and encouraging."""
    try:
        response = model.generate_content(prompt)
        return response.text
    except:
        return "Sorry, I'm having trouble right now. Please try again."

# Help response (optional)
def get_help_response(user_question):
    help_topics = {
        "gps": "To use GPS: Tap 'Use My Current Location' button. Allow location permission.",
        "voice": "Tap microphone button, speak clearly in Hindi or English.",
        "soil": "Upload a photo of soil or PDF lab report. AI will analyze.",
        "crop rotation": "Go to Crop Rotation tab. Select previous and next crop.",
        "weather": "Enter city name or use GPS. Get today + tomorrow forecast."
    }
    q_lower = user_question.lower()
    for key, answer in help_topics.items():
        if key in q_lower:
            return answer
    return "I can help with: GPS, voice, soil analysis, crop rotation, weather. What would you like to know?"

# GPS HTML (single definition)
GPS_HTML = """
<div id="gps-container" style="margin: 10px 0;">
    <button id="get-location" style="background-color:#4CAF50; color:white; padding:10px 20px; border:none; border-radius:30px; cursor:pointer; width:100%;">
        📍 Use My Current Location
    </button>
    <p id="location-status" style="margin-top:10px; color:#666; text-align:center;"></p>
</div>
<script>
    const btn = document.getElementById('get-location');
    const status = document.getElementById('location-status');
    btn.addEventListener('click', function() {
        if ('geolocation' in navigator) {
            status.innerHTML = "📍 Getting your location...";
            navigator.geolocation.getCurrentPosition(function(position) {
                const lat = position.coords.latitude;
                const lon = position.coords.longitude;
                status.innerHTML = "✅ Location captured! Getting weather...";
                const form = document.createElement('form');
                form.method = 'POST';
                form.action = '';
                const latInput = document.createElement('input');
                latInput.name = 'latitude';
                latInput.value = lat;
                const lonInput = document.createElement('input');
                lonInput.name = 'longitude';
                lonInput.value = lon;
                form.appendChild(latInput);
                form.appendChild(lonInput);
                document.body.appendChild(form);
                form.submit();
            }, function(error) {
                status.innerHTML = "❌ Could not get location. Please allow permission.";
            });
        } else {
            status.innerHTML = "❌ GPS not supported on this browser.";
        }
    });
</script>
"""

def get_city_from_coords(lat, lon):
    try:
        url = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=json"
        response = requests.get(url, headers={'User-Agent': 'KisanMitra'})
        data = response.json()
        city = data.get('address', {}).get('city') or data.get('address', {}).get('town') or data.get('address', {}).get('village')
        return city if city else "Your Location"
    except:
        return "Your Location"
# ========== MAIN TABS ==========
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([t("tab1"), t("tab2"), t("tab3"), t("tab4"), t("tab5"), "🔄 Crop Rotation"])


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
            
            # Auto-speak
            import json
            safe_answer = json.dumps(ans)
            speak_js = f"""
            <script>
                var utterance = new SpeechSynthesisUtterance({safe_answer});
                utterance.lang = '{'hi-IN' if st.session_state.lang_pref == "Hindi" else 'en-US'}';
                window.speechSynthesis.speak(utterance);
            </script>
            """
            st.components.v1.html(speak_js, height=0)
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
            
            # Auto-speak
            import json
            safe_answer = json.dumps(ans)
            speak_js = f"""
            <script>
                var utterance = new SpeechSynthesisUtterance({safe_answer});
                utterance.lang = '{'hi-IN' if st.session_state.lang_pref == "Hindi" else 'en-US'}';
                window.speechSynthesis.speak(utterance);
            </script>
            """
            st.components.v1.html(speak_js, height=0)

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

# ----- TAB 3: WEATHER (with GPS) -----
with tab3:
    st.header(t("weather_header"))
    
    # Add GPS button
    st.markdown(GPS_HTML, unsafe_allow_html=True)
    st.caption("— OR —")
    
    city = st.text_input(t("weather_city"), "Lucknow")
    
    # Handle GPS location from form submission
    if "latitude" in st.query_params and "longitude" in st.query_params:
        lat = st.query_params["latitude"]
        lon = st.query_params["longitude"]
        city = get_city_from_coords(lat, lon)
        st.success(f"📍 Location detected: {city}")
        # Auto-fetch weather
        with st.spinner("Fetching weather..."):
            w = get_weather(city)  # your existing get_weather function
        col1, col2, col3 = st.columns(3)
        col1.metric("Temperature", f"{w['temp']}°C")
        col2.metric("Humidity", f"{w['humidity']}%")
        col3.metric("Condition", w['description'].title())
        
    
    if st.button(t("weather_btn")):
        w = get_weather(city)
        col1, col2, col3 = st.columns(3)
        col1.metric("Temperature", f"{w['temp']}°C")
        col2.metric("Humidity", f"{w['humidity']}%")
        col3.metric("Condition", w['description'].title())
        st.session_state.weather_fetched = True
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

# ----- TAB 6: CROP ROTATION -----
with tab6:
    st.header("🔄 Crop Rotation Advisor")
    st.caption("Plan your next crop based on previous harvest")
    
    col1, col2 = st.columns(2)
    with col1:
        previous_crop = st.selectbox("Previous crop grown", 
            ["Sugarcane", "Wheat", "Rice", "Potato", "Tomato", "Maize"])
    with col2:
        next_crop = st.selectbox("Crop you want to grow next",
            ["Wheat", "Mustard", "Rice", "Potato", "Tomato", "Maize", "Pulses", "Onion"])
    
    if st.button("Get Rotation Advice"):
        advice = get_crop_rotation_advice(previous_crop, next_crop)
        
        if advice["suitable"]:
            st.success(f"✅ Good rotation choice!")
        else:
            st.warning(f"⚠️ {advice['advice']}")
        
        st.info(f"🌱 **Soil advice:** {advice['soil']}")
        
        # Also give Gemini-powered detailed advice
        with st.spinner("Getting detailed AI advice..."):
            prompt = f"Farmer grew {previous_crop} and wants to grow {next_crop}. Give soil management and fertilizer advice."
            detailed = model.generate_content(prompt)
            st.markdown(f'<div class="bot-msg">🤖 <strong>AI Suggestion:</strong><br>{detailed.text}</div>', unsafe_allow_html=True)


# ----- FOOTER -----
st.markdown("---")
st.caption(t("footer"))
# ========== FLOATING CHATBOT POPOVER (BOTTOM RIGHT) ==========
with st.popover("🤖", use_container_width=False):
    st.markdown("### 💬 KisanMitra Assistant")
    
    # Greeting in Hindi (spoken and displayed)
    greeting = "नमस्ते! मैं आपकी कैसे मदद कर सकता हूँ?"
    st.info(greeting)
    
    # Speak greeting automatically when popover opens
    safe_greet = json.dumps(greeting)
    greet_js = f"""
    <script>
        var u = new SpeechSynthesisUtterance({safe_greet});
        u.lang = 'hi-IN';
        window.speechSynthesis.speak(u);
    </script>
    """
    st.components.v1.html(greet_js, height=0)
    
    # Voice input (using st.audio_input)
    audio_val = st.audio_input("🎤 Speak your question", key="chat_audio_popover")
    if audio_val:
        with st.spinner("Transcribing..."):
            text = transcribe_audio(audio_val.getvalue())
        if text:
            st.session_state.popover_query = text
            st.rerun()
    
    # Text input as fallback
    text_q = st.text_input("Or type your question", key="chat_text_popover")
    if text_q:
        st.session_state.popover_query = text_q
        st.rerun()
    
    # Process query
    if "popover_query" in st.session_state and st.session_state.popover_query:
        q = st.session_state.popover_query
        with st.spinner("Thinking..."):
            ans = chatbot_response(q, st.session_state.lang_pref)
        st.success(f"🤖 {ans}")
        # Speak answer
        safe_ans = json.dumps(ans)
        speak_js = f"""
        <script>
            var u2 = new SpeechSynthesisUtterance({safe_ans});
            u2.lang = '{'hi-IN' if st.session_state.lang_pref == "Hindi" else 'en-US'}';
            window.speechSynthesis.speak(u2);
        </script>
        """
        st.components.v1.html(speak_js, height=0)
        # Clear query
        del st.session_state.popover_query