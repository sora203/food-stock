import streamlit as st
import gspread
import pandas as pd
from datetime import datetime, date
import requests
import time

# --- 🎨 デザイン ---
def local_css():
    st.markdown("""
        <style>
        .stApp { background-image: url("https://www.toptal.com/designers/subtlepatterns/uploads/wood_pattern.png"); background-repeat: repeat; background-attachment: fixed; }
        [data-testid="stAppViewBlockContainer"] { background-color: rgba(245, 222, 179, 0.7); padding: 3rem; border-radius: 15px; margin-top: 2rem; }
        [data-testid="stSidebar"] { background-color: #262730 !important; }
        header { background-color: rgba(0,0,0,0) !important; }
        [data-testid="stHeader"] button { color: white !important; fill: white !important; }
        .main-title { font-size: 3.5rem; font-weight: 900; color: #3e2723; line-height: 1.1; margin-bottom: 20px; }
        #MainMenu, footer {visibility: hidden;}
        </style>
    """, unsafe_allow_html=True)

st.set_page_config(page_title="在庫管理メモ", layout="wide")
local_css()

# --- 設定 ---
URL = "https://docs.google.com/spreadsheets/d/10Hhcn0qNOvGceSNWLxy3_IOCJTvS1i9xaarZirmUUdw/edit?usp=sharing"
SHEET_NAME = "在庫データ"

# --- 💡 クライアント取得 ---
@st.cache_resource(ttl=600)
def get_gspread_client():
    raw_key = st.secrets["connections"]["gsheets"]["private_key"].replace("\\n", "\n").strip()
    creds = {"type": "service_account", "project_id": "my-food-stock-app", "private_key": raw_key,
             "client_email": st.secrets["connections"]["gsheets"]["client_email"], "token_uri": "https://www.googleapis.com/oauth2/v4/token"}
    return gspread.service_account_from_dict(creds)

# --- 💡 データ取得（リトライ・エラー回避強化版） ---
@st.cache_data(ttl=20) # キャッシュを20秒に。これでGoogleへの負担を大幅カット。
def get_data_cached(_sheet_name):
    client = get_gspread_client()
    sh = client.open_by_url(URL)
    # ここで直接シートを開き、失敗したらリトライ
    for i in range(3):
        try:
            ws = sh.worksheet(SHEET_NAME)
            return ws.get_all_records()
        except:
            time.sleep(2)
    return []

# --- 💡 書き込み関数 ---
def write_to_google_safe(func, *args):
    client = get_gspread_client()
    sh = client.open_by_url(URL)
    ws = sh.worksheet(SHEET_NAME)
    for i in range(3):
        try:
            res = func(ws, *args)
            st.cache_data.clear() # 書き込んだらキャッシュを消す
            return res
        except:
            time.sleep(1.5)
    return None

# --- LINEログイン (略) ---
def get_line_login_url():
    return (f"https://access.line.me/oauth2/v2.1/authorize?response_type=code&client_id={st.secrets['line']['login_channel_id']}"
            f"&redirect_uri=https://food-memo-app.streamlit.app&state=random&scope=profile%20openid")

def get_line_user_info(code):
    res = requests.post("https://api.line.me/oauth2/v2.1/token", data={
        "grant_type": "authorization_code", "code": code, "redirect_uri": "https://food-memo-app.streamlit.app",
        "client_id": st.secrets["line"]["login_channel_id"], "client_secret": st.secrets["line"]["login_channel_secret"]
    }).json()
    return requests.post("https://api.line.me/oauth2/v2.1/verify", data={
        "id_token": res.get("id_token"), "client_id": st.secrets["line"]["login_channel_id"]
    }).json()

# --- 🔐 ログイン ---
if "user_id" not in st.session_state:
    qp = st.query_params
    if "code" not in qp:
        st.markdown("<h1 style='text-align: center;'>Stock Manager</h1>", unsafe_allow_html=True)
        st.link_button("LINEでログイン", get_line_login_url())
        st.stop()
    else:
        u_info = get_line_user_info(qp["code"])
        st.session_state.user_id = str(u_info.get("sub"))
        st.session_state.user_name = u_info.get("displayName") or "利用者"
        st.query_params.clear()

uid, uname = st.session_state.user_id, st.session_state.user_name
st.markdown(f"<div>{uname} 様</div><div class='main-title'>在庫リスト</div>", unsafe_allow_html=True)

# --- 🍎 メイン処理 ---
all_recs = get_data_cached(SHEET_NAME)
all_df = pd.DataFrame(all_recs) if all_recs else pd.DataFrame(columns=["品名", "数量", "賞味期限", "保存場所", "種類", "LINE_ID"])
all_df["LINE_ID"] = all_df["LINE_ID"].astype(str)
df = all_df[all_df["LINE_ID"] == uid].copy()

# --- サイドバー ---
with st.sidebar:
    st.markdown("### 在庫を追加")
    with st.form("add_form", clear_on_submit=True):
        n = st.text_input("品名")
        a = st.number_input("数量", min_value=1, value=1)
        e = st.date_input("賞味期限", value=date.today()).strftime('%Y/%m/%d')
        c1 = st.selectbox("保存場所", ["冷蔵", "冷凍", "常温", "その他"])
        c2 = st.selectbox("種類", ["肉", "野菜", "麺", "飲み物", "その他"])
        if st.form_submit_button("追加") and n:
            m = (all_df['品名'] == n) & (all_df['賞味期限'] == e) & (all_df['保存場所'] == c1) & (all_df['種類'] == c2) & (all_df['LINE_ID'] == uid)
            if m.any():
                idx = all_df.index[m][0]
                new_val = int(all_df.at[idx, '数量']) + a
                if write_to_google_safe(lambda ws, r, c, v: ws.update_cell(r, c, v), int(idx) + 2, 2, int(new_val)):
                    st.rerun()
            else:
                if write_to_google_safe(lambda ws, row: ws.append_row(row), [n, int(a), e, c1, c2, uid]):
                    st.rerun()

# --- リスト ---
if not df.empty:
    ed_res = st.data_editor(df.assign(選択=False)[["選択", "品名", "数量", "賞味期限", "保存場所", "種類"]], 
                            use_container_width=True, hide_index=True, key="ed",
                            column_config={"選択": st.column_config.CheckboxColumn()})

    # 数量変更
    if st.session_state.ed["edited_rows"]:
        for r_idx, chg in st.session_state.ed["edited_rows"].items():
            if "数量" in chg:
                actual_idx = df.index[r_idx]
                if write_to_google_safe(lambda ws, r, c, v: ws.update_cell(r, c, v), int(actual_idx) + 2, 2, int(chg["数量"])):
                    st.rerun()

    # 削除
    if st.button("🗑️ 選択項目を削除", type="primary"):
        del_indices = ed_res[ed_res["選択"] == True].index.tolist()
        if del_indices:
            new_all = all_df.drop(del_indices)
            def bulk_update(ws, data):
                ws.clear()
                ws.update('A1', [all_df.columns.tolist()] + data.values.tolist())
            if write_to_google_safe(bulk_update, new_all):
                st.rerun()
else:
    st.info("データがありません。")
