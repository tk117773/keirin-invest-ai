import streamlit as st
import pandas as pd
import re

# =====================================
# 1. ページ設定
# =====================================
st.set_page_config(page_title="KEIRIN INVEST AI Ultimate", layout="wide")
st.title("🚴 KEIRIN INVEST AI Ultimate")

# 競輪場補正
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
# 2. 最強解析ロジック（正規表現を極限まで柔軟化）
# =====================================

def extract_players_final(text):
    """
    行単位ではなく、テキスト全体から正規表現で選手情報をぶっこ抜く
    """
    players = []
    
    # 1. まず「車番 選手名 (年齢)」のセットをすべて探す
    # 形式: "1 1 岩津裕介(44)" や "1 岩津裕介 (44)" など
    player_blocks = re.findall(r'([1-9])\s+([^\s\d\(\)（）]+)[\s\n]*[\(（](\d{2})[\)）]', text)
    
    # 2. テキストを「選手名」で分割して、それぞれの成績を個別に探す
    # これにより、名前と数字が離れていても確実に紐付く
    for i in range(len(player_blocks)):
        car_num, name, age = player_blocks[i]
        
        # この選手のデータが開始される位置を探す
        start_pos = text.find(name)
        # 次の選手までのテキストを切り出す（最後の選手なら最後まで）
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
        
        # 切り出したテキストから数値を抽出
        nums = re.findall(r"\d+\.\d+|\d+", target_text)
        
        # 小数点がある数字（確率）を抽出
        floats = [float(n) for n in nums if "." in n]
        # 小数点がない数字（決まり手や年齢、着外数など）を抽出
        ints = [int(n) for n in nums if "." not in n]
        
        # 決まり手（S, B, 逃, 捲, 差, マ）の抽出
        # 選手名の直後に現れる5〜7個程度の整数を狙う
        relevant_ints = [n for n in ints if n != int(age) and n < 50] # 年齢やギア比を除外
        if len(relevant_ints) >= 6:
            p_data["S"] = relevant_ints[0]
            p_data["B"] = relevant_ints[1]
            p_data["逃"] = relevant_ints[2]
            p_data["捲"] = relevant_ints[3]
            p_data["差"] = relevant_ints[4]
            p_data["マ"] = relevant_ints[5]
            
        # 確率（勝率, 連対率, 3連対率）
        if len(floats) >= 3:
            p_data["勝率"] = floats[0]
            p_data["連対率"] = floats[1]
            p_data["3連対率"] = floats[2]
            
        players.append(p_data)
        
    return players

def calculate_scores(players, place):
    for p in players:
        score = 0
        score += p["勝率"] * 2.5 + p["連対率"] * 1.8 + p["3連対率"] * 1.2
        score += p["B"] * 3.0 + p["逃"] * 2.5 + p["捲"] * 2.5 + p["差"] * 1.0
        if p["年齢"] <= 30: score += 25
        elif p["年齢"] <= 35: score += 12
        score += BANK_BONUS.get(place, 0)
        p["AIスコア"] = round(score, 1)
    return sorted(players, key=lambda x: x["AIスコア"], reverse=True)

# =====================================
# 3. Streamlit UI
# =====================================

# 入力エリア
race_data = st.text_area("競輪データを貼り付けてください（出走表まるごと）", height=400)

c1, c2 = st.columns(2)
with c1:
    btn = st.button("AI解析実行", type="primary", use_container_width=True)
with c2:
    if st.button("リセット", use_container_width=True):
        st.rerun()

if btn:
    if not race_data.strip():
        st.warning("データが空です。")
    else:
        place = "不明"
        for k in BANK_BONUS.keys():
            if k in race_data: place = k
            
        players = extract_players_final(race_data)
        
        if not players:
            st.error("選手が見つかりませんでした。貼り付けたデータに『選手名(年齢)』の形式があるか確認してください。")
        else:
            sorted_p = calculate_scores(players, place)
            
            st.success(f"解析完了！ 開催場: {place} / 抽出選手数: {len(sorted_p)}名")

            # 📊 メインランキング表
            st.subheader("📊 AIスコアランキング")
            df = pd.DataFrame(sorted_p)
            st.dataframe(df[["車番", "選手名", "年齢", "AIスコア", "勝率", "連対率", "S", "B", "逃", "捲", "差", "マ"]], use_container_width=True)

            # 🎯 最終印と買い目
            st.divider()
            col_a, col_b = st.columns(2)
            
            with col_a:
                st.subheader("📝 AI最終印")
                marks = ["◎", "○", "▲", "☆", "△"]
                for i, p in enumerate(sorted_p[:5]):
                    st.write(f"**{marks[i]}** {p['車番']}番 {p['選手名']} ({p['AIスコア']}点)")
            
            with col_b:
                st.subheader("🎯 3連単 推奨買い目")
                if len(sorted_p) >= 4:
                    a, b, c, d = [p["車番"] for p in sorted_p[:4]]
                    st.info(f"**本線**: {a}-{b}-{c}, {a}-{b}-{d}, {a}-{c}-{b}")
                    st.warning(f"**穴**: {b}-{a}-{c}, {c}-{a}-{b}, {d}-{a}-{b}")

st.caption("※本ツールはデータの解析結果を提供するものであり、車券の的中を保証するものではありません。購入は自己責任でお願いいたします。")
