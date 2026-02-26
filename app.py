import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

st.set_page_config(page_title="在庫管理アプリ", layout="wide")
st.title("🍎 食品在庫管理システム")

# スプレッドシートのURL
URL = "https://docs.google.com/spreadsheets/d/10Hhcn0qNOvGceSNWLxy3_IOCJTvS1i9xaarZirmUUdw/edit?usp=sharing"

# 💡 究極の解決策：Secretsを使わず、ここに直接設定を書く！
creds = {
    "type": "service_account",
    "project_id": "my-food-stock-app",
    "private_key_id": "75d12b638a7f1bcbb74bdbe4a62bfabd586e1741",
    "private_key": """-----BEGIN PRIVATE KEY-----
MIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQC7pEdlh6ySjEmN
Zcs6SbvMpEI43WAJX7DCss3NYoTnDNW5uDth919R64pBW8tNbzXB4KzPmfLoZWDT
I4Il1+1SXCk8LldQwkGJ7wPMgPSSg4hKKFA+EA8m5Hldy0pk2ESSKSlYFGX3+pqN
NgKqLRAZDykX6u+aDwO0GTqL+Kl2aOgZwtLT5efZ9aBlVs1UP5Y1W8Mw3yAP8VZF
+vdqjRdfvJ0BoikPhBrtqxpc2ntP70OzzEwwKMPT8a8fwN89j361rwegEbXj14E8
/lRDCeFmOMC4voRli5eBdzedCDYwdVfFeqvbm9hXA9rlETDKup3F1ZmxaJDBEGlo
lWOAWJFpAgMBAAECggEALuDS6X2k0pPzyDyXMj+7iFu9I6HC3XSnn2y2V8p2M5cU
SirJwybfDINQ7hU1zGmtP3uXEOKAOikhsH4dhMDWTI4zyxI0xDtTzlcFVvEcqQHt
acF6kpbGgkvwOkuQkXMqZm2cI6Is+3ADbqYAsm1BqVENTilmpNF9dmAbLV75T1hm
jUmqisaoSMlOLmYJ9IRN+g+L5T29J9PfDmdBCZjgFOVzdg2Uiwqf0DL6x6iwYik7
ZpdFJ4FNki31asQsSkchJBce2XAACLM0F8quwGuFWOT79HBGoZk2i/g9Zuy1xk+x
2ubkvXD/WgEypQ5D0/LJUQBfsFb518Ok7dTMxGVrFQKBgQDlHpnOhCHWrpAUzpdY
K7arsPbwOKrs64tfc0qBsI6pDEXhNbCxUdHLB8ffsUA2Y7sBB4M9n/4Yq7A9UPsn
oqaTiWeTIBSN+Hgk2VvrrVNVlpzKEEJCyUPoee5mDFd0dJr2S+5ehzWkdHvC6Vok
9cn9ej11kyMOJFeCXTCAjGndIwKBgQDRp+3W0i2vFMNL1PlFribXr7IscG5Ti7Oc
ohbdkG+jEXFBbOT3NR4rBEFG6ydQ/uECHeXmii/PvJzTIJlrxBJQnNXBMvCD3F/V
TG9RoVt1Fgq+TRuguSFD2GGRVP4MOJHwW7guTbobIkTZ1ASVn8UHvjkVBNJ6HEzh
tJMMfkm+AwKBgQCcwVDtsA0OuiOteKKnGlFCKjLoq3yV15llVpW1ITyZf+IXcQpQ
ZvAn/kzLSJPsIlOBIsix0tKfwmczrEIJHgjli+6nBB3L/CEG5Qc0uUL4nbDrti//
TX/+f92RSARVkqmqtMyDM/KJb4B1G/4mp1ro50dBN8eWF1sfv+49JNQRDQKBgFDU
nkKL5B3nv5FexNaXCveD8MRJnCnIVc1sZNv2XOSNCj0qtJB2XEhl9m3kvIkpc6f05
77ARaNuLmV7gu6XLw0/nF5ZUAFymMyB2RpjPQAaFSAEUk2lE1ulkXEF+5i9qBAIK
KplXiD/711WwI1BYd8tDcJiE8mz3ykBesS7o5Z9nAoGBALSg4QKF60JdQyP+yN8K
GoX5JbusjZMVGN0FwSZyiyJW3jSa04N6D+OZt+yReqT7LdZpdvHHKvsEzHtItJjf
GTZsC0AQpi8dgKSqhnz0MQGKxA6d7bsjbfqBhrJe+dliGVfKSJUoPbJ5PB4HcAXh
AzUorgOKgXEaBUp7VBxhpiWK
-----END PRIVATE KEY-----""",
    "client_email": "foodstock-bot@my-food-stock-app.iam.gserviceaccount.com",
}

# 接続の作成
conn = st.connection("gsheets", type=GSheetsConnection, **creds)

# --- 入力フォーム ---
st.sidebar.header("新しい在庫の追加")
with st.sidebar.form("add_form"):
    name = st.text_input("品名")
    amount = st.number_input("数量", min_value=1, step=1)
    expiry_date = st.date_input("賞味期限")
    category = st.selectbox("カテゴリー", ["冷蔵", "冷凍", "常温", "その他"])
    submit_button = st.form_submit_button("在庫を追加する")

if submit_button and name:
    # 既存データを読み込んで追加
    existing_data = conn.read(spreadsheet=URL, ttl=0)
    new_row = pd.DataFrame([{
        "name": name,
        "amount": amount,
        "expiry_date": expiry_date.strftime('%Y/%m/%d'),
        "category": category
    }])
    updated_df = pd.concat([existing_data, new_row], ignore_index=True)
    
    # 書き込み実行
    conn.update(spreadsheet=URL, data=updated_df)
    st.success(f"「{name}」を追加しました！")
    st.balloons()

# --- 表示 ---
df = conn.read(spreadsheet=URL, ttl=0)
st.dataframe(df, use_container_width=True)
