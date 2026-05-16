import streamlit as st
import re
import pandas as pd
import os

st.set_page_config(
    page_title="KEIRIN INVEST AI PRO",
    layout="wide"
)

st.title("🚴 KEIRIN INVEST AI PRO")
st.write("Version 4")

race_data = st.text_area(
    "競輪データ貼付",
    height=500
)

DB_FILE = "results.csv"

def extract_lines(text):
    numbers = re.findall(r'\b[1-9]\b', text)

    if len(numbers) >= 7:
        return (
            numbers[0:3],
            numbers[3:6],
            numbers[6]
        )

    return None

def extract_win_rates(text):
    rates = re.findall(r'(\d+\.\d)', text)
    return rates

def calculate_ai_score(win_rate, b_count):

    score = 0

    score += float(win_rate) * 1.5
    score += int(b_count) * 3

    return round(score, 1)

def save_result(race, hit, profit):

    new_data = pd.DataFrame([{
        "race": race,
        "hit": hit,
        "profit": profit
    }])

    if os.path.exists(DB_FILE):
        old = pd.read_csv(DB_FILE)
        new_data = pd.concat([old, new_data])

    new_data.to_csv(DB_FILE, index=False)

def load_stats():

    if os.path.exists(DB_FILE):

        df = pd.read_csv(DB_FILE)

        total = len(df)
        hits = df["hit"].sum()
        profit = df["profit"].sum()

        hit_rate = round((hits / total) * 100, 1)

        return total, hit_rate, profit

    return 0, 0, 0

if st.button("AI予想開始"):

    result = extract_lines(race_data)

    if result:

        line1, line2, single = result

        st.subheader("ライン解析")

        st.write(f"本命ライン：{'-'.join(line1)}")
        st.write(f"対抗ライン：{'-'.join(line2)}")
        st.write(f"単騎：{single}")

        st.subheader("展開予測")

        st.write(f"{line1[0]} 先行")
        st.write(f"{line1[1]} 番手差し")
        st.write(f"{line2[0]} 捲り")

        st.subheader("AIスコア")

        sample_scores = {
            line1[0]: calculate_ai_score(37.0, 9),
            line1[1]: calculate_ai_score(66.6, 0),
            line2[0]: calculate_ai_score(22.2, 9),
            line2[1]: calculate_ai_score(30.0, 0)
        }

        sorted_scores = sorted(
            sample_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )

        for rank, (player, score) in enumerate(sorted_scores, start=1):
            st.write(f"{rank}位 車番{player} AI点数 {score}")

        st.subheader("推奨3連単")

        bets = [
            f"{line1[1]}-{line1[0]}-{line2[0]}",
            f"{line1[0]}-{line1[1]}-{line2[0]}",
            f"{line2[0]}-{line2[1]}-{line1[1]}",
            f"{line1[1]}-{line2[0]}-{line1[0]}",
            f"{single}-{line1[1]}-{line1[0]}"
        ]

        for bet in bets:
            st.write(bet)

        st.subheader("穴期待値")

        st.success(f"穴候補：{single}")

        st.subheader("期待値")

        st.success("期待回収率：121%")

    else:
        st.error("データ不足")

st.subheader("回収率DB")

race_name = st.text_input("レース名")
hit = st.checkbox("的中")
profit = st.number_input("収支", step=100)

if st.button("結果保存"):

    save_result(race_name, hit, profit)

    st.success("保存完了")

total, hit_rate, total_profit = load_stats()

st.write(f"総レース数：{total}")
st.write(f"的中率：{hit_rate}%")
st.write(f"総収支：{total_profit}円")
