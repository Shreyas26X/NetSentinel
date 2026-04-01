import streamlit as st
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
from groq import Groq

# ------------------ APP CONFIG ------------------
st.set_page_config(page_title="NetSentinel", layout="wide")
st.title("🔐 NetSentinel – AI-Based Network Intrusion Detection System")

# Dataset path
DATA_FILE = "dataset/Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv"

# ------------------ DATA LOADING ------------------
@st.cache_data
def load_data(filepath):
    """Load and clean dataset"""
    try:
        df = pd.read_csv(filepath, nrows=15000)
        df.columns = df.columns.str.strip()
        df.replace([np.inf, -np.inf], np.nan, inplace=True)
        df.dropna(inplace=True)
        return df
    except FileNotFoundError:
        return None


# ------------------ MODEL TRAINING ------------------
def train_model(df):
    """Train Random Forest model"""
    features = [
        'Flow Duration', 'Total Fwd Packets', 'Total Backward Packets',
        'Total Length of Fwd Packets', 'Fwd Packet Length Max',
        'Flow IAT Mean', 'Flow IAT Std', 'Flow Packets/s'
    ]
    target = 'Label'

    X = df[features]
    y = df[target]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.3, random_state=42
    )

    model = RandomForestClassifier(
        n_estimators=10,
        max_depth=10,
        random_state=42
    )

    model.fit(X_train, y_train)
    accuracy = accuracy_score(y_test, model.predict(X_test))

    return model, accuracy, X_test, y_test


# ------------------ PREDICTION ------------------
def predict_packet(model, packet):
    """Predict if packet is benign or attack"""
    return model.predict([packet])[0]


# ------------------ AI EXPLANATION ------------------
def generate_explanation(api_key, packet, prediction):
    """Generate explanation using Groq API"""
    try:
        client = Groq(api_key=api_key)

        prompt = f"""
        You are a cybersecurity analyst.
        A network packet was classified as: {prediction}

        Packet Details:
        {packet.to_string()}

        Explain:
        1. Why this packet is classified as {prediction}
        2. Keep explanation simple and beginner-friendly
        """

        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.6,
        )

        return completion.choices[0].message.content

    except Exception as e:
        return f"API Error: {e}"


# ------------------ SIDEBAR ------------------
st.sidebar.header("⚙️ Settings")
api_key = st.sidebar.text_input("Groq API Key", type="password")

# ------------------ LOAD DATA ------------------
df = load_data(DATA_FILE)

if df is None:
    st.error("Dataset not found. Place CSV file inside 'dataset/' folder.")
    st.stop()

st.sidebar.success(f"Dataset Loaded: {len(df)} rows")

# ------------------ TRAIN MODEL ------------------
if st.sidebar.button("Train Model"):
    with st.spinner("Training model..."):
        model, accuracy, X_test, y_test = train_model(df)

        st.session_state['model'] = model
        st.session_state['X_test'] = X_test
        st.session_state['y_test'] = y_test

        st.sidebar.success(f"Model Trained | Accuracy: {accuracy:.2%}")


# ------------------ MAIN DASHBOARD ------------------
st.header("📊 Threat Analysis Dashboard")

if 'model' in st.session_state:

    # Capture random packet
    if st.button("🎲 Capture Random Packet"):
        idx = np.random.randint(0, len(st.session_state['X_test']))
        st.session_state['packet'] = st.session_state['X_test'].iloc[idx]
        st.session_state['actual'] = st.session_state['y_test'].iloc[idx]

    if 'packet' in st.session_state:
        packet = st.session_state['packet']

        col1, col2 = st.columns(2)

        # Display packet data
        with col1:
            st.subheader("📦 Packet Data")
            st.dataframe(packet)

        # Prediction result
        with col2:
            st.subheader("🔍 Detection Result")

            prediction = predict_packet(st.session_state['model'], packet)

            if prediction == "BENIGN":
                st.success("SAFE (BENIGN)")
            else:
                st.error(f"🚨 ATTACK DETECTED ({prediction})")

            st.caption(f"Actual Label: {st.session_state['actual']}")

            st.markdown("---")

            # AI explanation
            if st.button("Explain using AI"):
                if not api_key:
                    st.warning("Please enter your Groq API key")
                else:
                    explanation = generate_explanation(api_key, packet, prediction)
                    st.info(explanation)

else:
    st.info("Train the model using the sidebar to begin analysis.")
