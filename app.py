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
    "函館": 4, "青森": 5, "いわき平": 6, "弥彦": 4, "前橋": 5, "取手": 5,
    "宇都宮": 5, "大宮": 4, "西武園": 4, "京王閣": 3, "立川": 4, "松戸": 4,
    "千葉": 5, "川崎": 3, "平塚": 3, "小田原": 2, "伊東": 5, "静岡": 5,
    "名古屋": 4, "岐阜": 5, "大垣": 4, "豊橋": 5, "富山": 4, "松阪": 5,
    "四日市": 6, "福井": 4, "奈良": 4, "向日町": 5, "和歌山": 5, "岸和田": 6,
    "玉野": 5, "広島": 4, "防府": 4, "高松": 4, "小松島": 5, "高知": 6,
    "松山": 5, "小倉": 6, "久留米": 5, "武雄": 4, "佐世保": 5, "別府": 6, "熊本": 5
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
        if "並び予想" in line or "ライン" in line:
            start = True
            continue
        if start:
            # 1-9の数字、またはハイフンで繋がれた数字を抽出
            found_nums = re.findall(r'[1-9]', line)
            if found_nums and len(nums) < 9:
                nums.extend(found_nums)

    # 重複を排除せず、見つかった順に処理
    if len(nums) >= 9:
        return (nums[0:3], nums[3:6], nums[6:9])
    elif len(nums) >= 7:
        return (nums[0:3], nums[3:5], nums[5:7])
    elif len(nums) >= 4:
        return (nums[0:2], nums[2:4], [])
    
    # テキスト全体からハイフン繋ぎの並びを直接探すフォールバック
    line_match = re.search(r'([1-9][-1-9]+)', text)
    if line_match:
        parts = line_match.group(1).split('-')
        return (parts, [], [])

    return (["1", "2", "3"], ["4", "5"], ["6", "7"])  # 解析不可時のデフォルト

# =====================================
# 選手解析（強化安定版）
# =====================================
def extract_players(text):
    players = []
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # 柔軟に「車番 選手名 (年齢)」のパターンを探す
        # 例: "1 1 吉田 拓矢 (28)" や "2 渡邉 一成 41歳" などに対応
        match = re.search(r'(?:^|\s)([1-9])\s+([^\s\(\d]+)\s*[\(（](\d+)[\)）]', line)
        
        # カッコがないパターン（例: 1 吉田拓矢 28）
        if not match:
            match = re.search(r'(?:^|\s)([1-9])\s+([^\s\d]{2,5})\s+(\d{2})(?:\s|$)', line)

        if match:
            car_num = match.group(1)
            player_name = match.group(2).strip()
            age = int(match.group(3))
            
            player = {
                "車番": car_num,
                "選手名": player_name,
                "年齢": age,
                "S": 0, "B": 0, "逃": 0, "捲": 0, "差": 0, "マ": 0,
                "勝率": 0.0, "連対率": 0.0, "3連対率": 0.0
            }
            
            # 選手名が見つかった行の「後ろ3行」の中から成績らしき数字の列を探す
            for search_idx in range(i + 1, min(i + 4, len(lines))):
                next_line = lines[search_idx]
                nums = re.findall(r"\d+\.\d+|\d+", next_line)
                
                # 成績データ（S, B, 逃, 捲, 差, マ, 各種確率）が含まれていそうな行
                if len(nums) >= 7:
                    try:
                        # 整数と浮動小数点を賢く分類
                        ints = [int(n) for n in nums if '.' not in n]
                        floats = [float(n) for n in nums if '.' in n]
                        
                        if len(ints) >= 6:
                            player["S"] = ints[0]
                            player["B"] = ints[1]
                            player["逃"] = ints[2]
                            player["捲"] = ints[3]
                            player["差"] = ints[4]
                            player["マ"] = ints[5]
                        
                        if len(floats) >= 3:
                            player["勝率"] = floats[0]
                            player["連対率"] = floats[1]
                            player["3連対率"] = floats[2]
                        elif len(ints) >= 9: # 全部整数で並んでいる場合
                            player["勝率"] = float(ints[-3])
                            player["連対率"] = float(ints[-2])
                            player["3連対率"] = float(ints[-1])
                        break
                    except:
                        pass
            
            players.append(player)
        i += 1
        
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

    return sorted(players, key=lambda x: x["AIスコア"], reverse=True)

# =====================================
# 推奨買い目生成（★ご要望に基づき、おすすめの購入車券を出力）
# =====================================
def generate_bets(players_sorted):
    bets = {"本線": [], "中穴": [], "大穴": []}
    if len(players_sorted) < 3:
        return bets

    a = players_sorted[0]["車番"]
    b = players_sorted[1]["車番"]
    c = players_sorted[2]["車番"]
    d = players_sorted[3]["車番"] if len(players_sorted) >= 4 else c
    e = players_sorted[4]["車番"] if len(players_sorted) >= 5 else c

    # 本線6点
    bets["本線"] = [f"{a}-{b}-{c}", f"{a}-{c}-{b}", f"{b}-{a}-{c}", f"{a}-{b}-{d}", f"{a}-{c}-{d}", f"{b}-{c}-{a}"]
    # 中穴6点
    bets["中穴"] = [f"{c}-{a}-{b}", f"{c}-{b}-{a}", f"{d}-{a}-{b}", f"{b}-{d}-{a}", f"{c}-{a}-{d}", f"{d}-{b}-{c}"]
    # 大穴3点
    bets["大穴"] = [f"{e}-{a}-{b}", f"{a}-{e}-{b}", f"{d}-{e}-{a}"]
    return bets

# =====================================
# AI期待値・的中確率
# =====================================
def calculate_ev(players_sorted):
    if len(players_sorted) < 3: return 0
    return round((players_sorted[0]["AIスコア"] + players_sorted[1]["AIスコア"] + players_sorted[2]["AIスコア"]) * 3, 1)

def calculate_hit_probability(players_sorted):
    if len(players_sorted) < 4: return 0
    top_scores = [p["AIスコア"] for p in players_sorted[:3]]
    avg_score = sum(top_scores) / 3
    
    if avg_score >= 180: hit_rate = 78
    elif avg_score >= 150: hit_rate = 68
    elif avg_score >= 120: hit_rate = 58
    elif avg_score >= 100: hit_rate = 48
    elif avg_score >= 80: hit_rate = 38
    else: hit_rate = 25

    top_b = players_sorted[0].get("B", 0)
    if top_b >= 10: hit_rate += 5
    elif top_b >= 5: hit_rate += 3

    high_age_count = sum(1 for p in players_sorted[:3] if p.get("年齢", 0) >= 48)
    hit_rate -= high_age_count * 2

    score_gap = players_sorted[0]["AIスコア"] - players_sorted[3]["AIスコア"]
    if score_gap <= 10: hit_rate -= 8
    elif score_gap <= 20: hit_rate -= 4

    return round(max(5, min(hit_rate, 95)), 1)

# =====================================
# 画面レイアウト
# =====================================
race_data = st.text_area("競輪データ貼付 (出走表や並び予想のテキストをそのままペーストしてください)", height=400, key="race_data")

if st.button("クリア"):
    st.session_state["race_data"] = ""
    st.rerun()

if st.button("AI予想開始"):
    if race_data.strip() == "":
        st.warning("競輪データを入力してください")
    else:
        with st.spinner("AI解析中..."):
            place = extract_place(race_data)
            st.header(f"開催場: {place}")

            # ライン解析
            line_result = extract_lines(race_data)
            st.subheader("📋 展開・ライン予想")
            if line_result[0]:
                st.info(f"想定ライン: {' / '.join(['-'.join(l) for l in line_result if l])}")

            # 選手解析
            players = extract_players(race_data)
            
            if len(players) == 0:
                st.error("選手データの抽出に失敗しました。入力テキストの形式を確認してください。")
                st.info("【推奨フォーマット例】\n1 選手名 (30)\n2 3 5 1 0 0 25.4 40.1 55.0")
            else:
                players_sorted = calculate_scores(players, place)

                # 解析確認データフレーム
                st.header("📊 解析結果一覧")
                df = pd.DataFrame(players_sorted)
                show_cols = ["車番", "選手名", "年齢", "AIスコア", "勝率", "連対率", "3連対率", "S", "B", "逃", "捲", "差", "マ"]
                exist_cols = [c for c in show_cols if c in df.columns]
                st.dataframe(df[exist_cols], use_container_width=True)

                # 推奨買い目
                st.header("🎯 推奨買い目（3連単 おすすめ購入馬券）")
                bets = generate_bets(players_sorted)
                
                col_b1, col_b2, col_b3 = st.columns(3)
                with col_b1:
                    st.success("【本線】(手堅く狙う6点)")
                    for b in bets["本線"]: st.write(f"・{b}")
                with col_b2:
                    st.warning("【中穴】(リターンを狙う6点)")
                    for b in bets["中穴"]: st.write(f"・{b}")
                with col_b3:
                    st.error("【大穴】(高配当狙いの3点)")
                    for b in bets["大穴"]: st.write(f"・{b}")

                # 各種指標
                st.header("📈 レース信頼度・投資判断")
                ev = calculate_ev(players_sorted)
                hit_rate = calculate_hit_probability(players_sorted)
                
                col_m1, col_m2, col_m3 = st.columns(3)
                with col_m1:
                    st.metric("AI期待値", f"{ev}%")
                with col_m2:
                    st.metric("的中確率", f"{hit_rate}%")
                with col_m3:
                    if ev >= 700: st.success("投資判断: 🔥強く買い")
                    elif ev >= 500: st.warning("投資判断: 👍買い")
                    else: st.error("投資判断: 🛑見送り推奨")
