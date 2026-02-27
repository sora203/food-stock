import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import requests
from supabase import create_client, Client

# --- 🎨 デザインと基本設定 ---
st.set_page_config(page_title="在庫管理メモ", layout="wide")

st.markdown("""
    <style>
    /* 背景とコンテナ */
    .stApp { background-image: url("https://www.toptal.com/designers/subtlepatterns/uploads/wood_pattern.png"); background-repeat: repeat; background-attachment: fixed; }
    [data-testid="stAppViewBlockContainer"] { background-color: rgba(245, 222, 179, 0.7); padding: 3rem; border-radius: 15px; margin-top: 2rem; }
    
    /* メインタイトル */
    .main-title { font-size: 3.5rem; font-weight: 900; color: #3e2723; line-height: 1.1; margin-bottom: 20px; }
    
    /* 種類で絞り込み（マルチセレクトのラベル）の色をタブと同じ茶色に */
    [data-testid="stAppViewBlockContainer"] .stMultiSelect label {
        color: #3e2723 !important;
        font-weight: 800 !important;
        font-size: 1.2rem !important;
    }

    /* タブをボタン風にカスタマイズ */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
        background-color: rgba(62, 39, 35, 0.1);
        padding: 8px;
        border-radius: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 45px;
        background-color: #ffffff;
        border-radius: 8px;
        padding: 0 20px;
        color: #3e2723 !important;
        font-weight: bold !important;
        border: 1px solid #3e2723;
        transition: all 0.3s;
    }
    .stTabs [aria-selected="true"] {
        background-color: #3e2723 !important;
        color: #ffffff !important;
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }

    /* 表の文字色 */
    [data-testid="stDataFrame"] td { color: #212121 !important; font-weight: 500; }
    
    /* 通知カード */
    .alert-card {
        padding: 15px;
        border-radius: 12px;
        margin-bottom: 12px;
        font-weight: bold;
        display: flex;
        align-items: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .alert-danger { background-color: #ff5252; color: white; border-left: 8px solid #b71c1c; }
    .alert-warning { background-color: #ffca28; color: #3e2723; border-left: 8px solid #f57f17; }
    .alert-icon { font-size: 1.5rem; margin-right: 15px; }
    
    /* 🌟 不要なマークやリンクを消し、矢印だけ残す */
    #MainMenu {visibility: hidden;}                /* 右上のメニュー */
    footer {visibility: hidden;}                   /* 下部のクレジット */
    .stDeployButton {display:none;}                /* 右下の王冠マーク */
    
    /* ヘッダー全体を非表示にするが、矢印ボタン(st-emotion-cache-...)は残す */
    header[data-testid="stHeader"] {background: none;}
    header[data-testid="stHeader"] > div {display: none;}
    
    </style>
""", unsafe_allow_html=True)

today_val = date.today()
LOCATIONS = ["冷蔵", "冷凍", "常温"]
CATEGORIES = ["肉", "野菜", "海鮮", "麺", "飲料", "調味料", "その他"]

# --- 💡 Supabase接続 ---
@st.cache_resource
def init_supabase() -> Client:
    return create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])

supabase = init_supabase()

# --- LINE連携 ---
def get_line_login_url():
    client_id = st.secrets["line"]["login_channel_id"]
    redirect_uri = "https://food-memo-app.streamlit.app"
    return (f"https://access.line.me/oauth2/v2.1/authorize?response_type=code&client_id={client_id}"
            f"&redirect_uri={redirect_uri}&state=random&scope=profile%20openid")

def get_line_user_info(code):
    res = requests.post("https://api.line.me/oauth2/v2.1/token", data={
        "grant_type": "authorization_code", "code": code, "redirect_uri": "https://food-memo-app.streamlit.app",
        "client_id": st.secrets["line"]["login_channel_id"], "client_secret": st.secrets["line"]["login_channel_secret"]
    }).json()
    return requests.post("https://api.line.me/oauth2/v2.1/verify", data={
        "id_token": res.get("id_token"), "client_id": st.secrets["line"]["login_channel_id"]
    }).json()

# --- 🔐 ログイン管理 ---
if "user_id" not in st.session_state:
    qp = st.query_params
    if "code" not in qp:
        st.markdown("<h1 style='text-align: center;'>Stock Manager</h1>", unsafe_allow_html=True)
        st.link_button("LINEでログイン", get_line_login_url())
        st.stop()
    else:
        try:
            u_info = get_line_user_info(qp["code"])
            st.session_state.user_id = str(u_info.get("sub"))
            st.session_state.user_name = u_info.get("displayName") or "利用者"
            st.query_params.clear()
        except:
            st.error("ログインに失敗しました。再読み込みしてください。")
            st.stop()

uid, uname = st.session_state.user_id, st.session_state.user_name
st.markdown(f"<div style='color: #3e2723; font-weight: bold;'>{uname} 様</div><div class='main-title'>在庫リスト</div>", unsafe_allow_html=True)

# --- 🍎 データ操作 ---
def load_data():
    res = supabase.table("stocks").select("*").eq("line_id", uid).order("expiry_date").execute()
    return pd.DataFrame(res.data)

df = load_data()

# --- ⏰ 期限アラート機能 ---
if not df.empty:
    one_day_later = today_val + timedelta(days=1)
    three_days_later = today_val + timedelta(days=3)
    df['expiry_dt'] = pd.to_datetime(df['expiry_date']).dt.date
    
    red_group = df[df['expiry_dt'] <= one_day_later]
    yellow_group = df[df['expiry_dt'] == three_days_later]

    if not (red_group.empty and yellow_group.empty):
        st.markdown(f"<h3 style='color: #3e2723;'>🔔 期限のお知らせ</h3>", unsafe_allow_html=True)
        for _, row in red_group.iterrows():
            status = "【期限切れ】" if row['expiry_dt'] < today_val else "【本日まで】" if row['expiry_dt'] == today_val else "【あと1日】"
            icon = "🚫" if row['expiry_dt'] < today_val else "⏰"
            st.markdown(f"""<div class='alert-card alert-danger'><span class='alert-icon'>{icon}</span>{status} {row['name']} ({row['expiry_date']})</div>""", unsafe_allow_html=True)
        for _, row in yellow_group.iterrows():
            st.markdown(f"""<div class='alert-card alert-warning'><span class='alert-icon'>📅</span>【あと3日】 {row['name']} ({row['expiry_date']})</div>""", unsafe_allow_html=True)
        st.markdown("---")

# --- サイドバー（追加フォーム） ---
with st.sidebar:
    st.markdown("### 在庫を追加")
    with st.form("add_new_stock_form", clear_on_submit=True):
        n = st.text_input("品名")
        a = st.number_input("数量", min_value=1, value=1)
        e_date = st.date_input("賞味期限", value=today_val)
        e = e_date.strftime('%Y-%m-%d')
        c1 = st.selectbox("保存場所", LOCATIONS)
        c2 = st.selectbox("種類", CATEGORIES)
        
        if st.form_submit_button("追加する") and n:
            existing = supabase.table("stocks").select("*").match({
                "name": n, "expiry_date": e, "location": c1, "category": c2, "line_id": uid
            }).execute()
            
            if existing.data and len(existing.data) > 0:
                new_qty = existing.data[0]["quantity"] + a
                supabase.table("stocks").update({"quantity": new_qty}).eq("id", existing.data[0]["id"]).execute()
            else:
                supabase.table("stocks").insert({
                    "name": n, "quantity": a, "expiry_date": e, "location": c1, "category": c2, "line_id": uid
                }).execute()
            st.rerun()

# --- メイン表示 ---
if not df.empty:
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["🏠 すべて", "❄️ 冷蔵", "🧊 冷凍", "📦 常温", "🗑️ 整理"])

    def display_filtered_df(target_df, key_suffix=""):
        selected_cats = st.multiselect("種類で絞り込み", CATEGORIES, key=f"filter_{key_suffix}")
        if selected_cats:
            target_df = target_df[target_df['category'].isin(selected_cats)]
        
        if target_df.empty:
            st.info("該当する在庫はありません。")
        else:
            st.dataframe(target_df[["name", "quantity", "expiry_date", "location", "category"]], use_container_width=True, hide_index=True)

    with tab1:
        display_filtered_df(df, key_suffix="all")
    with tab2:
        display_filtered_df(df[df['location'] == '冷蔵'], key_suffix="fridge")
    with tab3:
        display_filtered_df(df[df['location'] == '冷凍'], key_suffix="freezer")
    with tab4:
        display_filtered_df(df[df['location'] == '常温'], key_suffix="pantry")
    with tab5:
        st.markdown(f"<h3 style='color: #3e2723;'>🗑️ 在庫の一括削除</h3>", unsafe_allow_html=True)
        delete_items = st.multiselect("削除したい項目を選んでください", options=df["id"].tolist(), format_func=lambda x: f"{df[df['id']==x]['name'].values[0]} ({df[df['id']==x]['expiry_date'].values[0]})")
        if st.button("選択した項目を削除する", type="primary"):
            if delete_items:
                for d_id in delete_items:
                    supabase.table("stocks").delete().eq("id", d_id).execute()
                st.success("削除しました！")
                st.rerun()
else:
    st.info("在庫がありません。サイドバーから追加してください！")
