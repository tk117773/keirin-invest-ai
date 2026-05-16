import streamlit as st
import re
import pandas as pd
import os

st.set_page_config(
    page_title="KEIRIN AI Version8",
    layout="wide"
)

st.title("🚴 KEIRIN INVEST AI Version8")

DB_FILE = "results.csv"

if "race_data" not in st.session_state:

    st.session_state["race_data"] = ""

race_data = st.text_area(
    "競輪データ貼付",
    height=500,
    key="race_data"
)

if st.button("クリア"):

    st.session_state["race_data"] = ""

    st.rerun()

odds_input = st.number_input(
    "想定オッズ",
    min_value=1.0,
    value=10.0,
    step=0.1
)

BANK_BONUS = {

    "函館": 4,
    "青森": 5,
    "いわき平": 6,
    "弥彦": 4,
    "前橋": 5,
    "取手": 5,
    "宇都宮": 5,
    "大宮": 4,
    "西武園": 4,
    "京王閣": 3,
    "立川": 4,
    "松戸": 4,
    "千葉": 5,
    "川崎": 3,
    "平塚": 3,
    "小田原": 2,
    "伊東": 5,
    "静岡": 5,
    "名古屋": 4,
    "岐阜": 5,
    "大垣": 4,
    "豊橋": 5,
    "富山": 4,
    "松阪": 5,
    "四日市": 6,
    "福井": 4,
    "奈良": 4,
    "向日町": 5,
    "和歌山": 5,
    "岸和田": 6,
    "玉野": 5,
    "広島": 4,
    "防府": 4,
    "高松": 4,
    "小松島": 5,
    "高知": 6,
    "松山": 5,
    "小倉": 6,
    "久留米": 5,
    "武雄": 4,
    "佐世保": 5,
    "別府": 6,
    "熊本": 5
}

def extract_place(text):

    for bank in BANK_BONUS.keys():

        if bank in text:
            return bank

    return "不明"

def extract_lines(text):

    nums = re.findall(r'[1-9]', text)

    if len(nums) >= 7:

        return (
            nums[0:3],
            nums[3:6],
            nums[6]
        )

    return None

def extract_players(text):

    pattern = r'([1-9])\s+[1-9]\s+([^\(]+)\('

    result = re.findall(pattern, text)

    return result

def extract_rates(text):

    rates = re.findall(r'\d+\.\d+', text)

    clean_rates = []

    for r in rates:

        value = float(r)

        if 0 < value <= 100:

            clean_rates.append(value)

    return clean_rates

def ai_structure_analysis(player_name):

    score = 0

    if "逃" in player_name:
        score += 10

    if "追" in player_name:
        score += 5

    return score

def calc_score(rate, bonus):

    score = 0

    score += float(rate) * 1.5
    score += bonus

    return round(score, 1)

def calc_expected_value(score, odds):

    win_prob = min(score / 100, 0.9)

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

        count = min(
            len(players),
            len(rates)
        )

        if count == 0:

            st.error("解析失敗")

            st.stop()

        for i in range(count):

            name = players[i][1].strip()

            structure_bonus = ai_structure_analysis(name)

            score = calc_score(
                rates[i],
                bank_bonus + structure_bonus
            )

            ai_scores[name] = score

        sorted_scores = sorted(
            ai_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )

        for rank, (name, score) in enumerate(sorted_scores, start=1):

            st.write(f"{rank}位 {name} AI点数 {score}")

        top_score = sorted_scores[0][1]

        ev = calc_expected_value(
            top_score,
            odds_input
        )

        st.subheader("人気危険度")

        if odds_input <= 3:

            st.error("過剰人気")

        elif odds_input <= 8:

            st.warning("標準人気")

        else:

            st.success("穴期待値")

        st.subheader("AI期待値")

        st.success(f"{ev}%")

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
            f"{single}-{line2[0]}-{line1[1]}"
        ]

        for bet in bets:

            st.write(bet)
    else:

        st.error("ライン解析失敗")

        st.write("並び予想部分を確認してください")
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