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
# 解析ロジック
# =====================================

def extract_place(text):
    for place in BANK_BONUS.keys():
        if place in text:
            return place
    return "不明"

def extract_lines(text):
    # 「並び予想」の後の数字を抽出
    lines = text.split("\n")
    nums = []
    start = False
    for line in lines:
        if "並び予想" in line:
            start = True
            continue
        if start:
            val = line.strip()
            if re.match(r'^[1-9]$', val):
                nums.append(val)
            elif len(nums) > 0: # 数字が途切れたら終了
                break
    
    if len(nums) >= 9: return (nums[0:3], nums[3:6], nums[6:9])
    if len(nums) >= 7: return (nums[0:3], nums[3:5], nums[5:7])
    return (["1","2","3"], ["4","5","6"], ["7","8","9"]) # デフォルト

def extract_players(text):
    players_dict = {}
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    
    current_car_num = None
    
    for line in lines:
        # 1. 選手名と年齢の抽出 (例: 1 1 岩津裕介(44))
        name_match = re.search(r'([1-9])\s+([^\s\d\(\)]+)\((\d{2})\)', line)
        if name_match:
            current_car_num = name_match.group(1)
            players_dict[current_car_num] = {
                "車番": current_car_num,
                "選手名": name_match.group(2),
                "年齢": int(name_match.group(3)),
                "S": 0, "B": 0, "逃": 0, "捲": 0, "差": 0, "マ": 0,
                "勝率": 0.0, "連対率": 0.0, "3連対率": 0.0
            }
            continue

        if current_car_num:
            nums = re.findall(r"\d+\.\d+|\d+", line)
            
            # 決まり手行 (整数が6つ並ぶ箇所)
            if 6 <= len(nums) <= 8 and all("." not in n for n in nums):
                try:
                    players_dict[current_car_num].update({
                        "S": int(nums[0]), "B": int(nums[1]),
                        "逃": int(nums[2]), "捲": int(nums[3]),
                        "差": int(nums[4]), "マ": int(nums[5])
                    })
                except: pass
            
            # 確率行 (小数点が含まれる箇所)
            if any("." in n for n in nums):
                floats = [float(n) for n in nums if "." in n]
                if len(floats) >= 3:
                    players_dict[current_car_num].update({
                        "勝率": floats[0], "連対率": floats[1], "3連対率": floats[2]
                    })

    return list(players_dict.values())

def calculate_scores(players, place):
    for p in players:
        score = 0
        # 能力値スコア
        score += p["勝率"] * 1.5 + p["連対率"] * 1.2 + p["3連対率"] * 0.8
        # 脚質スコア
        score += p["B"] * 2.0 + p["逃"] * 2.0 + p["捲"] * 1.8 + p["差"] * 1.2 + p["マ"] * 0.8
        # 若手補正
        if p["年齢"] <= 30: score += 15
        elif p["年齢"] <= 35: score += 8
        # バンク補正
        score += BANK_BONUS.get(place, 0)
        p["AIスコア"] = round(score, 1)
    
    return sorted(players, key=lambda x: x["AIスコア"], reverse=True)

def generate_bets(sorted_p):
    if len(sorted_p) < 5: return None
    a, b, c, d, e = [p["車番"] for p in sorted_p[:5]]
    return {
        "本線": [f"{a}-{b}-{c}", f"{a}-{b}-{d}", f"{a}-{c}-{b}", f"{a}-{c}-{d}", f"{b}-{a}-{c}", f"{b}-{a}-{d}"],
        "中穴": [f"{c}-{a}-{b}", f"{c}-{b}-{a}", f"{d}-{a}-{b}", f"{d}-{b}-{a}", f"{a}-{d}-{e}", f"{b}-{d}-{e}"],
        "大穴": [f"{e}-{a}-{b}", f"{e}-{b}-{c}", f"{d}-{e}-{a}"]
    }

# =====================================
# UIレイアウト
# =====================================

race_data = st.text_area("競輪データ貼付 (出走表をコピー＆ペーストしてください)", height=300)

col_ctrl1, col_ctrl2 = st.columns(2)
with col_ctrl1:
    btn_start = st.button("AI予想開始", use_container_width=True, type="primary")
with col_ctrl2:
    if st.button("クリア", use_container_width=True):
        st.rerun()

if btn_start:
    if not race_data.strip():
        st.warning("データを入力してください")
    else:
        place = extract_place(race_data)
        line_result = extract_lines(race_data)
        players = extract_players(race_data)
        
        if not players:
            st.error("選手情報を読み取れませんでした。コピー範囲を確認してください。")
        else:
            sorted_p = calculate_scores(players, place)
            
            # 結果表示
            st.header(f"📍 開催場: {place}")
            
            # ライン
            st.subheader("📋 想定ライン（並び）")
            st.code(" / ".join(["-".join(l) for l in line_result if l]))

            # ランキング
            st.subheader("📊 AIスコアランキング")
            df = pd.DataFrame(sorted_p)
            cols = ["車番", "選手名", "年齢", "AIスコア", "勝率", "連対率", "S", "B", "逃", "捲", "差", "マ"]
            st.dataframe(df[cols], use_container_width=True)

            # 推奨買い目
            st.header("🎯 推奨買い目 (3連単)")
            bets = generate_bets(sorted_p)
            if bets:
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.success("【本線】")
                    for b in bets["本線"]: st.write(f"・{b}")
                with c2:
                    st.warning("【中穴】")
                    for b in bets["中穴"]: st.write(f"・{b}")
                with c3:
                    st.error("【大穴】")
                    for b in bets["大穴"]: st.write(f"・{b}")

            # 投資判断
            st.header("💡 AI解析結果")
            avg_top3 = sum(p["AIスコア"] for p in sorted_p[:3]) / 3
            st.metric("レース信頼度スコア", f"{round(avg_top3, 1)}")
            
            if avg_top3 > 120: st.success("投資判断: 🔥 S級勝負レース")
            elif avg_top3 > 80: st.warning("投資判断: ⚖️ A級標準レース")
            else: st.error("投資判断: 🧊 荒れ予想・見送り推奨")
