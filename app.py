import streamlit as st
import gspread
import pandas as pd
from datetime import datetime, date
import requests
import urllib.parse

# --- 設定 ---
st.set_page_config(page_title="LINE在庫管理システム", layout="wide")
URL = "https://docs.google.com/spreadsheets/d/10Hhcn0qNOvGceSNWLxy3_IOCJTvS1i9xaarZirmUUdw/edit?usp=sharing"

# --- LINEログイン用の関数 ---
def get_line_login_url():
    client_id = st.secrets["line"]["login_channel_id"]
    # 💡 コールバックURL（LINE Developersの設定と完全に一致させること）
    redirect_uri = "https://food-memo-app.streamlit.app"
    
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "state": "random_string",
        "scope": "profile openid"
    }
    # 💡 安全なURL形式に一括変換
    url = f"https://access.line.me/oauth2/v2.1/authorize?{urllib.parse.urlencode(params)}"
    return url

def get_line_user_info(code):
    token_url = "https://api.line.me/oauth2/v2.1/token"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": "https://food-memo-app.streamlit.app",
        "client_id": st.secrets["line"]["login_channel_id"],
        "client_secret": st.secrets["line"]["login_channel_secret"]
    }
    res = requests.post(token_url, headers=headers, data=data).json()
    id_token = res.get("id_token")
    
    # IDトークンを検証してユーザー情報を取得
    payload = {"id_token": id_token, "client_id": st.secrets["line"]["login_channel_id"]}
    user_info = requests.post("https://api.line.me/oauth2/v2.1/verify", data=payload).json()
    return user_info

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
    except Exception as e:
        st.error(f"認証エラー: {e}"); return None

def send_individual_line(to_id, message):
    try:
        url = "https://api.line.me/v2/bot/message/push"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {st.secrets['line']['channel_access_token']}"
        }
        payload = {"to": to_id, "messages": [{"type": "text", "text": message}]}
        res = requests.post(url, headers=headers, json=payload)
        return res.status_code
    except: return None

# --- 🔐 ログイン処理 ---
query_params = st.query_params
if "code" not in query_params:
    st.title("🔐 在庫管理ログイン")
    st.write("ボタンを押してLINEでログインしてください。")
    login_url = get_line_login_url()
    # 💡 デザインされたログインボタン
    st.markdown(f'''
        <a href="{login_url}" target="_self" style="
            background-color: #00B900; 
            color: white; 
            padding: 12px 24px; 
            text-decoration: none; 
            border-radius: 8px; 
            font-weight: bold; 
            display: inline-block;
            margin-top: 20px;">
            LINEでログイン
        </a>
    ''', unsafe_allow_html=True)
    st.stop()
else:
    # ログイン後の処理
    code = query_params["code"]
    try:
        user_info = get_line_user_info(code)
        user_id = user_info.get("sub")
        user_name = user_info.get("name")
    except Exception as e:
        st.error("ログインに失敗しました。URL設定を確認してください。")
        st.stop()

# --- 🍎 メイン画面 ---
st.title(f"🍱 {user_name} さんの在庫リスト")

client = get_gspread_client()
if client:
    sh = client.open_by_url(URL)
    sheet_name = user_name
    
    try:
        worksheet = sh.worksheet(sheet_name)
    except:
        # シートがない場合は新規作成
        worksheet = sh.add_worksheet(title=sheet_name, rows="100", cols="20")
        worksheet.append_row(["品名", "数量", "賞味期限", "保存場所", "種類", "LINE_ID"])
        worksheet.update_cell(2, 6, user_id)
        st.rerun()

    # IDを常に最新にする（通知用）
    worksheet.update_cell(2, 6, user_id)

    # --- サイドバー：在庫追加 ---
    STORAGE_CATS = ["冷蔵", "冷凍", "常温", "その他"]
    TYPE_CATS = ["肉", "野菜", "麺", "飲み物", "その他"]
    
    st.sidebar.title("🛠️ 操作パネル")
    st.sidebar.info(f"ログイン中: {user_name}")
    
    with st.sidebar.form("add_form"):
        st.subheader("➕ 在庫の追加")
        name = st.text_input("品名")
        amount = st.number_input("数量", min_value=1)
        expiry = st.date_input("賞味期限")
        cat1 = st.selectbox("保存場所", STORAGE_CATS)
        cat2 = st.selectbox("種類", TYPE_CATS)
        if st.form_submit_button("追加") and name:
            worksheet.append_row([name, int(amount), expiry.strftime('%Y/%m/%d'), cat1, cat2])
            st.success(f"{name} を追加しました！")
            st.rerun()

    # --- メインエリア：在庫表示と通知 ---
    data = worksheet.get_all_records()
    if data:
        df = pd.DataFrame(data)
        if "LINE_ID" in df.columns: df = df.drop(columns=["LINE_ID"])

        # 🔔 通知ボタン
        if st.button("期限が近い在庫をLINEに通知する", type="primary"):
            today = date.today()
            alerts = []
            for _, r in df.iterrows():
                try:
                    d = datetime.strptime(str(r["賞味期限"]), '%Y/%m/%d').date()
                    if (d - today).days <= 3:
                        alerts.append(f"・{r['品名']} ({r['賞味期限']})")
                except: continue
            
            if alerts:
                msg = f"\n【{user_name}さんの期限間近リスト】\n" + "\n".join(alerts) + "\n早めに使いましょう！"
                if send_individual_line(user_id, msg) == 200:
                    st.success("LINEに通知を送信しました！")
                else:
                    st.error("通知の送信に失敗しました。Messaging APIの設定を確認してください。")
            else:
                st.info("3日以内に期限が切れるものはありません。")

        st.subheader("📦 在庫一覧")
        st.data_editor(df, use_container_width=True, hide_index=True)
    else:
        st.info("データがありません。サイドバーから追加してください。")

