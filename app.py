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
# 2. 解析ロジック
# =====================================

def extract_place_fixed(text):
    """開催場所をテキストの冒頭から優先的に抽出"""
    # 最初の100文字以内を重点的に探す
    header = text[:100]
    for place in BANK_BONUS.keys():
        if place in header:
            return place
    # 見つからない場合は全体から探す
    for place in BANK_BONUS.keys():
        if place in text:
            return place
    return "不明"

def extract_players_final(text):
    """テキスト全体から選手と成績を紐付け抽出"""
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
        
        # 決まり手抽出（年齢や大きな数字を除外して精度向上）
        relevant_ints = [n for n in ints if n != int(age) and n < 40]
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
                 p["B"] * 3.0 + p["逃"] * 2.5 + p["捲"] * 2.5 + p["差"] * 1.0)
        if p["年齢"] <= 30: score += 25
        elif p["年齢"] <= 35: score += 12
        score += BANK_BONUS.get(place, 0)
        p["AIスコア"] = round(score, 1)
    return sorted(players, key=lambda x: x["AIスコア"], reverse=True)

def generate_bets_fixed(sorted_p):
    """ご要望通りの点数（6-6-3）で生成"""
    if len(sorted_p) < 5: return None
    # 上位5名の車番を取得
    n = [p["車番"] for p in sorted_p]
    
    # 3連単フォーマット: 1着-2着-3着
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
# 3. UI
# =====================================
race_data = st.text_area("競輪データを貼り付けてください", height=300)

if st.button("AI予想開始", type="primary", use_container_width=True):
    if race_data.strip():
        place = extract_place_fixed(race_data)
        players = extract_players_final(race_data)
        
        if players:
            sorted_p = calculate_scores(players, place)
            st.success(f"📍 開催場: {place} 競輪場")
            
            # ランキング
            st.subheader("📊 AI能力指数ランキング")
            df = pd.DataFrame(sorted_p)
            st.dataframe(df[["車番", "選手名", "年齢", "AIスコア", "勝率", "連対率", "S", "B", "逃", "捲", "差", "マ"]], use_container_width=True)

            # 買い目表示
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
            st.error("選手データを抽出できませんでした。コピー範囲を確認してください。")

if st.button("リセット"): st.rerun()
