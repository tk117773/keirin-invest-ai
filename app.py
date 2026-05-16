import streamlit as st
import re
import pandas as pd

# =========================
# ページ設定
# =========================
st.set_page_config(
    page_title="競輪投資AI",
    layout="wide"
)

st.title("競輪投資AI（期待値分析版）")

# =========================
# 入力欄
# =========================
race_data = st.text_area(
    "レースデータ入力",
    height=400,
    placeholder="競輪データを貼り付け"
)

# =========================
# データ解析
# =========================
def analyze_race(data):

    lines = data.splitlines()

    players = []

    current_player = {}

    for line in lines:

        line = line.strip()

        # 選手行判定
        match = re.match(
            r"(\d+)\s+(\d+)\s+([^\(]+)\((\d+)\)",
            line
        )

        if match:

            if current_player:
                players.append(current_player)

            current_player = {
                "車番": match.group(2),
                "選手名": match.group(3).strip(),
                "年齢": int(match.group(4))
            }

            continue

        # 成績行取得
        nums = re.findall(r"\d+\.\d+|\d+", line)

        if len(nums) >= 10 and current_player:

            try:
                current_player["S"] = int(nums[0])
                current_player["B"] = int(nums[1])
                current_player["逃"] = int(nums[2])
                current_player["捲"] = int(nums[3])
                current_player["差"] = int(nums[4])
                current_player["マ"] = int(nums[5])
                current_player["勝率"] = float(nums[6])
                current_player["連対率"] = float(nums[7])
                current_player["3連対率"] = float(nums[8])

            except:
                pass

    # 最後追加
    if current_player:
        players.append(current_player)

    # =========================
    # AIスコア計算
    # =========================

    for p in players:

        score = 0

        score += p.get("勝率", 0) * 2
        score += p.get("連対率", 0) * 1.2
        score += p.get("3連対率", 0)

        score += p.get("B", 0) * 2
        score += p.get("逃", 0) * 1.5
        score += p.get("捲", 0) * 2
        score += p.get("差", 0) * 1.8
        score += p.get("マ", 0)

        # 若手機動型補正
        if p.get("年齢", 50) <= 35:
            score += 5

        # 高齢追込減点
        if p.get("年齢", 0) >= 48 and p.get("B", 0) == 0:
            score -= 3

        p["AIスコア"] = round(score, 1)

    # =========================
    # スコア順
    # =========================
    players_sorted = sorted(
        players,
        key=lambda x: x["AIスコア"],
        reverse=True
    )

    # =========================
    # 印
    # =========================
    marks = ["◎", "○", "▲", "☆"]

    result_text = ""

    for i, p in enumerate(players_sorted[:4]):

        result_text += (
            f"{marks[i]} "
            f"{p['車番']}番 "
            f"{p['選手名']} "
            f"AI:{p['AIスコア']}\n"
        )

    # =========================
    # 買い目生成
    # =========================
    top3 = players_sorted[:3]

    if len(top3) >= 3:

        a = top3[0]["車番"]
        b = top3[1]["車番"]
        c = top3[2]["車番"]

        bets = [
            f"{a}-{b}-{c}",
            f"{a}-{c}-{b}",
            f"{b}-{a}-{c}",
            f"{a}-{b}-全"
        ]

    else:
        bets = []

    result_text += "\n【推奨買い目】\n"

    for b in bets:
        result_text += f"{b}\n"

    # =========================
    # DataFrame
    # =========================
    df = pd.DataFrame(players_sorted)

    return result_text, df


# =========================
# 実行
# =========================
if st.button("解析開始"):

    if race_data.strip() == "":

        st.warning("レースデータを入力してください")

    else:

        with st.spinner("AI解析中..."):

            result, df = analyze_race(race_data)

        # =========================
        # AIランキング
        # =========================
        st.subheader("AIスコアランキング")

        if "AIスコア" in df.columns:

            for i in range(min(4, len(df))):

                col1, col2 = st.columns([1, 4])

                with col1:
                    st.metric(
                        f"{df.iloc[i]['車番']}番",
                        df.iloc[i]["AIスコア"]
                    )

                with col2:
                    st.write(df.iloc[i]["選手名"])

        # =========================
        # 表表示
        # =========================
        st.subheader("解析確認")

        display_cols = [
            "車番",
            "選手名",
            "AIスコア",
            "勝率",
            "連対率",
            "3連対率",
            "B",
            "逃",
            "捲",
            "差"
        ]

        existing_cols = [
            c for c in display_cols
            if c in df.columns
        ]

        st.dataframe(
            df[existing_cols],
            use_container_width=True
        )

        # =========================
        # 最終予想
        # =========================
        st.subheader("AI最終予想")

        st.text(result)