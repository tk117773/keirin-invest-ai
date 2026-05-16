import streamlit as st

st.set_page_config(
    page_title="KEIRIN INVEST AI",
    layout="wide"
)

st.title("🚴 KEIRIN INVEST AI")

st.write("競輪投資AI 起動成功")

race_data = st.text_area(
    "競輪データ貼付",
    height=300
)

if st.button("AI予想開始"):

    st.subheader("AI予想結果")

    st.write("本命：4-1-2")
    st.write("対抗：2-7-1")
    st.write("穴：5-1-4")

    st.write("期待値：★★★★☆")
