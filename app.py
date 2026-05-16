import streamlit as st
import pandas as pd
import re

# =====================================
# 1. ページ設定 & データ定義
# =====================================
st.set_page_config(page_title="KEIRIN INVEST AI Ultimate", layout="wide")
st.title("🚴 KEIRIN INVEST AI Ultimate")
st.caption("【完全統合版】ライン結束・的中率・回収期待値・厳選8点ロジック")

# 地区区分
REGION_MAP = {
    "北日本": ["青森", "岩手", "秋田", "山形", "宮城", "福島"],
    "関東": ["茨城", "栃木", "群馬", "埼玉", "東京", "千葉", "神奈川", "山梨", "新潟"],
    "南関東": ["千葉", "神奈川", "静岡"],
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
# 2. 解析エンジン（ここに関数をまとめました）
# =====================================

def get_region(pref):
    for region, prefs in REGION_MAP.items():
        if pref in prefs: return region
    return "不明"

def extract_place(text):
    header = text[:150]
    for place in BANK_BONUS.keys():
        if place in header: return place
    return "不明"

def extract_players_ultra(text):
    players = []
    # 車番・名前・年齢・府県を抽出
    matches = list(re.finditer(r'([1-9])\s+([^\s\d\(\)（）]+)[\s\n]*[\(（](\d{2})[\)）][\s\n]*([^\s/]+)', text))
    
    for i, match in enumerate(matches):
        car_num, name, age, pref = match.groups()
        start_idx = match.start()
        end_idx = matches[i+1].start() if i+1 < len(matches) else len(text)
        block = text[start_idx:end_idx]
        
        all_nums = re.findall(r"\d+\.\d+|\d+", block)
        floats = [float(n) for n in all_nums if "." in n]
        ints = [int(n) for n in all_nums if "." not in n and int(n) != int(age) and int(n) < 60]

        # S B 逃 捲 差 マ の抽出
        s, b, nige, maki, sashi, ma = 0, 0, 0, 0, 0, 0
        for j in range(len(ints) - 5):
            window = ints[j:j+6]
            if 0 < sum(window) < 120:
                s, b, nige, maki, sashi, ma = window
                break
        
        # 勝率等の抽出
        win_rate, ren_rate, san_rate = 0.0, 0.0, 0.0
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
    # 1. 個人の基本スコア
    for p in players:
        score = (p["勝率"] * 1.5 + p["B"] * 5.5 + p["逃"] * 4.0 + p["捲"] * 3.5 + p["差"] * 1.0)
        score += BANK_BONUS.get(place, 5)
        if p["年齢"] <= 30: score += 20
        p["AI個人スコア"] = round(score, 1)

    # 2. ライン情報の解析
    line_groups = []
    current_line = []
    for l in line_raw.split():
        if l.isdigit(): current_line.append(l)
        else:
            if current_line: line_groups.append(current_line)
            current_line = []
    if current_line: line_groups.append(current_line)

    # 3. 結束度加点
    for group in line_groups:
        if len(group) < 2: continue
        leader = next((p for p in players if p["車番"] == group[0]), None)
        if not leader: continue
        for i in range(1, len(group)):
            f = next((p for p in players if p["車番"] == group[i]), None)
            if not f: continue
            if leader["府県"] == f["府県"]: f["AI個人スコア"] += 15.0
            elif leader["地区"] == f["地区"]: f["AI個人スコア"] += 8.0
            else: f["AI個人スコア"] += 2.0

    return sorted(players, key=lambda x: x["AI個人スコア"], reverse=True)

# =====================================
# 3. メインレイアウト
# =====================================
col_in1, col_in2 = st.columns([3, 1])
with col_in1:
    data_input = st.text_area("出走表データを貼り付けてください", height=300)
with col_in2:
    line_input = st.text_area("並び予想 (数字を改行/空白入力)", height=300, placeholder="7\n1\n9\n4\n2...")

if st.button("AI解析・厳選8点生成開始", type="primary", use_container_width=True):
    if not data_input.strip():
        st.error("データを入力してください。")
    else:
        # ここで呼び出し順序を確定
        current_place = extract_place(data_input)
        player_list = extract_players_ultra(data_input)
        
        if player_list:
            sorted_p = calculate_advanced_scores(player_list, current_place, line_input)
            
            # 的中率・回収計算
            top_p = sorted_p[0]
            diff = top_p["AI個人スコア"] - sorted_p[1]["AI個人スコア"]
            accuracy = round(min(30 + (diff * 2.5) + (top_p["B"] * 2), 98.2), 1)
            est_return = int(1000 * (accuracy / 22) * (1 + (top_p["勝率"]/100)))

            # 結果表示
            st.success(f"📍 開催場: {current_place} / 的中期待値: {accuracy}%")
            
            m1, m2, m3 = st.columns(3)
            m1.metric("予想的中率", f"{accuracy}%")
            m2.metric("想定回収額 (800円時)", f"¥{est_return:,}")
            m3.metric("主導権期待値 (B)", f"{top_p['B']}")

            # ランキング
            st.subheader("📊 AIライン結束・能力解析表")
            df = pd.DataFrame(sorted_p)
            st.dataframe(df[["車番", "選手名", "府県", "AI個人スコア", "B", "逃", "捲", "差", "勝率"]], use_container_width=True)

            # 買い目生成 (8点厳選)
            st.divider()
            st.header("🎯 3連単 厳選8点勝負")
            n = [p["車番"] for p in sorted_p]
            if len(n) >= 5:
                b_hon = [f"{n[0]}-{n[1]}-{n[2]}", f"{n[0]}-{n[1]}-{n[3]}", f"{n[1]}-{n[0]}-{n[2]}", f"{n[1]}-{n[0]}-{n[3]}"]
                b_chu = [f"{n[0]}-{n[2]}-{n[1]}", f"{n[0]}-{n[1]}-{n[4]}"]
                b_ana = [f"{n[2]}-{n[0]}-{n[1]}", f"{n[3]}-{n[0]}-{n[1]}"]
                
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.success("🔥 本線 (4点)")
                    for b in b_hon: st.write(f"**{b}**")
                with c2:
                    st.warning("⚖️ 中穴 (2点)")
                    for b in b_chu: st.write(f"**{b}**")
                with c3:
                    st.error("🚀 大穴 (2点)")
                    for b in b_ana: st.write(f"**{b}**")
            
            st.info(f"💡 **投資判断**: {'厚めに勝負可能' if accuracy > 70 else '手堅く分散投資'}。軸馬 {top_p['選手名']} の自力能力を高く評価しています。")
        else:
            st.error("選手情報を解析できませんでした。コピー範囲を確認してください。")

if st.button("リセット"): st.rerun()
