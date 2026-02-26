import streamlit as st
import gspread
import pandas as pd
from datetime import datetime, date
import requests
import urllib.parse

# --- 設定 ---
st.set_page_config(page_title="LINE在庫管理システム", layout="wide")
# ⚠️ スプレッドシートのURLが正しいか今一度ご確認ください
URL = "https://docs.google.com/spreadsheets/d/10Hhcn0qNOvGceSNWLxy3_IOCJTvS1i9xaarZirmUUdw/edit?usp=sharing"

# --- LINEログイン用の関数 ---
def get_line_login_url():
    client_id = st.secrets["line"]["login_channel_id"]
    redirect_uri = "https://food-memo-app.streamlit.app"
    
    # 💡 2重エンコードを防ぐためシンプルな結合
    url = (
        f"https://access.line.me/oauth2/v2.1/authorize?"
        f"response_type=code&"
        f"client_id={client_id}&"
        f"redirect_uri={redirect_uri}&"
        f"state=random_string&"
        f"scope=profile%20openid"
    )
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
        st.error(f"認証エラー: {e}")
        return None

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
    except:
        return None

# --- 🔐 ログイン処理 ---
query_params = st.query_params
if "code" not in query_params:
    st.title("🔐 在庫管理ログイン")
    st.write("ボタンを押してLINEでログインしてください。")
    login_url = get_line_login_url()
    st.link_button("LINEでログイン", login_url, type="primary")
    st.stop()
else:
    code = query_params["code"]
    try:
        user_info = get_line_user_info(code)
        user_id = user_info.get("sub")
        # 💡 displayName または name から取得
        user_name = user_info.get("displayName") or user_info.get("name") or "User"
    except Exception as e:
        st.error(f"ログイン失敗: {e}")
        st.stop()

# --- 🍎 メイン画面 ---
st.title(f"🍱 在庫リスト")

client = get_gspread_client()
if client:
    try:
        sh = client.open_by_url(URL)
        sheet_name = user_name
        
        # --- シートの取得・作成ロジック ---
        try:
            worksheet = sh.worksheet(sheet_name)
        except:
            # シートがない場合は新規作成（エラー回避のため最大限のtry-except）
            try:
                worksheet = sh.add_worksheet(title=sheet_name, rows="1000", cols="10")
                # ヘッダー作成に失敗しても止まらないようにする
                try:
                    worksheet.append_row(["品名", "数量", "賞味期限", "保存場所", "種類", "LINE_ID"])
                except:
                    pass
                st.rerun()
            except Exception as e:
                st.error("シートの自動作成に失敗しました。スプレッドシート側で『編集者』権限があるか確認してください。")
                st.info(f"手動解決策：スプレッドシートに「{sheet_name}」という名前のシートを作成してください。")
                st.stop()

        # IDの更新（失敗しても動作には影響しないので無視）
        try:
            worksheet.update_acell('F2', user_id)
        except:
            pass

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
                try:
                    worksheet.append_row([name, int(amount), expiry.strftime('%Y/%m/%d'), cat1, cat2])
                    st.success(f"{name} を追加しました！")
                    st.rerun()
                except Exception as e:
                    st.error(f"追加に失敗しました。権限を確認してください: {e}")

        # --- メインエリア：在庫表示 ---
        data = worksheet.get_all_records()
        if data:
            df = pd.DataFrame(data)
            if "LINE_ID" in df.columns: df = df.drop(columns=["LINE_ID"])

            # 🔔 通知ボタン
            if st.button("期限が近い在庫をLINEに通知する"):
                today = date.today()
                alerts = []
                for _, r in df.iterrows():
                    try:
                        d = datetime.strptime(str(r["賞味期限"]), '%Y/%m/%d').date()
                        if (d - today).days <= 3:
                            alerts.append(f"・{r['品名']} ({r['賞味期限']})")
                    except: continue
                
                if alerts:
                    msg = f"\n【期限間近リスト】\n" + "\n".join(alerts) + "\n早めに使いましょう！"
                    if send_individual_line(user_id, msg) == 200:
                        st.success("LINEに通知を送信しました！")
                    else:
                        st.error("通知に失敗しました。")
                else:
                    st.info("3日以内に期限が切れるものはありません。")

            st.subheader("📦 在庫一覧")
            st.data_editor(df, use_container_width=True, hide_index=True)
        else:
            st.info("まだ在庫データがありません。サイドバーから追加してください。")

    except Exception as e:
        st.error(f"スプレッドシートが開けません: {e}")

