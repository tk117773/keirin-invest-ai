import streamlit as st
import re
import pandas as pd
import os


st.set_page_config(
    page_title="KEIRIN INVEST AI FINAL",
    layout="wide"
)

st.title("🚴 KEIRIN INVEST AI FINAL")
st.write("Version 7")

DB_FILE = "results.csv"

if "race_data" not in st.session_state:
    st.session_state.race_data = ""

race_data = st.text_area(
    "競輪データ貼付",
    height=500,
    key="race_data"
)

if st.button("クリア"):
    st.session_state.race_data = ""
    st.rerun()

odds_input = st.number_input(
    "想定オッズ",
    min_value=1.0,
    value=10.0,
    step=0.1
)

BANK_BONUS = {
    "宇都宮": 5,
    "平塚": 3,
    "松戸": 4,
    "小田原": 2,
    "高知": 6
}

def extract_place(text):

    for bank in BANK_BONUS.keys():

        if bank in text:
            return bank

    return "不明"

def extract_lines(text):

    numbers = re.findall(r'\b[1-9]\b', text)

    if len(numbers) >= 7:

        return (
            numbers[0:3],
            numbers[3:6],
            numbers[6]
        )

    return None

def extract_players(text):

    pattern = r'([1-9])\s+[1-9]\s+([^\(]+)\('

    return re.findall(pattern, text)

def extract_rates(text):

    return re.findall(r'\d+\.\d+', text)

def extract_b(text):

    b_list = []

    lines = text.split("\n")

    for line in lines:

        cols = line.split()

        if len(cols) > 10:

            try:
                b = int(cols[4])
                b_list.append(b)

            except:
                pass

    return b_list

def calc_score(rate, b, bonus):

    score = 0

    score += float(rate) * 1.8
    score += int(b) * 4
    score += bonus

    return round(score, 1)

def calc_expected_value(score, odds):

    win_prob = min(score / 120, 0.9)

    ev = round(win_prob * odds * 100, 1)

    return ev

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

        return df, total, hit_rate, profit

    return pd.DataFrame(), 0, 0, 0

if st.button("AI予想開始"):

    place = extract_place(race_data)

    bank_bonus = BANK_BONUS.get(place, 0)

    result = extract_lines(race_data)

    players = extract_players(race_data)

    rates = extract_rates(race_data)

    b_counts = extract_b(race_data)

    if result:

        line1, line2, single = result

        st.subheader("開催場")

        st.write(place)

        st.subheader("ライン解析")

        st.write(f"本命ライン：{'-'.join(line1)}")
        st.write(f"対抗ライン：{'-'.join(line2)}")
        st.write(f"単騎：{single}")

        st.subheader("AIスコア")

        ai_scores = {}

        for i in range(min(len(players), len(rates), len(b_counts))):

            name = players[i][1].strip()

            score = calc_score(
                rates[i],
                b_counts[i],
                bank_bonus
            )

            ai_scores[name] = score

        sorted_scores = sorted(
            ai_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )

       if len(sorted_scores) == 0:

            st.error("選手データ解析失敗")

            st.stop()

        for rank, (name, score) in enumerate(sorted_scores, start=1):

            st.write(f"{rank}位 {name} AI点数 {score}")

        top_score = sorted_scores[0][1]
            st.write(f"{rank}位 {name} AI点数 {score}")

        ev = calc_expected_value(
            top_score,
            odds_input
        )

        st.subheader("人気危険度")

        if odds_input <= 3:
            st.error("過剰人気注意")

        elif odds_input <= 8:
            st.warning("人気ゾーン")

        else:
            st.success("穴期待値あり")

        st.subheader("AI期待値")

        st.success(f"期待値：{ev}%")

        st.subheader("投資判断")

        if ev >= 130:
            st.success("強く買い")

        elif ev >= 100:
            st.warning("買い候補")

        else:
            st.error("見送り")

        st.subheader("推奨3連単")

        bets = [
            f"{line1[1]}-{line1[0]}-{line2[0]}",
            f"{line1[0]}-{line1[1]}-{line2[0]}",
            f"{line2[0]}-{line2[1]}-{line1[1]}",
            f"{single}-{line1[1]}-{line1[0]}",
            f"{line1[1]}-{single}-{line1[0]}",
            f"{line2[0]}-{line1[1]}-{single}",
            f"{single}-{line2[0]}-{line1[1]}",
            f"{line1[0]}-{single}-{line2[0]}"
        ]

        for bet in bets:
            st.write(bet)

st.subheader("結果登録")

race_name = st.text_input("レース名")

hit = st.checkbox("的中")

profit = st.number_input(
    "収支",
    step=100
)

if st.button("結果保存"):

    save_result(
        race_name,
        hit,
        profit
    )

    st.success("保存完了")

df, total, hit_rate, total_profit = load_stats()

st.subheader("投資成績")

st.write(f"総レース数：{total}")
st.write(f"的中率：{hit_rate}%")
st.write(f"総収支：{total_profit}円")

if not df.empty:

    st.subheader("過去レースDB")

    df["累計収支"] = df["profit"].cumsum()

    st.dataframe(df)

    st.subheader("累計収支")

    st.write(df["累計収支"].tolist())