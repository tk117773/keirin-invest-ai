import streamlit as st
import pandas as pd
import re

# =====================================
# ページ設定
# =====================================

st.set_page_config(
    page_title="KEIRIN INVEST AI",
    layout="wide"
)

st.title("🚴 KEIRIN INVEST AI Ultimate")

# =====================================
# Session State
# =====================================

if "race_data" not in st.session_state:

    st.session_state["race_data"] = ""

# =====================================
# 全国競輪場補正
# =====================================

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

# =====================================
# 開催場抽出
# =====================================

def extract_place(text):

    for place in BANK_BONUS.keys():

        if place in text:

            return place

    return "不明"

# =====================================
# ライン解析
# =====================================

def extract_lines(text):

    lines = text.split("\n")

    nums = []

    start = False

    for line in lines:

        line = line.strip()

        if "並び予想" in line:

            start = True
            continue

        if start:

            if re.match(r'^[1-9]$', line):

                nums.append(line)

    # 9車対応
    if len(nums) >= 9:

        return (
            nums[0:3],
            nums[3:6],
            nums[6:9]
        )

    # 7車対応
    elif len(nums) >= 7:

        return (
            nums[0:3],
            nums[3:6],
            [nums[6]]
        )

    return None

# =====================================
# 選手解析
# =====================================

def extract_players(text):

    players = []

    lines = text.split("\n")

    current_player = {}

    for line in lines:

        line = line.strip()

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

    if current_player:

        players.append(current_player)

    return players

# =====================================
# AIスコア計算
# =====================================

def calculate_scores(players, place):

    for p in players:

        score = 0

        # 基本能力
        score += p.get("勝率", 0) * 2
        score += p.get("連対率", 0) * 1.5
        score += p.get("3連対率", 0)

        # 脚質
        score += p.get("B", 0) * 2.5
        score += p.get("逃", 0) * 2
        score += p.get("捲", 0) * 2.2
        score += p.get("差", 0) * 1.8
        score += p.get("マ", 0)

        # 若手機動型補正
        if p.get("年齢", 50) <= 35:

            score += 5

        # 高齢追込減点
        if p.get("年齢", 0) >= 48 and p.get("B", 0) == 0:

            score -= 4

        # バンク補正
        if place in BANK_BONUS:

            score += BANK_BONUS[place]

        p["AIスコア"] = round(score, 1)

    return sorted(
        players,
        key=lambda x: x["AIスコア"],
        reverse=True
    )

# =====================================
# 買い目生成
# =====================================

def generate_bets(players_sorted):

    bets = []

    if len(players_sorted) >= 4:

        a = players_sorted[0]["車番"]
        b = players_sorted[1]["車番"]
        c = players_sorted[2]["車番"]
        d = players_sorted[3]["車番"]

        bets = {

            "本線": [
                f"{a}-{b}-{c}",
                f"{a}-{c}-{b}",
                f"{b}-{a}-{c}",
                f"{a}-{b}-{d}"
            ],

            "中穴": [
                f"{c}-{a}-{b}",
                f"{b}-{c}-{a}"
            ],

            "大穴": [
                f"{d}-{a}-{b}",
                f"{a}-{d}-{b}"
            ]
        }

    return bets

# =====================================
# AI期待値
# =====================================

def calculate_ev(players_sorted):

    if len(players_sorted) < 3:

        return 0

    ev = round(

        (
            players_sorted[0]["AIスコア"]
            + players_sorted[1]["AIスコア"]
            + players_sorted[2]["AIスコア"]

        ) * 3,

        1
    )

    return ev

# =====================================
# 入力欄
# =====================================

race_data = st.text_area(

    "競輪データ貼付",
    height=500,
    key="race_data"
)

# =====================================
# クリア
# =====================================

if st.button("クリア"):

    st.session_state["race_data"] = ""

    st.rerun()

# =====================================
# AI解析開始
# =====================================

if st.button("AI予想開始"):

    if race_data.strip() == "":

        st.warning("競輪データを入力してください")

    else:

        with st.spinner("AI解析中..."):

            # =====================================
            # 開催場
            # =====================================

            place = extract_place(race_data)

            st.header("開催場")

            st.success(place)

            # =====================================
            # ライン解析
            # =====================================

            line_result = extract_lines(race_data)

            if line_result:

                st.header("ライン解析")

                for idx, line in enumerate(line_result, start=1):

                    st.write(
                        f"ライン{idx} : {'-'.join(line)}"
                    )

            else:

                st.error("ライン解析失敗")

            # =====================================
            # 選手解析
            # =====================================

            players = extract_players(race_data)

            if len(players) == 0:

                st.error("選手解析失敗")

            else:

                # =====================================
                # AIスコア計算
                # =====================================

                players_sorted = calculate_scores(
                    players,
                    place
                )

                # =====================================
                # AIスコアランキング
                # =====================================

                st.header("AIスコアランキング")

                for idx, p in enumerate(players_sorted[:4]):

                    col1, col2 = st.columns([1, 5])

                    with col1:

                        st.metric(

                            f"{idx+1}位 {p['車番']}番",

                            p["AIスコア"]
                        )

                    with col2:

                        st.write(p["選手名"])

                # =====================================
                # DataFrame
                # =====================================

                st.header("解析確認")

                df = pd.DataFrame(players_sorted)

                show_cols = [

                    "車番",
                    "選手名",
                    "年齢",
                    "AIスコア",
                    "勝率",
                    "連対率",
                    "3連対率",
                    "S",
                    "B",
                    "逃",
                    "捲",
                    "差",
                    "マ"
                ]

                exist_cols = [

                    c for c in show_cols
                    if c in df.columns
                ]

                st.dataframe(

                    df[exist_cols],

                    use_container_width=True
                )

                # =====================================
                # 印
                # =====================================

                st.header("AI最終印")

                marks = ["◎", "○", "▲", "☆"]

                for i, p in enumerate(players_sorted[:4]):

                    st.write(

                        f"{marks[i]} "
                        f"{p['車番']}番 "
                        f"{p['選手名']} "
                        f"AI:{p['AIスコア']}"
                    )

                # =====================================
                # 買い目
                # =====================================

                bets = generate_bets(players_sorted)

                st.header("推奨買い目")

                if bets:

                    st.subheader("本線")

                    for b in bets["本線"]:

                        st.success(b)

                    st.subheader("中穴")

                    for b in bets["中穴"]:

                        st.warning(b)

                    st.subheader("大穴")

                    for b in bets["大穴"]:

                        st.error(b)

                # =====================================
                # AI期待値
                # =====================================

                ev = calculate_ev(players_sorted)

                st.header("AI期待値")

                st.metric(
                    "期待値",
                    f"{ev}%"
                )

                # =====================================
                # 投資判断
                # =====================================

                st.header("投資判断")

                if ev >= 900:

                    st.success("SS級超期待値レース")

                elif ev >= 700:

                    st.success("強く買い")

                elif ev >= 500:

                    st.warning("買い")

                else:

                    st.error("見送り推奨")

                # =====================================
                # 展開予想
                # =====================================

                st.header("展開予想")

                if line_result:

                    st.write(
                        "主導権予想 : "
                        + "-".join(line_result[0])
                    )

                    st.write(
                        "捲り警戒 : "
                        + "-".join(line_result[1])
                    )

                    if len(line_result) >= 3:

                        st.write(
                            "穴ライン : "
                            + "-".join(line_result[2])
                        )

                # =====================================
                # 波乱度
                # =====================================

                st.header("波乱度")

                if ev >= 900:

                    st.success("C 本命寄り")

                elif ev >= 700:

                    st.warning("B 標準")

                else:

                    st.error("A 荒れ警戒")