import streamlit as st
import re

st.set_page_config(
    page_title="競輪投資AI",
    layout="wide"
)

st.title("競輪投資AI")

# ----------------------------
# 入力欄
# ----------------------------

race_data = st.text_area(
    "レースデータ入力",
    height=350,
    placeholder="競輪データを貼り付け"
)

# ----------------------------
# AI解析
# ----------------------------

def analyze_race(data):

    lines = data.splitlines()

    ai_score = 70

    result = []

    # 選手抽出
    riders = []

    for line in lines:

        m = re.search(r'^\d+\s+\d+\s+([^\(]+)', line)

        if m:
            riders.append(m.group(1).strip())

    # 簡易AIロジック
    if len(riders) >= 3:

        main = riders[0]
        second = riders[1]
        third = riders[2]

        ai_score = 87

        result.append(f"◎本命 {main}")
        result.append(f"○対抗 {second}")
        result.append(f"▲穴 {third}")

        result.append("")
        result.append("【推奨買い目】")
        result.append(f"{main}-{second}-{third}")
        result.append(f"{main}-{third}-{second}")

    else:

        ai_score = 40

        result.append("データ解析不足")

    return "\n".join(result), ai_score

# ----------------------------
# session_state 初期化
# ----------------------------

if "result" not in st.session_state:
    st.session_state.result = ""

if "ai_score" not in st.session_state:
    st.session_state.ai_score = 0

# ----------------------------
# 解析ボタン
# ----------------------------

if st.button("解析開始"):

    if race_data.strip() == "":

        st.warning("レースデータを入力してください")

    else:

        with st.spinner("AI解析中..."):

            result, ai_score = analyze_race(race_data)

            st.session_state.result = result
            st.session_state.ai_score = ai_score

# ----------------------------
# AIスコア表示
# ----------------------------

if st.session_state.ai_score > 0:

    st.subheader("AIスコア")

    st.metric(
        label="期待値スコア",
        value=int(st.session_state.ai_score)
    )

# ----------------------------
# 解析確認表示
# ----------------------------

if st.session_state.result != "":

    st.subheader("解析確認")

    st.text(st.session_state.result)