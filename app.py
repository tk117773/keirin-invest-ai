import streamlit as st
import pandas as pd
import re

# =====================================
# 1. ページ設定
# =====================================
st.set_page_config(page_title="KEIRIN INVEST AI Ultimate", layout="wide")
st.title("🚴 KEIRIN INVEST AI Ultimate")

# 競輪場補正データ
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
# 2. 解析・計算ロジック
# =====================================

def extract_place_fixed(text):
    header = text[:100]
    for place in BANK_BONUS.keys():
        if place in header: return place
    for place in BANK_BONUS.keys():
        if place in text: return place
    return "不明"

def extract_players_final(text):
    players = []
    # 選手名(年齢) のパターンで分割
    player_blocks = re.findall(r'([1-9])\s+([^\s\d\(\)（）]+)[\s\n]*[\(（](\d{2})[\)）]', text)
    
    for i in range(len(player_blocks)):
        car_num, name, age = player_blocks[i]
        start_pos = text.find(name)
        if i + 1 < len(player_blocks):
            next_name = player_blocks[i+1][1]
            end_pos = text.find(next_name)
            target_text = text[start_pos:end_pos]
        else:
            target_text = text[start_pos:]
        
        p_data = {
            "車番": car_num, "選手名": name, "年齢": int(age),
            "S": 0, "B": 0, "逃": 0, "捲": 0, "差": 0, "マ": 0,
            "勝率": 0.0, "連対率": 0.0, "3連対率": 0.0, "AIスコア": 0.0
        }
        
        nums = re.findall(r"\d+\.\d+|\d+", target_text)
        floats = [float(n) for n in nums if "." in n]
        ints = [int(n) for n in nums if "." not in n]
        
        relevant_ints = [n for n in ints if n != int(age) and n < 45]
        if len(relevant_ints) >= 6:
            p_data.update({"S": relevant_ints[0], "B": relevant_ints[1], "逃": relevant_ints[2], 
                           "捲": relevant_ints[3], "差": relevant_ints[4], "マ": relevant_ints[5]})
        if len(floats) >= 3:
            p_data.update({"勝率": floats[0], "連対率": floats[1], "3連対率": floats[2]})
        players.append(p_data)
    return players

def calculate_scores(players, place):
    for p in players:
        score = (p["勝率"] * 2.5 + p["連対率"] * 1.8 + p["3連対率"] * 1.2 +
                 p["B"] * 3.5 + p["逃"] * 3.0 + p["捲"] * 2.8 + p["差"] * 1.5)
        if p["年齢"] <= 30: score += 25
        elif p["年齢"] <= 35: score += 12
        score += BANK_BONUS.get(place, 0)
        p["AIスコア"] = round(score, 1)
    return sorted(players, key=lambda x: x["AIスコア"], reverse=True)

def generate_bets_fixed(sorted_p):
    if len(sorted_p) < 5: return None
    n = [p["車番"] for p in sorted_p]
    return {
        "本線（6点）": [
            f"{n[0]}-{n[1]}-{n[2]}", f"{n[0]}-{n[1]}-{n[3]}", 
            f"{n[0]}-{n[2]}-{n[1]}", f"{n[0]}-{n[2]}-{n[3]}",
            f"{n[1]}-{n[0]}-{n[2]}", f"{n[1]}-{n[0]}-{n[3]}"
        ],
        "中穴（6点）": [
            f"{n[0]}-{n[3]}-{n[1]}", f"{n[0]}-{n[3]}-{n[2]}",
            f"{n[2]}-{n[0]}-{n[1]}", f"{n[2]}-{n[1]}-{n[0]}",
            f"{n[0]}-{n[1]}-{n[4]}", f"{n[1]}-{n[2]}-{n[3]}"
        ],
        "大穴（3点）": [
            f"{n[3]}-{n[0]}-{n[1]}", f"{n[3]}-{n[1]}-{n[2]}", f"{n[4]}-{n[0]}-{n[1]}"
        ]
    }

# =====================================
# 3. UI部
# =====================================
race_data = st.text_area("競輪データを貼り付けてください", height=300)

if st.button("AI解析・的中率診断開始", type="primary", use_container_width=True):
    if race_data.strip():
        place = extract_place_fixed(race_data)
        players = extract_players_final(race_data)
        
        if players:
            sorted_p = calculate_scores(players, place)
            
            # --- 的中率と判断の計算 ---
            top_score = sorted_p[0]["AIスコア"]
            second_score = sorted_p[1]["AIスコア"]
            score_diff = top_score - second_score
            
            # 的中期待値の算出ロジック
            base_prob = 40 + (score_diff * 2) # スコア差があるほど的中率アップ
            if base_prob > 85: base_prob = 85 + (score_diff * 0.1)
            final_prob = round(min(base_prob, 98.2), 1) # 最大98.2%
            
            # 買い目判断
            if final_prob > 80:
                decision = "🔥 鉄板級：一点集中勝負"
                color = "success"
            elif final_prob > 60:
                decision = "⚖️ 標準：本線軸で手堅く"
                color = "info"
            elif final_prob > 40:
                decision = "⚠️ 混戦：広めに構えるべき"
                color = "warning"
            else:
                decision = "🎲 荒れ予想：見送りが賢明"
                color = "error"

            # 表示セクション
            st.success(f"📍 開催場: {place} 競輪場")
            
            # 的中率・判断のハイライト表示
            m1, m2 = st.columns(2)
            with m1:
                st.metric("AI予想的中期待値", f"{final_prob}%")
            with m2:
                st.subheader(f"買い目判断: {decision}")

            # ランキング
            st.subheader("📊 AI能力指数ランキング")
            df = pd.DataFrame(sorted_p)
            st.dataframe(df[["車番", "選手名", "年齢", "AIスコア", "勝率", "連対率", "S", "B", "逃", "捲", "差", "マ"]], use_container_width=True)

            # 買い目
            st.divider()
            st.header("🎯 AI推奨買い目 (3連単)")
            bets = generate_bets_fixed(sorted_p)
            if bets:
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.success("🔥 本線 (6点)")
                    for b in bets["本線（6点）"]: st.write(f"・{b}")
                with col2:
                    st.warning("⚖️ 中穴 (6点)")
                    for b in bets["中穴（6点）"]: st.write(f"・{b}")
                with col3:
                    st.error("🚀 大穴 (3点)")
                    for b in bets["大穴（3点）"]: st.write(f"・{b}")
        else:
            st.error("選手データを抽出できませんでした。")

if st.button("リセット"): st.rerun()
