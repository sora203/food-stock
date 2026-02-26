import streamlit as st
import gspread
import pandas as pd
from datetime import datetime, date
import requests

# --- 設定 ---
st.set_page_config(page_title="個別在庫管理", layout="wide")
URL = "https://docs.google.com/spreadsheets/d/10Hhcn0qNOvGceSNWLxy3_IOCJTvS1i9xaarZirmUUdw/edit?usp=sharing"

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

# --- 💬 LINE個別通知関数 ---
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

# --- 🔑 ログイン処理 ---
if "authenticated" not in st.session_state: st.session_state.authenticated = False
if not st.session_state.authenticated:
    st.title("🔐 在庫管理ログイン")
    password = st.text_input("アクセスパスワード", type="password")
    if st.button("ログイン"):
        if password == "admin1234": # 救済用
            st.session_state.show_rescue = True
        elif password:
            st.session_state.authenticated = True
            st.session_state.current_pw = password
            st.rerun()
    
    if st.session_state.get("show_rescue"):
        st.warning("⚠️ 登録済みパスワード一覧")
        client = get_gspread_client()
        if client:
            sh = client.open_by_url(URL)
            st.code([s.title for s in sh.worksheets() if s.title != "admin_log"])
    st.stop()

# --- メイン画面 ---
st.title(f"🍎 {st.session_state.current_pw} さんの在庫リスト")

client = get_gspread_client()
if client:
    sh = client.open_by_url(URL)
    sheet_name = st.session_state.current_pw
    
    try:
        worksheet = sh.worksheet(sheet_name)
    except:
        worksheet = sh.add_worksheet(title=sheet_name, rows="100", cols="20")
        worksheet.append_row(["品名", "数量", "賞味期限", "保存場所", "種類", "LINE_ID"])
        st.rerun()

    # --- 🆔 LINE ID設定セクション（案1：QRガイド付き） ---
    rows = worksheet.get_all_values()
    user_line_id = rows[1][5] if len(rows) > 1 and len(rows[1]) >= 6 else ""

    with st.expander("👤 初めて使う方：LINE通知の設定はこちら"):
        st.write("個別の通知を受け取るには、以下の2ステップが必要です。")
        col_qr, col_inst = st.columns([1, 2])
        
        with col_qr:
            # 💡 ここにあなたのLINE BOTのQRコード画像URLを貼ってください
            # LINE DevelopersのMessaging API設定タブにあるQRコードのURLをコピーして貼り付けます
            st.image("https://qr-official.line.me/gs/M_xxxxxxxx.png", caption="1. 友達追加") 
        
        with col_inst:
            st.write("2. あなたの『LINEユーザーID』を入力してください。")
            st.info("※LINE IDとは異なります。管理画面等で確認できる『U...』から始まる英数字です。")
            new_id = st.text_input("LINEユーザーIDを貼り付け", value=user_line_id)
            if st.button("通知設定を保存"):
                worksheet.update_cell(2, 6, new_id)
                st.success("保存完了！これで自分に通知が届くようになります。")
                st.rerun()

    # --- 在庫操作パネル（サイドバー） ---
    STORAGE_CATS = ["冷蔵", "冷凍", "常温", "その他"]
    TYPE_CATS = ["肉", "野菜", "麺", "飲み物", "その他"]
    
    st.sidebar.title("🛠️ 操作パネル")
    filter_storage = st.sidebar.multiselect("保存場所で絞り込む", STORAGE_CATS)
    
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

        # 🔔 通知ボタン
        if st.button("期限が近い在庫を自分のLINEに送る", type="secondary"):
            if not user_line_id:
                st.error("先に『通知設定』からIDを登録してください。")
            else:
                today = date.today()
                alerts = []
                for _, r in df.iterrows():
                    try:
                        d = datetime.strptime(str(r["賞味期限"]), '%Y/%m/%d').date()
                        if (d - today).days <= 3:
                            alerts.append(f"・{r['品名']} ({r['賞味期限']})")
                    except: continue
                
                if alerts:
                    msg = f"\n【{sheet_name}さんの期限間近リスト】\n" + "\n".join(alerts) + "\n早めに使いましょう！"
                    if send_individual_line(user_line_id, msg) == 200:
                        st.success("LINEに通知を飛ばしました！")
                else:
                    st.info("3日以内に期限が切れるものはありません。")

        # 在庫一覧（編集・削除機能付き）
        st.subheader("📦 在庫一覧")
        st.data_editor(df, use_container_width=True, hide_index=True)

    else:
        st.info("データがありません。サイドバーから追加してください。")
