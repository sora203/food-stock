import streamlit as st
import gspread
import pandas as pd
from datetime import datetime, date
import requests
from streamlit_line_login import LineLogin

# --- 設定 ---
st.set_page_config(page_title="LINEログイン在庫管理", layout="wide")
URL = "https://docs.google.com/spreadsheets/d/10Hhcn0qNOvGceSNWLxy3_IOCJTvS1i9xaarZirmUUdw/edit?usp=sharing"

# --- LINEログイン初期化 ---
line_login = LineLogin(
    client_id=st.secrets["line"]["login_channel_id"],
    client_secret=st.secrets["line"]["login_channel_secret"],
    redirect_uri=f"https://{st.secrets.get('app_url', 'YOUR_APP_NAME.streamlit.app')}", # 後述の注意参照
)

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

# --- 💬 LINE通知関数 ---
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
# パスワード入力の代わりにLINEログインを実行
line_user = line_login.login()

if not line_user:
    st.title("🔐 在庫管理ログイン")
    st.info("下のボタンからLINEでログインしてください。")
    st.stop()

# ログイン成功時、ユーザー情報を取得
user_id = line_user['sub']         # これが U... から始まる内部ID
user_name = line_user['name']      # LINEの表示名（Aさん、Bさん）

# --- メイン画面 ---
st.title(f"🍎 {user_name} さんの在庫リスト")

client = get_gspread_client()
if client:
    sh = client.open_by_url(URL)
    # LINEの表示名をシート名にする（シートがなければ自動作成）
    sheet_name = user_name
    
    try:
        worksheet = sh.worksheet(sheet_name)
    except:
        worksheet = sh.add_worksheet(title=sheet_name, rows="100", cols="20")
        worksheet.append_row(["品名", "数量", "賞味期限", "保存場所", "種類", "LINE_ID"])
        # 初回作成時にIDを2行目6列目に書き込む
        worksheet.update_cell(2, 6, user_id)
        st.rerun()

    # IDを取得（念のため常に最新を保持）
    worksheet.update_cell(2, 6, user_id)

    # --- 在庫操作パネル ---
    STORAGE_CATS = ["冷蔵", "冷凍", "常温", "その他"]
    TYPE_CATS = ["肉", "野菜", "麺", "飲み物", "その他"]
    
    st.sidebar.title("🛠️ 操作パネル")
    st.sidebar.write(f"ログイン中: {user_name}")
    
    with st.sidebar.form("add_form"):
        st.subheader("➕ 在庫の追加")
        name = st.text_input("品名")
        amount = st.number_input("数量", min_value=1)
        expiry = st.date_input("賞味期限")
        cat1 = st.selectbox("保存場所", STORAGE_CATS)
        cat2 = st.selectbox("種類", TYPE_CATS)
        if st.form_submit_button("追加") and name:
            worksheet.append_row([name, int(amount), expiry.strftime('%Y/%m/%d'), cat1, cat2])
            st.rerun()

    # --- 在庫データ表示 ---
    data = worksheet.get_all_records()
    if data:
        df = pd.DataFrame(data)
        if "LINE_ID" in df.columns: df = df.drop(columns=["LINE_ID"])

        # 🔔 通知ボタン（ID入力を介さず、ログイン情報から直接送信！）
        if st.button("期限が近い在庫を自分のLINEに送る"):
            today = date.today()
            alerts = []
            for _, r in df.iterrows():
                try:
                    d = datetime.strptime(str(r["賞味期限"]), '%Y/%m/%d').date()
                    if (d - today).days <= 3:
                        alerts.append(f"・{r['品名']} ({r['賞味期限']})")
                except: continue
            
            if alerts:
                msg = f"\n【{user_name}さんの期限間近リスト】\n" + "\n".join(alerts)
                if send_individual_line(user_id, msg) == 200:
                    st.success("LINEに通知を飛ばしました！")
            else:
                st.info("3日以内に期限が切れるものはありません。")

        st.subheader("📦 在庫一覧")
        st.data_editor(df, use_container_width=True, hide_index=True)
    else:
        st.info("データがありません。サイドバーから追加してください。")
