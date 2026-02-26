import streamlit as st
from streamlit_gsheets import GSheetsConnection

st.title("食品在庫管理アプリ")

# 接続設定
try:
    # 💡 point: Secretsの [connections.gsheets] という階層を無視して読み込む設定
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # 💡 point: URLはSecretsに頼らず、ここに直接書くのが一番確実です
    url = "https://docs.google.com/spreadsheets/d/10Hhcn0qNOvGceSNWLxy3_IOCJTvS1i9xaarZirmUUdw/edit?usp=sharing"
    
    df = conn.read(spreadsheet=url, ttl=0)
    st.write("### 現在の在庫一覧")
    st.dataframe(df)
except Exception as e:
    st.error("エラーが発生しました。設定を確認してください。")
    st.code(e)
