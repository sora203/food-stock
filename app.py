import streamlit as st
from streamlit_gsheets import GSheetsConnection
import gspread
import pandas as pd

st.set_page_config(page_title="在庫管理アプリ", layout="wide")
st.title("🍎 食品在庫管理システム")

URL = "https://docs.google.com/spreadsheets/d/10Hhcn0qNOvGceSNWLxy3_IOCJTvS1i9xaarZirmUUdw/edit?usp=sharing"

# 🔑 認証情報（ここをそっくり入れ替え）
creds_dict = {
    "type": "service_account",
    "project_id": "my-food-stock-app",
    "private_key_id": "75d12b638a7f1bcbb74bdbe4a62bfabd586e1741",
    "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQC7pEdlh6ySjEmN\nZcs6SbvMpEI43WAJX7DCss3NYoTnDNW5uDth919R64pBW8tNbzXB4KzPmfLoZWDT\nI4Il1+1SXCk8LldQwkGJ7wPMgPSSg4hKKFA+EA8m5Hldy0pk2ESSKSlYFGX3+pqN\nNgKqLRAZDykX6u+aDwO0GTqL+Kl2aOgZwtLT5efZ9aBlVs1UP5Y1W8Mw3yAP8VZF\n+vdqjRdfvJ0BoikPhBrtqxpc2ntP70OzzEwwKMPT8a8fwN89j361rwegEbXj14E8\n/lRDCeFmOMC4voRli5eBdzedCDYwdVfFeqvbm9hXA9rlETDKup3F1ZmxaJDBEGlo\nlWOAWJFpAgMBAAECggEALuDS6X2k0pPzyDyXMj+7iFu9I6HC3XSnn2y2V8p2M5cU\nSirJwybfDINQ7hU1zGmtP3uXEOKAOikhsH4dhMDWTI4zyxI0xDtTzlcFVvEcqQHt\nacF6kpbGgkvwOkuQkXMqZm2cI6Is+3ADbqYAsm1BqVENTilmpNF9dmAbLV75T1hm\njUmqisaoSMlOLmYJ9IRN+g+L5T29J9PfDmdBCZjgFOVzdg2Uiwqf0DL6x6iwYik7\nZpdFJ4FNki31asQsSkchJBce2XAACLM0F8quwGuFWOT79HBGoZk2i/g9Zuy1xk+x\n2ubkvXD/WgEypQ5D0/LJUQBfsFb518Ok7dTMxGVrFQKBgQDlHpnOhCHWrpAUzpdY\nK7arsPbwOKrs64tfc0qBsI6pDEXhNbCxUdHLB8ffsUA2Y7sBB4M9n/4Yq7A9UPsn\noqaTiWeTIBSN+Hgk2VvrrVNVlpzKEEJCyUPoee5mDFd0dJr2S+5ehzWkdHvC6Vok\n9cn9ej11kyMOJFeCXTCAjGndIwKBgQDRp+3W0i2vFMNL1PlFribXr7IscG5Ti7Oc\nohbdkG+jEXFBbOT3NR4rBEFG6ydQ/uECHeXmii/PvJzTIJlrxBJQnNXBMvCD3F/V\nTG9RoVt1Fgq+TRuguSFD2GGRVP4MOJHwW7guTbobIkTZ1ASVn8UHvjkVBNJ6HEzh\ntJMMfkm+AwKBgQCcwVDtsA0OuiOteKKnGlFCKjLoq3yV15llVpW1ITyZf+IXcQpQ\nZvAn/kzLSJPsIlOBIsix0tKfwmczrEIJHgjli+6nBB3L/CEG5Qc0uUL4nbDrti//\nTX/+f92RSARVkqmqtMyDM/KJb4B1G/4mp1ro50dBN8eWF1sfv+49JNQRDQKBgFDU\nnkKL5B3nv5FexNaXCveD8MRJnCnIVc1sZNv2XOSNCj0qtJB2XEhl9m3kvIkpc6f05\n77ARaNuLmV7gu6XLw0/nF5ZUAFymMyB2RpjPQAaFSAEUk2lE1ulkXEF+5i9qBAIK\nKplXiD/711WwI1BYd8tDcJiE8mz3ykBesS7o5Z9nAoGBALSg4QKF60JdQyP+yN8K\nGoX5JbusjZMVGN0FwSZyiyJW3jSa04N6D+OZt+yReqT7LdZpdvHHKvsEzHtItJjf\nGTZsC0AQpi8dgKSqhnz0MQGKxA6d7bsjbfqBhrJe+dliGVfKSJUoPbJ5PB4HcAXh\nAzUorgOKgXEaBUp7VBxhpiWK\n-----END PRIVATE KEY-----\n",
    "client_email": "foodstock-bot@my-food-stock-app.iam.gserviceaccount.com",
    "token_uri": "https://oauth2.google.com/token",
}

# 表示用の接続（これまでの方法）
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 入力フォーム ---
st.sidebar.header("新しい在庫の追加")
with st.sidebar.form("add_form"):
    name = st.text_input("品名")
    amount = st.number_input("数量", min_value=1, step=1)
    expiry_date = st.date_input("賞味期限")
    category = st.selectbox("カテゴリー", ["冷蔵", "冷凍", "常温", "その他"])
    submit_button = st.form_submit_button("在庫を追加する")

if submit_button and name:
    try:
        # 直接スプレッドシートにアクセスして1行追加する
        gc = gspread.service_account_from_dict(creds_dict)
        sh = gc.open_by_url(URL)
        worksheet = sh.get_worksheet(0) # 一番左のシート
        
        # 追加するデータ
        new_row = [name, int(amount), expiry_date.strftime('%Y/%m/%d'), category]
        worksheet.append_row(new_row)
        
        st.success(f"「{name}」をスプレッドシートに追加しました！")
        st.balloons()
    except Exception as e:
        st.error(f"追加エラーが発生しました: {e}")

# --- 一覧表示 ---
try:
    df = conn.read(spreadsheet=URL, ttl=0)
    st.dataframe(df, use_container_width=True)
except:
    st.info("スプレッドシートを読み込んでいます...")

