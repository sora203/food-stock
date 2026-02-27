import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import requests
from supabase import create_client, Client

# --- 🎨 デザインと基本設定 ---
st.set_page_config(page_title="在庫管理メモ", layout="wide")

st.markdown("""
    <style>
    .stApp { background-image: url("https://www.toptal.com/designers/subtlepatterns/uploads/wood_pattern.png"); background-repeat: repeat; background-attachment: fixed; }
    [data-testid="stAppViewBlockContainer"] { background-color: rgba(245, 222, 179, 0.7); padding: 3rem; border-radius: 15px; margin-top: 2rem; }
    .main-title { font-size: 3.5rem; font-weight: 900; color: #3e2723; line-height: 1.1; margin-bottom: 20px; }
    .alert-box { padding: 10px; border-radius: 10px; margin-bottom: 10px; font-weight: bold; }
    .alert-today { background-color: #ff5252; color: white; border: 2px solid #b71c1c; }
    .alert-soon { background-color: #ffca28; color: #3e2723; border: 2px solid #f57f17; }
    #MainMenu, footer {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# 今日の日付を最初に定義しておく（エラー防止）
today_val = date.today()

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
st.markdown(f"<div>{uname} 様</div><div class='main-title'>在庫リスト</div>", unsafe_allow_html=True)

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
    
    today_items = df[df['expiry_dt'] == today_val]
    one_day_items = df[df['expiry_dt'] == one_day_later]
    three_day_items = df[df['expiry_dt'] == three_days_later]
    expired_items = df[df['expiry_dt'] < today_val]

    if not (today_items.empty and one_day_items.empty and three_day_items.empty and expired_items.empty):
        st.markdown("### ⚠️ 期限アラート")
        if not expired_items.empty:
            for _, row in expired_items.iterrows():
                st.markdown(f"<div class='alert-box alert-today'>【期限切れ！】 {row['name']} ({row['expiry_date']})</div>", unsafe_allow_html=True)
        if not today_items.empty:
            for _, row in today_items.iterrows():
                st.markdown(f"<div class='alert-box alert-today'>【本日まで！】 {row['name']}</div>", unsafe_allow_html=True)
        if not one_day_items.empty:
            for _, row in one_day_items.iterrows():
                st.markdown(f"<div class='alert-box alert-soon'>【あと1日】 {row['name']}</div>", unsafe_allow_html=True)
        if not three_day_items.empty:
            for _, row in three_day_items.iterrows():
                st.markdown(f"<div class='alert-box alert-soon'>【あと3日】 {row['name']}</div>", unsafe_allow_html=True)
        st.markdown("---")

# --- サイドバー ---
with st.sidebar:
    st.markdown("### 在庫を追加")
    # フォームを開始
    with st.form("add_new_stock_form", clear_on_submit=True):
        n = st.text_input("品名")
        a = st.number_input("数量", min_value=1, value=1)
        # format引数を削除して安定性を優先
        e_date = st.date_input("賞味期限", value=today_val)
        e = e_date.strftime('%Y-%m-%d')
        c1 = st.selectbox("保存場所", ["冷蔵", "冷凍", "常温", "その他"])
        c2 = st.selectbox("種類", ["肉", "野菜", "麺", "飲み物", "その他"])
        
        # フォームの送信ボタン（これがないとエラーになります）
        submit_clicked = st.form_submit_button("追加する")
        
        if submit_clicked and n:
            existing = supabase.table("stocks").select("*").match({
                "name": n, "expiry_date": e, "location": c1, "category": c2, "line_id": uid
            }).execute()
            
            if existing.data:
                new_qty = existing.data[0]["quantity"] + a
                supabase.table("stocks").update({"quantity": new_qty}).eq("id", existing.data[0]["id"]).execute()
            else:
                supabase.table("stocks").insert({
                    "name": n, "quantity": a, "expiry_date": e, "location": c1, "category": c2, "line_id": uid
                }).execute()
            st.rerun()

# --- メイン表示 ---
if not df.empty:
    st.dataframe(
        df[["name", "quantity", "expiry_date", "location", "category"]], 
        use_container_width=True, 
        hide_index=True
    )

    st.markdown("---")
    st.markdown("### 🗑️ 在庫の整理")
    
    delete_items = st.multiselect(
        "削除したい項目を選んでください",
        options=df["id"].tolist(),
        format_func=lambda x: f"{df[df['id']==x]['name'].values[0]} ({df[df['id']==x]['expiry_date'].values[0]})"
    )

    if st.button("選択した項目を削除する", type="primary"):
        if delete_items:
            for d_id in delete_items:
                supabase.table("stocks").delete().eq("id", d_id).execute()
            st.success("削除しました！")
            st.rerun()
else:
    st.info("在庫がありません。サイドバーから追加してください！")
