import streamlit as st
import gspread
import pandas as pd
from datetime import datetime, date
import requests
import urllib.parse

# --- 🎨 カスタムCSS（サイドバー・ダークモード仕様） ---
def local_css():
    st.markdown("""
        <style>
        /* アプリ全体の背景（木目調） */
        .stApp {
            background-image: url("https://www.toptal.com/designers/subtlepatterns/uploads/wood_pattern.png");
            background-repeat: repeat;
            background-attachment: fixed;
        }

        /* メインコンテンツ（白透過） */
        [data-testid="stAppViewBlockContainer"] {
            background-color: rgba(255, 255, 255, 0.92);
            padding: 3rem;
            border-radius: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
            margin-top: 2rem;
        }

        /* 🌙 サイドバーだけダークモード */
        [data-testid="stSidebar"] {
            background-color: #262730 !important; /* ダークグレー */
            color: #ffffff !important;
        }
        
        /* サイドバー内のテキストを白くする */
        [data-testid="stSidebar"] .stMarkdown, 
        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] p {
            color: #ffffff !important;
        }
        
        /* サイドバー内の入力欄のデザイン調整 */
        [data-testid="stSidebar"] input, 
        [data-testid="stSidebar"] select {
            background-color: #3e404b !important;
            color: white !important;
            border: 1px solid #555 !important;
        }

        /* ログインボタン（大きく・中央・緑） */
        .stLinkButton { display: flex; justify-content: center; padding: 20px 0; }
        div.stLinkButton > a {
            background-color: #06C755 !important;
            color: white !important;
            border-radius: 50px !important;
            padding: 1.2rem 5rem !important;
            font-size: 1.4rem !important;
            font-weight: bold !important;
            text-decoration: none !important;
        }

        /* タイトルデザイン */
        .user-title { font-size: 1.3rem; color: #666; margin-bottom: -5px; }
        .main-title { font-size: 3.5rem; font-weight: 800; color: #333; line-height: 1; margin-bottom: 20px; }
        
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        </style>
    """, unsafe_allow_html=True)

# --- 設定 ---
st.set_page_config(page_title="在庫管理メモ", page_icon="📝", layout="wide")
local_css()
URL = "https://docs.google.com/spreadsheets/d/10Hhcn0qNOvGceSNWLxy3_IOCJTvS1i9xaarZirmUUdw/edit?usp=sharing"

# --- LINEログイン用の関数 ---
def get_line_login_url():
    client_id = st.secrets["line"]["login_channel_id"]
    redirect_uri = "https://food-memo-app.streamlit.app"
    url = (f"https://access.line.me/oauth2/v2.1/authorize?response_type=code&client_id={client_id}"
           f"&redirect_uri={redirect_uri}&state=random_string&scope=profile%20openid")
    return url

def get_line_user_info(code):
    token_url = "https://api.line.me/oauth2/v2.1/token"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "grant_type": "authorization_code", "code": code,
        "redirect_uri": "https://food-memo-app.streamlit.app",
        "client_id": st.secrets["line"]["login_channel_id"],
        "client_secret": st.secrets["line"]["login_channel_secret"]
    }
    res = requests.post(token_url, headers=headers, data=data).json()
    id_token = res.get("id_token")
    payload = {"id_token": id_token, "client_id": st.secrets["line"]["login_channel_id"]}
    return requests.post("https://api.line.me/oauth2/v2.1/verify", data=payload).json()

def get_gspread_client():
    try:
        raw_key = st.secrets["connections"]["gsheets"]["private_key"]
        fixed_key = raw_key.replace("\\n", "\n").strip()
        creds = {
            "type": "service_account", "project_id": "my-food-stock-app",
            "private_key": fixed_key, "client_email": st.secrets["connections"]["gsheets"]["client_email"],
            "token_uri": "https://www.googleapis.com/oauth2/v4/token",
        }
        return gspread.service_account_from_dict(creds)
    except: return None

def send_individual_line(to_id, message):
    try:
        url = "https://api.line.me/v2/bot/message/push"
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {st.secrets['line']['channel_access_token']}"}
        payload = {"to": to_id, "messages": [{"type": "text", "text": message}]}
        return requests.post(url, headers=headers, json=payload).status_code
    except: return None

# --- 🔐 ログイン画面 ---
query_params = st.query_params
if "code" not in query_params:
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    st.markdown("<h1 style='text-align: center; color: #333; font-size: 3rem;'>Stock Manager</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #666; font-size: 1.2rem;'>毎日の食材管理を、もっと楽しく。</p>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    st.link_button("LINEでログイン", get_line_login_url())
    st.stop()
else:
    try:
        user_info = get_line_user_info(query_params["code"])
        user_id = user_info.get("sub")
        user_name = user_info.get("displayName") or user_info.get("name") or "User"
    except:
        st.error("ログイン失敗。再試行してください。")
        st.stop()

# --- 🍎 メイン画面 ---
# タイトルの改行デザイン
st.markdown(f"<div class='user-title'>{user_name} 様</div>", unsafe_allow_html=True)
st.markdown("<div class='main-title'>在庫リスト</div>", unsafe_allow_html=True)
st.markdown("<br>", unsafe_allow_html=True)

client = get_gspread_client()
if client:
    sh = client.open_by_url(URL)
    try:
        worksheet = sh.worksheet(user_name)
    except:
        worksheet = sh.add_worksheet(title=user_name, rows="1000", cols="10")
        worksheet.append_row(["品名", "数量", "賞味期限", "保存場所", "種類", "LINE_ID"])
        st.rerun()

    # --- サイドバー：追加 ---
    with st.sidebar:
        st.markdown(f"### 在庫を追加")
        with st.form("add_form", clear_on_submit=True):
            name = st.text_input("品名", placeholder="例: たまご")
            amount = st.number_input("数量", min_value=1, value=1)
            expiry = st.date_input("賞味期限", value=date.today())
            cat1 = st.selectbox("保存場所", ["冷蔵", "冷凍", "常温", "その他"])
            cat2 = st.selectbox("種類", ["肉", "野菜", "麺", "飲み物", "その他"])
            if st.form_submit_button("リストに追加"):
                if name:
                    worksheet.append_row([name, int(amount), expiry.strftime('%Y/%m/%d'), cat1, cat2])
                    st.toast(f"{name}を追加しました")
                    st.rerun()

    # --- メインエリア ---
    data = worksheet.get_all_records()
    if data:
        df = pd.DataFrame(data)
        df.insert(0, "選択", False)
        
        search_query = st.text_input("検索", placeholder="品名や場所を入力...")
        
        df_filtered = df.copy()
        if search_query:
            mask = df_filtered.drop(columns=["選択"]).apply(lambda r: r.astype(str).str.contains(search_query, case=False).any(), axis=1)
            df_filtered = df_filtered[mask]

        col_btn1, col_btn2 = st.columns([1, 1])
        with col_btn1:
            if st.button("期限間近を通知"):
                today = date.today()
                alerts = [f"・{r['品名']} ({r['賞味期限']})" for _, r in df.iterrows() if (datetime.strptime(str(r["賞味期限"]), '%Y/%m/%d').date() - today).days <= 3]
                if alerts:
                    msg = f"\n【期限間近リスト】\n" + "\n".join(alerts) + "\n早めに使いましょう！"
                    send_individual_line(user_id, msg); st.success("通知しました")
                else: st.info("期限が近いものはありません")
        
        with col_btn2:
            delete_btn = st.button("選択項目を削除", type="primary")

        edited_df = st.data_editor(
            df_filtered.drop(columns=["LINE_ID"], errors='ignore'),
            use_container_width=True,
            hide_index=True,
            column_config={"選択": st.column_config.CheckboxColumn()}
        )

        if delete_btn:
            delete_names = edited_df[edited_df["選択"] == True]["品名"].tolist()
            if delete_names:
                new_data = [list(data[0].keys())]
                keep_rows = [r for r in data if r["品名"] not in delete_names]
                for r in keep_rows: new_data.append(list(r.values()))
                worksheet.clear(); worksheet.update('A1', new_data)
                st.rerun()
    else:
        st.info("データがありません")


