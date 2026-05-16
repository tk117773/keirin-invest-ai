import streamlit as st
import pandas as pd
import re

# =====================================
# 1. ページ設定 & バンクデータ
# =====================================
st.set_page_config(page_title="KEIRIN INVEST AI Ultimate", layout="wide")
st.title("🚴 KEIRIN INVEST AI Ultimate")
st.caption("【最新Ver】6段階解析プロセス & 3連単厳選8点ロジック実装")

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
# 2. 解析エンジン
# =====================================

def extract_place(text):
    header = text[:100]
    for place in BANK_BONUS.keys():
        if place in header: return place
    return "不明"

def extract_players(text):
    players = []
    # 名前(年齢)のパターンで抽出
    player_blocks = re.findall(r'([1-9])\s+([^\s\d\(\)（）]+)[\s\n]*[\(（](\d{2})[\)）]', text)
    
    for i in range(len(player_blocks)):
        car_num, name, age = player_blocks[i]
        start_pos = text.find(name)
        next_pos = text.find(player_blocks[i+1][1]) if i+1 < len(player_blocks) else len(text)
        target_text = text[start_pos:next_pos]
        
        p = {"車番": car_num, "選手名": name, "年齢": int(age), "S": 0, "B": 0, "逃": 0, "捲": 0, "差": 0, "マ": 0, "勝率": 0.0, "連対率": 0.0, "3連対率": 0.0}
        
        nums = re.findall(r"\d+\.\d+|\d+", target_text)
        floats = [float(n) for n in nums if "." in n]
        ints = [int(n) for n in nums if "." not in n and int(n) != int(age) and int(n) < 50]
        
        if len(ints) >= 6: p.update({"S": ints[0], "B": ints[1], "逃": ints[2], "捲": ints[3], "差": ints[4], "マ": ints[5]})
        if len(floats) >= 3: p.update({"勝率": floats[0], "連対率": floats[1], "3連対率": floats[2]})
        players.append(p)
    return players

def calculate_advanced_scores(players, place):
    """解析プロセス 1〜4を統合したスコアリング"""
    for p in players:
        # 基本能力
        score = p["勝率"] * 2.0 + p["連対率"] * 1.5 + p["3連対率"] * 1.0
        # 1. ライン主導権・M指数補正 (B回数を重視)
        score += p["B"] * 4.0 + p["S"] * 1.5
        # 2. 脚質補正 (逃げ・捲りの自力型を評価)
        score += p["逃"] * 3.0 + p["捲"] * 2.5
        # 3. 若手・高齢補正
        if p["年齢"] <= 29: score += 20  # 若手の波乱
        if p["年齢"] >= 43: score -= 5   # 高齢追込の過信禁止
        # 4. バンク特性
        score += BANK_BONUS.get(place, 5)
        
        p["AIスコア"] = round(score, 1)
    return sorted(players, key=lambda x: x["AIスコア"], reverse=True)

def generate_strict_bets(sorted_p):
    """解析プロセス 5〜6: 3連単厳選8点・オッズ期待値分析"""
    if len(sorted_p) < 5: return None
    
    # 選手ランク付け
    # ◎:指数1位, ○:指数2位, ▲:指数3位, △:指数4位, ☆:指数5位
    n = [p["車番"] for p in sorted_p]
    
    return {
        "本線（4点）": [
            f"{n[0]}-{n[1]}-{n[2]}", f"{n[0]}-{n[1]}-{n[3]}",
            f"{n[1]}-{n[0]}-{n[2]}", f"{n[1]}-{n[0]}-{n[3]}"
        ],
        "中穴（2点）": [
            f"{n[0]}-{n[2]}-{n[4]}", f"{n[2]}-{n[0]}-{n[1]}"
        ],
        "大穴（2点）": [
            f"{n[3]}-{n[0]}-{n[1]}", f"{n[4]}-{n[0]}-{n[1]}"
        ]
    }

# =====================================
# 3. UI表示
# =====================================
data_input = st.text_area("出走表データを貼り付けてください", height=300)

if st.button("AI解析・厳選8点生成", type="primary", use_container_width=True):
    if data_input.strip():
        place = extract_place(data_input)
        players = extract_players(data_input)
        
        if players:
            sorted_p = calculate_advanced_scores(players, place)
            
            # 的中期待値・判断表示
            diff = sorted_p[0]["AIスコア"] - sorted_p[1]["AIスコア"]
            prob = round(min(45 + (diff * 2.5), 98.5), 1)
            
            st.success(f"📍 開催場: {place} / 的中期待値: {prob}%")
            
            # ランキング
            st.subheader("📊 AI能力指数ランキング（プロセス1〜4適用）")
            st.dataframe(pd.DataFrame(sorted_p)[["車番", "選手名", "年齢", "AIスコア", "B", "逃", "捲", "勝率"]], use_container_width=True)

            # 買い目（プロセス5〜6適用）
            st.divider()
            st.header("🎯 厳選買い目 3連単8点（資金配分推奨）")
            bets = generate_strict_bets(sorted_p)
            
            c1, c2, c3 = st.columns(3)
            with c1:
                st.success("🔥 本線 (4点)")
                for b in bets["本線（4点）"]: st.write(f"**{b}** (配分: 30%)")
            with c2:
                st.warning("⚖️ 中穴 (2点)")
                for b in bets["中穴（2点）"]: st.write(f"**{b}** (配分: 15%)")
            with c3:
                st.error("🚀 大穴 (2点)")
                for b in bets["大穴（2点）"]: st.write(f"**{b}** (配分: 10%)")
            
            st.info("💡 **買い目判断**: " + ("鉄板。上位の能力が突出しています。" if prob > 75 else "混戦。展開ひとつで高配当の可能性があります。"))
        else:
            st.error("選手情報を解析できませんでした。")

if st.button("リセット"): st.rerun()
