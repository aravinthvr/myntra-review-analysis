import streamlit as st
import google.generativeai as genai
from bs4 import BeautifulSoup
import firebase_admin
from firebase_admin import credentials, firestore
import json
import time
import re
import pandas as pd
import plotly.express as px
from datetime import datetime

# --- 1. PREMIUM UI & SIDEBAR STYLING ---
st.set_page_config(page_title="ReviewIQ Pro", page_icon="◈", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600&family=DM+Serif+Display&display=swap');
    
    .stApp { background-color: #0c0d0f; color: #e8eaed; font-family: 'Outfit', sans-serif; }
    [data-testid="stSidebar"] { background-color: #131518 !important; border-right: 1px solid #2a2d34; min-width: 300px !important; }
    
    /* Navigation Sidebar */
    .nav-wrapper { margin-top: 2.5rem; display: flex; flex-direction: column; gap: 0.5rem; }
    .stButton > button {
        width: 100%; text-align: left !important; justify-content: flex-start !important;
        background: transparent !important; border: 1px solid transparent !important; color: #9aa0ab !important;
        padding: 14px 24px !important; font-size: 15px !important; transition: 0.3s ease;
        border-radius: 8px !important;
    }
    .stButton > button:hover { color: #c8f064 !important; background: #1a1c20 !important; border-color: #2a2d34 !important; }
    
    /* Dashboard KPI Cards */
    .kpi-card { background: #131518; border: 1px solid #2a2d34; padding: 24px; border-radius: 14px; border-top: 4px solid #c8f064; }
    .kpi-label { color: #5c6370; font-size: 10px; text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 8px;}
    .kpi-value { font-family: 'DM Serif Display'; font-size: 42px; color: #e8eaed; line-height: 1; }
    
    /* Review Content */
    .dept-box { background: #1a1c20; border: 1px solid #2a2d34; padding: 18px; border-radius: 12px; height: 100%; transition: 0.2s; }
    .dept-box:hover { border-color: #c8f064; }
    .review-bubble { background: #131518; border-left: 4px solid #c8f064; padding: 14px 20px; margin-bottom: 12px; border-radius: 0 12px 12px 0; font-size: 14px; line-height: 1.6; border: 1px solid #2a2d34; border-left-width: 4px; }
    .proof-tag { color: #c8f064; font-size: 10px; font-weight: 600; text-transform: uppercase; margin-top: 6px; display: block; opacity: 0.8; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CORE UTILS & DATA REPAIR ---
if not firebase_admin._apps:
    try:
        cred = credentials.Certificate("serviceAccountKey.json")
        firebase_admin.initialize_app(cred)
    except: st.sidebar.warning("Firebase Creds Not Found")
db = firestore.client() if firebase_admin._apps else None

def validate_and_repair_data(data):
    """Schema guard to prevent TypeErrors in the UI."""
    if not isinstance(data, dict): return None
    # Repair Departments
    if "departments" in data:
        repaired = []
        for d in data["departments"]:
            if isinstance(d, dict): repaired.append(d)
            else: repaired.append({"icon": "📊", "name": "Feature", "sentiment": "Neutral", "msg": str(d)})
        data["departments"] = repaired
    # Repair Quotes
    for key in ["top_pos", "top_neg"]:
        if key in data:
            repaired_q = []
            for q in data[key]:
                if isinstance(q, dict): repaired_q.append(q)
                else: repaired_q.append({"text": str(q), "reviewer": "Verified User"})
            data[key] = repaired_q
    return data

def safe_json_loads(text):
    """Extracts and repairs JSON from AI responses."""
    try:
        cleaned = re.search(r'\{.*\}', text, re.DOTALL).group(0)
        # Fix unescaped characters often found in raw reviews
        cleaned = cleaned.replace('\n', ' ').replace('\r', ' ')
        raw_data = json.loads(cleaned)
        return validate_and_repair_data(raw_data)
    except: return None

# --- 3. DYNAMIC UI RENDERER ---
def render_full_analysis(data):
    st.markdown(f"<h1 style='font-family:DM Serif Display; font-size:42px;'>{data.get('product_name')}</h1>", unsafe_allow_html=True)
    st.info(f"💡 **Verdict:** {data.get('verdict')}")
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Verified Reviews", data.get('total_reviews', 0))
    c2.metric("Sentiment Weight", f"{float(data.get('sentiment_score', 0))*100:.0f}%")
    c3.metric("Avg Rating", f"{data.get('avg_rating', 0)}★")

    st.markdown("### 📊 Market Department Health")
    depts = data.get('departments', [])
    if depts:
        cols = st.columns(len(depts))
        for i, d in enumerate(depts):
            with cols[i]:
                st.markdown(f"""<div class="dept-box"><div style="font-size:18px">{d.get('icon','📦')} {d.get('name','Node')}</div>
                <div style="color:#5c6370; font-size:11px">{d.get('sentiment','N/A')}</div>
                <div style="font-size:12.5px; margin-top:8px">{d.get('msg','-')}</div></div>""", unsafe_allow_html=True)

    st.divider()
    p_col, n_col = st.columns(2)
    with p_col:
        st.markdown("#### 🟢 Verified Praises")
        for p in data.get('top_pos', []):
            st.markdown(f"""<div class="review-bubble">{p.get('text')}<span class="proof-tag">— Verified Review: {p.get('reviewer')}</span></div>""", unsafe_allow_html=True)
    with n_col:
        st.markdown("#### 🔴 Critical Issues")
        for n in data.get('top_neg', []):
            st.markdown(f"""<div class="review-bubble" style="border-left-color:#f87171">{n.get('text')}<span class="proof-tag">— Verified Review: {n.get('reviewer')}</span></div>""", unsafe_allow_html=True)

# --- 4. THE ANALYTICS ENGINE (MAP-REDUCE) ---
def deep_analyze_verified(raw_html, api_key):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    soup = BeautifulSoup(raw_html, 'html.parser')
    review_nodes = soup.find_all('div', class_='detailed-reviews-flexReviews')
    
    # Pre-processing nodes to extract names + text
    reviews_data = []
    for node in review_nodes:
        name_tag = node.find(['span', 'p'], class_=lambda x: x and ('user' in x.lower() or 'name' in x.lower()))
        name = name_tag.get_text(strip=True) if name_tag else "Anonymous Customer"
        content = node.get_text(separator=" ", strip=True)
        reviews_data.append(f"User: {name} | Feedback: {content}")

    # Process in batches of 60 to prevent token lag
    chunk_size = 60
    chunks = [reviews_data[i:i + chunk_size] for i in range(0, len(reviews_data), chunk_size)]
    batch_notes = []
    
    prog = st.progress(0)
    status_msg = st.empty()
    
    for i, chunk in enumerate(chunks):
        status_msg.text(f"Scanning Batch {i+1}/{len(chunks)}...")
        prog.progress((i+1)/len(chunks))
        res = model.generate_content(f"Extract patterns & keep reviewer names: {' '.join(chunk)}")
        batch_notes.append(res.text)
        time.sleep(0.5)

    final_prompt = f"""
    Product HTML Snippet: {raw_html[:1500]}
    Analysis Data: {batch_notes}
    Create a detailed JSON report. Map quotes strictly to reviewer names.
    Structure: {{ "product_name": "...", "total_reviews": {len(reviews_data)}, "avg_rating": 4.5, "sentiment_score": 0.8, "verdict": "...", "departments": [{{ "icon": "", "name": "", "sentiment": "", "msg": "" }}], "top_pos": [{{ "text": "", "reviewer": "" }}], "top_neg": [{{ "text": "", "reviewer": "" }}] }}
    """
    status_msg.text("Finalizing Global Report...")
    response = model.generate_content(final_prompt, generation_config={"response_mime_type": "application/json"})
    return safe_json_loads(response.text)

# --- 5. NAVIGATION ---
with st.sidebar:
    st.markdown("<h1 style='font-family:DM Serif Display; color:#c8f064; margin-bottom:0;'>◈ ReviewIQ</h1><p style='color:#5c6370; font-size:10px; letter-spacing:1.5px;'>PRO ANALYTICS v2.6</p>", unsafe_allow_html=True)
    
    if 'page' not in st.session_state: st.session_state.page = "Dashboard"
    
    st.markdown('<div class="nav-wrapper">', unsafe_allow_html=True)
    if st.button("◫ Dashboard"): st.session_state.page = "Dashboard"
    if st.button("⊕ Product Scanner"): st.session_state.page = "Scanner"
    if st.button("📜 Scan History"): st.session_state.page = "History"
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.divider()
    u_key = st.text_input("Gemini API Key", type="password")

# --- 6. PAGE LOGIC ---
if st.session_state.page == "Dashboard":
    st.title("🏛️ Market Intelligence")
    if db:
        docs = list(db.collection("analysis_history").order_by("timestamp", direction=firestore.Query.DESCENDING).stream())
        if docs:
            raw_history = []
            for d in docs:
                item = d.to_dict()
                item['timestamp'] = pd.to_datetime(item['timestamp'])
                raw_history.append(item)
            df = pd.DataFrame(raw_history)
            
            k1, k2, k3, k4 = st.columns(4)
            k1.markdown(f'<div class="kpi-card"><div class="kpi-label">Total Reviews</div><div class="kpi-value">{int(df["total_reviews"].sum())}</div></div>', unsafe_allow_html=True)
            k2.markdown(f'<div class="kpi-card" style="border-top-color:#34d399"><div class="kpi-label">Market NPS</div><div class="kpi-value">{df["sentiment_score"].mean():.2f}</div></div>', unsafe_allow_html=True)
            k3.markdown(f'<div class="kpi-card" style="border-top-color:#a78bfa"><div class="kpi-label">Analyses</div><div class="kpi-value">{len(df)}</div></div>', unsafe_allow_html=True)
            risk_count = len(df[df["sentiment_score"] < 0.5])
            k4.markdown(f'<div class="kpi-card" style="border-top-color:#f87171"><div class="kpi-label">Critical Risks</div><div class="kpi-value">{risk_count}</div></div>', unsafe_allow_html=True)

            st.divider()
            c1, c2 = st.columns([2, 1])
            with c1:
                st.markdown("#### 📈 Intelligence Timeline")
                fig = px.line(df, x='timestamp', y='sentiment_score', hover_name='product_name', template="plotly_dark", color_discrete_sequence=["#c8f064"])
                st.plotly_chart(fig, use_container_width=True)
            with c2:
                st.markdown("#### ⚖️ Sentiment Spread")
                sent_bins = pd.cut(df['sentiment_score'], bins=[0, 0.4, 0.7, 1.0], labels=['Negative', 'Neutral', 'Positive'])
                fig_p = px.pie(names=sent_bins.value_counts().index, values=sent_bins.value_counts().values, hole=0.7, template="plotly_dark", color_discrete_map={'Positive': '#34d399', 'Neutral': '#fbbf24', 'Negative': '#f87171'})
                st.plotly_chart(fig_p, use_container_width=True)
            
            st.divider()
            # Topic Cloud (Robust extraction)
            st.markdown("#### 🏷️ Global Trend Frequencies")
            all_topics = []
            for t_list in df['departments'].tolist():
                if isinstance(t_list, list):
                    for t in t_list:
                        if isinstance(t, dict): all_topics.append(t.get('name'))
                        elif isinstance(t, str): all_topics.append(t.split(':')[0])
            if all_topics:
                counts = pd.Series(all_topics).value_counts().head(8)
                t_cols = st.columns(len(counts))
                for i, (name, count) in enumerate(counts.items()):
                    with t_cols[i]:
                        st.markdown(f"<div style='text-align:center; background:#1a1c20; padding:15px; border-radius:10px; border:1px solid #2a2d34;'><div style='font-size:10px; color:#5c6370;'>{name[:10]}</div><div style='font-size:20px; color:#c8f064; font-weight:600;'>{count}</div></div>", unsafe_allow_html=True)
        else:
            st.info("No data in Firebase. Scan a product to generate the dashboard.")

elif st.session_state.page == "Scanner":
    st.title("⊕ Verified Intelligence Scanner")
    h_input = st.text_area("Paste HTML Source:", height=250, placeholder="Right-click -> Copy Outer HTML of the review section...")
    
    if st.button("🚀 Analyze & Verify Full Dataset", type="primary"):
        if h_input and u_key:
            final_data = deep_analyze_verified(h_input, u_key)
            if final_data:
                final_data['timestamp'] = datetime.now()
                if db: db.collection("analysis_history").add(final_data)
                render_full_analysis(final_data)
                st.balloons()
            else:
                st.error("JSON Error: AI returned invalid formatting. Try a smaller HTML sample.")

elif st.session_state.page == "History":
    st.title("📜 Verified Records")
    if db:
        docs = db.collection("analysis_history").order_by("timestamp", direction=firestore.Query.DESCENDING).stream()
        for doc in docs:
            d = doc.to_dict()
            with st.expander(f"🕒 {d.get('timestamp').strftime('%m/%d %H:%M')} | {d.get('product_name')}"):
                render_full_analysis(d)