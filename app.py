import streamlit as st
import gspread
import pandas as pd
from datetime import datetime, date
import requests
import urllib.parse

# --- 設定 ---
st.set_page_config(page_title="LINE在庫管理", layout="wide")
URL = "https://docs.google.com/spreadsheets/d/10Hhcn0qNOvGceSNWLxy3_IOCJTvS1i9xaarZirmUUdw/edit?usp=sharing"

# --- LINEログイン用の自作関数 ---
def get_line_login_url():
    client_id = st.secrets["line"]["login_channel_id"]
    redirect_uri = st.secrets["app_url"]
    state = "random_string"
    url = f"https://access.line.me/oauth2/v2.1/authorize?response_type=code&client_id={client_id}&redirect_uri={urllib.parse.quote(redirect_uri)}&state={state}&scope=profile%20openid"
    return url

def get_line_user_info(code):
    # トークン取得
    token_url = "https://api.line.me/oauth2/v2.1/token"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": st.secrets["app_url"],
        "client_id": st.secrets["line"]["login_channel_id"],
        "client_secret": st.secrets["line"]["login_channel_secret"]
    }
    res = requests.post(token_url, headers=headers, data=data).json()
    id_token = res.get("id_token")
    
    # IDトークンをデコードしてユーザー情報を取得
    payload = {"id_token": id_token, "client_id": st.secrets["line"]["login_channel_id"]}
    user_info = requests.post("https://api.line.me/oauth2/v2.1/verify", data=payload).json()
    return user_info

# --- 🔐 ログイン処理 ---
query_params = st.query_params
if "code" not in query_params:
    st.title("🔐 在庫管理ログイン")
    login_url = get_line_login_url()
    st.markdown(f'<a href="{login_url}" target="_self" style="background-color: #00B900; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; font-weight: bold;">LINEでログイン</a>', unsafe_allow_html=True)
    st.stop()
else:
    code = query_params["code"]
    user_info = get_line_user_info(code)
    user_id = user_info.get("sub")
    user_name = user_info.get("name")

# --- 以降、メインの在庫管理プログラム（前回のものと同じ） ---
st.title(f"🍎 {user_name} さんの在庫リスト")
# (ここから下のスプレッドシート処理などはそのまま継続)
