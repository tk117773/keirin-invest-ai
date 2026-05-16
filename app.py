import streamlit as st
import re

st.set_page_config(
    page_title="KEIRIN INVEST AI",
    layout="wide"
)

st.title("🚴 KEIRIN INVEST AI Version8")

# =========================
# Session State
# =========================

if "race_data" not in st.session_state:
    st.session_state["race_data"] = ""

# =========================
# 全国競輪場補正
# =========================

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

# =========================
# 開催場解析
# =========================

def extract_place(text):

    places = list(BANK_BONUS.keys())

    for place in places:

        if place in text:

            return place

    return "不明"

# =========================
# ライン解析
# =========================

def extract_lines(text):

    nums = re.findall(r'\b[1-9]\b', text)

    if len(nums) >= 7:

        return (
            nums[0:3],
            nums[3:6],
            nums[6]
        )

    return None

# =========================
# 選手解析
# =========================

def extract_players(text):

    players = []

    lines = text.split("\n")

    for line in lines:

        line = line.strip()

        if "(" in line and ")" in line:

            try:

                parts = line.split("(")

                left = parts[0].strip()

                cols = left.split()

                if len(cols) >= 3:

                    car_no = cols[0]

                    name = cols[2]

                    players.append((car_no, name))

            except:

                pass

    return players

# =========================
# 勝率解析
# =========================

def extract_rates(text):

    rates = []

    lines = text.split("\n")

    for line in lines:

        nums = re.findall(r'\d+\.\d+', line)

        if len(nums) >= 3:

            try:

                rate = float(nums[0])

                if 0 <= rate <= 100:

                    rates.append(rate)

            except:

                pass

    return rates

# =========================
# B数解析
# =========================

def extract_b_numbers(text):

    b_list = []

    lines = text.split("\n")

    for line in lines:

        nums = re.findall(r'\d+', line)

        if len(nums) > 5:

            try:

                b = int(nums[1])

                b_list.append(b)

            except:

                pass

    return b_list

# =========================
# 入力欄
# =========================

race_data = st.text_area(
    "競輪データ貼付",
    height=400,
    key="race_data"
)

# =========================
# クリアボタン
# =========================

if st.button("クリア"):

    st.session_state["race_data"] = ""

    st.rerun()

# =========================
# AI予想開始
# =========================

if st.button("AI予想開始"):

    place = extract_place(race_data)

    st.header("開催場")
    st.success(place)

    result = extract_lines(race_data)

    if result:

        main_line, rival_line, solo = result

        st.header("ライン解析")

        st.write(f"本命ライン : {'-'.join(main_line)}")

        st.write(f"対抗ライン : {'-'.join(rival_line)}")

        st.write(f"単騎 : {solo}")

        players = extract_players(race_data)

        rates = extract_rates(race_data)

        b_nums = extract_b_numbers(race_data)

        scores = []

        for i in range(min(len(players), len(rates))):

            car_no = players[i][0]
            name = players[i][1]

            rate = rates[i]

            b = 0

            if i < len(b_nums):
                b = b_nums[i]

            score = rate + (b * 2)

            if place in BANK_BONUS:
                score += BANK_BONUS[place]

            scores.append((car_no, name, score))

        sorted_scores = sorted(
            scores,
            key=lambda x: x[2],
            reverse=True
        )

        st.header("AIスコア")

        for rank, data in enumerate(sorted_scores, start=1):

            car_no, name, score = data

            st.write(
                f"{rank}位 {car_no} {name} AI点数 {round(score,1)}"
            )

        if len(sorted_scores) >= 3:

            st.header("推奨3連単")

            first = sorted_scores[0][0]
            second = sorted_scores[1][0]
            third = sorted_scores[2][0]

            st.success(f"{first}-{second}-{third}")

            st.header("AI期待値")

            ev = round(
                (
                    sorted_scores[0][2]
                    + sorted_scores[1][2]
                    + sorted_scores[2][2]
                ) * 3,
                1
            )

            st.success(f"{ev}%")

            st.header("投資判断")

            if ev >= 300:

                st.success("強く買い")

            elif ev >= 200:

                st.warning("買い")

            else:

                st.error("見送り")

    else:

        st.error("ライン解析失敗")

        st.write("並び予想部分を確認してください")