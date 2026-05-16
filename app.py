import streamlit as st
import pandas as pd
import re

# =====================================
# 1. ページ設定
# =====================================
st.set_page_config(
    page_title="KEIRIN INVEST AI Ultimate",
    layout="wide"
)

st.title("🚴 KEIRIN INVEST AI Ultimate")
st.caption("出走表データを貼り付けるだけで、AIがスコア算出と買い目生成を行います。")

# =====================================
# 2. 全国競輪場補正データ
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
# 3. 解析・計算ロジック
# =====================================

def extract_place(text):
    """テキストから開催場所を抽出"""
    for place in BANK_BONUS.keys():
        if place in text:
            return place
    return "不明"

def extract_lines(text):
    """並び予想からラインを抽出"""
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
            elif len(nums) > 0:
                break
    
    # 車券構成に応じた分割
    if len(nums) >= 9: return (nums[0:3], nums[3:6], nums[6:9])
    if len(nums) >= 7: return (nums[0:3], nums[3:5], nums[5:7])
    return (nums, [], [])

def extract_players(text):
    """複数行にわたる出走表から選手データを抽出"""
    players_dict = {}
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    
    current_car_num = None
    
    for line in lines:
        # 選手名・車番・年齢の行を特定 (例: "1 1 岩津裕介(44)")
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

        # 選手が特定されている間、続く行から数値を抽出
        if current_car_num:
            nums = re.findall(r"\d+\.\d+|\d+", line)
            if not nums: continue

            # 決まり手行 (整数が並んでいる。対戦成績のハイフン等が含まれないこと)
            if len(nums) >= 6 and all("." not in n for n in nums) and "-" not in line:
                players_dict[current_car_num].update({
                    "S": int(nums[0]), "B": int(nums[1]),
                    "逃": int(nums[2]), "捲": int(nums[3]),
                    "差": int(nums[4]), "マ": int(nums[5])
                })
            
            # 成績行 (勝率などの小数点が含まれる)
            elif any("." in n for n in nums):
                floats = [float(n) for n in nums if "." in n]
                if len(floats) >= 3:
                    players_dict[current_car_num].update({
                        "勝率": floats[0], "連対率": floats[1], "3連対率": floats[2]
                    })
                    # 一人分のデータが揃うポイント（勝率）でリセット
                    current_car_num = None 

    return list(players_dict.values())

def calculate_scores(players, place):
    """AIスコアリング"""
    for p in players:
        score = 0
        # 成績スコア
        score += p["勝率"] * 2.2 + p["連対率"] * 1.5 + p["3連対率"] * 1.0
        # 積極性・脚質スコア
        score += p["B"] * 2.8 + p["逃"] * 2.5 + p["捲"] * 2.2 + p["差"] * 1.2
        # 年齢補正（若手の機動力重視）
        if p["年齢"] <= 30: score += 20
        elif p["年齢"] <= 35: score += 10
        # バンク特製補正
        score += BANK_BONUS.get(place, 0)
        
        p["AIスコア"] = round(score, 1)
    
    return sorted(players, key=lambda x: x["AIスコア"], reverse=True)

def generate_bets(sorted_p):
    """推奨買い目の生成"""
    if len(sorted_p) < 4: return None
    a = sorted_p[0]["車番"]
    b = sorted_p[1]["車番"]
    c = sorted_p[2]["車番"]
    d = sorted_p[3]["車番"]
    
    return {
        "本線": [f"{a}-{b}-{c}", f"{a}-{b}-{d}", f"{a}-{c}-{b}"],
        "中穴": [f"{b}-{a}-{c}", f"{c}-{a}-{b}", f"{a}-{d}-{b}"],
        "大穴": [f"{c}-{b}-{a}", f"{d}-{a}-{b}", f"{b}-{c}-{d}"]
    }

# =====================================
# 4. メイン画面レイアウト
# =====================================

# データ入力
race_data = st.text_area("ここに競輪データを貼り付けてください", height=400)

col1, col2 = st.columns(2)
with col1:
    execute = st.button("AI予想を開始する", type="primary", use_container_width=True)
with col2:
    if st.button("リセット", use_container_width=True):
        st.rerun()

if execute:
    if not race_data.strip():
        st.warning("解析するデータを入力してください。")
    else:
        with st.spinner("AI解析および展開予想を算出中..."):
            place = extract_place(race_data)
            line_info = extract_lines(race_data)
            player_list = extract_players(race_data)
            
            if not player_list:
                st.error("選手情報を読み取れませんでした。出走表の『枠番 車番 選手名(年齢)』が含まれるようにコピーしてください。")
            else:
                sorted_players = calculate_scores(player_list, place)
                
                # 結果表示
                st.success(f"解析完了: {place}競輪場")
                
                # 1. スコアランキング（表）
                st.subheader("📊 AI解析スコアランキング")
                df = pd.DataFrame(sorted_players)
                df_display = df[["車番", "選手名", "年齢", "AIスコア", "勝率", "連対率", "S", "B", "逃", "捲", "差", "マ"]]
                st.dataframe(df_display, use_container_width=True)
                
                # 2. 最終印と推奨買い目
                st.divider()
                res_col1, res_col2 = st.columns(2)
                
                with res_col1:
                    st.subheader("📝 AI最終印")
                    marks = ["◎ 本命", "○ 対抗", "▲ 単穴", "☆ 特注", "△ 連下"]
                    for i, p in enumerate(sorted_players[:5]):
                        st.write(f"**{marks[i]}**: {p['車番']}番 {p['選手名']} ({p['AIスコア']}点)")
                
                with res_col2:
                    st.subheader("🎯 推奨買い目 (3連単)")
                    bets = generate_bets(sorted_players)
                    if bets:
                        st.write("**本線（期待値高）**")
                        st.info(" , ".join(bets["本線"]))
                        st.write("**狙い（中穴）**")
                        st.warning(" , ".join(bets["中穴"]))
                        st.write("**穴（波乱）**")
                        st.error(" , ".join(bets["大穴"]))

                # 3. 展開予想
                if any(line_info):
                    st.subheader("🚥 展開予想（並び）")
                    line_str = " / ".join(["-".join(l) for l in line_info if l])
                    st.code(line_str, language="text")

                # 4. 投資判断
                avg_score = sum(p["AIスコア"] for p in sorted_players[:3]) / 3
                st.subheader("💰 AI投資判断")
                if avg_score > 130:
                    st.success("【SS判断】圧倒的本命レース。厚めの投資を推奨。")
                elif avg_score > 90:
                    st.info("【A判断】実力伯仲。展開次第で絞って勝負。")
                else:
                    st.warning("【B判断】混戦模様。無理な投資は避け、広めに構えるか見送り推奨。")

# =====================================
# 5. フッター
# =====================================
st.caption("※本ツールはデータの解析結果を提供するものであり、的中を保証するものではありません。車券の購入は自己責任でお願いします。")
