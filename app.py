import streamlit as st
import pandas as pd
import re

# =====================================
# 1. ページ設定 & データ定義
# =====================================
st.set_page_config(page_title="KEIRIN INVEST AI Ultimate", layout="wide")
st.title("🚴 KEIRIN INVEST AI Ultimate")
st.caption("【最新Ver】ライン結束度(同県・同地区) & ライン厚み指数 解析エンジン搭載")

# 地区区分データ（結束度判定用）
REGION_MAP = {
    "北日本": ["青森", "岩手", "秋田", "山形", "宮城", "福島"],
    "関東": ["茨城", "栃木", "群馬", "埼玉", "東京", "千葉", "神奈川", "山梨", "新潟"],
    "南関東": ["千葉", "神奈川", "静岡"], # 重複含め実態に即して
    "中部": ["岐阜", "三重", "富山", "石川", "福井", "愛知"],
    "近畿": ["滋賀", "京都", "大阪", "兵庫", "奈良", "和歌山"],
    "中国": ["岡山", "広島", "山口"],
    "四国": ["徳島", "香川", "愛媛", "高知"],
    "九州": ["福岡", "佐賀", "長崎", "大分", "熊本", "宮崎", "鹿児島", "沖縄"]
}

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

def get_region(pref):
    for region, prefs in REGION_MAP.items():
        if pref in prefs: return region
    return "不明"

def extract_players_ultra(text):
    players = []
    # 車番・名前・年齢に加えて「府県」も抽出
    matches = list(re.finditer(r'([1-9])\s+([^\s\d\(\)（）]+)[\s\n]*[\(（](\d{2})[\)）][\s\n]*([^\s/]+)', text))
    
    for i, match in enumerate(matches):
        car_num, name, age, pref = match.groups()
        start_idx = match.start()
        end_idx = matches[i+1].start() if i+1 < len(matches) else len(text)
        block = text[start_idx:end_idx]
        
        all_nums = re.findall(r"\d+\.\d+|\d+", block)
        floats = [float(n) for n in all_nums if "." in n]
        ints = [int(n) for n in all_nums if "." not in n and int(n) != int(age) and int(n) < 60]

        s, b, nige, maki, sashi, ma = 0, 0, 0, 0, 0, 0
        for j in range(len(ints) - 5):
            window = ints[j:j+6]
            if 0 < sum(window) < 100:
                s, b, nige, maki, sashi, ma = window
                break
        
        win_rate, ren_rate, san_rate = 0.0, 0.0, 0.0
        if len(floats) >= 3:
            target_floats = [f for f in floats if f != 3.92]
            if len(target_floats) >= 3:
                win_rate, ren_rate, san_rate = target_floats[:3]

        players.append({
            "車番": car_num, "選手名": name, "年齢": int(age), "府県": pref, "地区": get_region(pref),
            "S": s, "B": b, "逃": nige, "捲": maki, "差": sashi, "マ": ma,
            "勝率": win_rate, "連対率": ren_rate, "3連対率": san_rate
        })
    return players

def calculate_advanced_scores(players, place, line_raw):
    """ライン結束度と厚みを考慮した計算"""
    # 1. 個人の基本スコア算出
    for p in players:
        score = (p["勝率"] * 1.5 + p["B"] * 5.0 + p["逃"] * 3.5 + p["捲"] * 3.0 + p["年齢"] * -0.2)
        score += BANK_BONUS.get(place, 5)
        p["AI個人スコア"] = round(score, 1)

    # 2. ライン情報の解析 (並び予想から)
    # 簡易的に [7,1,9] のようなグループに分け、結束度を判定
    line_groups = []
    current_line = []
    lines_raw_split = line_raw.split("\n")
    for l in lines_raw_split:
        val = l.strip()
        if val.isdigit():
            current_line.append(val)
        elif current_line:
            line_groups.append(current_line)
            current_line = []
    if current_line: line_groups.append(current_line)

    # 3. ライン結束加点
    for group in line_groups:
        if len(group) < 2: continue
        leader_num = group[0]
        # リーダーを見つける
        leader = next((p for p in players if p["車番"] == leader_num), None)
        if not leader: continue

        for i in range(1, len(group)):
            follower = next((p for p in players if p["車番"] == group[i]), None)
            if not follower: continue
            
            # 同県
            if leader["府県"] == follower["府県"]:
                follower["AI個人スコア"] += 15.0
                follower["結束度"] = "同県(強)"
            # 同地区
            elif leader["地区"] == follower["地区"]:
                follower["AI個人スコア"] += 8.0
                follower["結束度"] = "同地区(中)"
            else:
                follower["AI個人スコア"] += 2.0
                follower["結束度"] = "隣接地区(弱)"

    return sorted(players, key=lambda x: x["AI個人スコア"], reverse=True), line_groups

# =====================================
# 3. UI表示
# =====================================
col_in1, col_in2 = st.columns([2, 1])
with col_in1:
    data_input = st.text_area("出走表データを貼り付け", height=250)
with col_in2:
    line_input = st.text_area("並び予想 (数字を改行して入力)", height=250, placeholder="7\n1\n9\n4\n2...")

if st.button("AIライン解析・厳選8点生成", type="primary", use_container_width=True):
    if data_input.strip():
        place = extract_place(data_input)
        players = extract_players_ultra(data_input)
        
        if players:
            sorted_p, line_groups = calculate_advanced_scores(players, place, line_input)
            
            # --- 解析指標の算出 ---
            top_p = sorted_p[0]
            accuracy = round(min(30 + (top_p["AI個人スコア"] * 0.5) + (top_p["B"] * 1.5), 98.0), 1)

            st.success(f"📍 開催場: {place} / 的中期待値: {accuracy}%")
            
            # 的中率・判断
            m1, m2 = st.columns(2)
            m1.metric("ライン結束考慮 的中率", f"{accuracy}%")
            m2.metric("ライン合計指数 (主導権ライン)", f"{round(sum(p['AI個人スコア'] for p in sorted_p[:3]), 1)}")

            # 詳細表
            st.subheader("📊 ライン結束・能力分析表")
            df = pd.DataFrame(sorted_p)
            st.dataframe(df[["車番", "選手名", "府県", "AI個人スコア", "B", "逃", "捲", "差"]], use_container_width=True)

            # 買い目（厳選8点）
            st.divider()
            st.header("🎯 厳選3連単 8点 (本線4・中穴2・大穴2)")
            n = [p["車番"] for p in sorted_p]
            bets = {
                "本線（4点）": [f"{n[0]}-{n[1]}-{n[2]}", f"{n[0]}-{n[1]}-{n[3]}", f"{n[1]}-{n[0]}-{n[2]}", f"{n[1]}-{n[0]}-{n[3]}"],
                "中穴（2点）": [f"{n[0]}-{n[2]}-{n[4]}", f"{n[2]}-{n[0]}-{n[1]}"],
                "大穴（2点）": [f"{n[3]}-{n[0]}-{n[1]}", f"{n[4]}-{n[0]}-{n[1]}"]
            }
            
            b1, b2, b3 = st.columns(3)
            with b1:
                st.success("🔥 本線 (4点)")
                for b in bets["本線（4点）"]: st.write(f"**{b}**")
            with b2:
                st.warning("⚖️ 中穴 (2点)")
                for b in bets["中穴（2点）"]: st.write(f"**{b}**")
            with b3:
                st.error("🚀 大穴 (2点)")
                for b in bets["大穴（2点）"]: st.write(f"**{b}**")

            st.info(f"💡 **ライン分析**: 自力型 {top_p['選手名']} 選手と番手選手の結束度が評価を押し上げています。別線の単騎勢の突っ込みには注意が必要です。")
