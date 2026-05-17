import streamlit as st
import pandas as pd
import re

# --- ページ設定 ---
st.set_page_config(page_title="KEIRIN INVEST AI Ultimate", layout="wide")
st.title("🚴 KEIRIN INVEST AI Ultimate")
st.caption("【全項目反映・安定版】バラバラに貼り付けられたデータを選手名で自動統合")

def extract_combined_data_v2(text):
    # 選手ごとのデータを格納する辞書
    data_map = {}
    lines = text.split('\n')
    
    # 1. まず選手名と車番を全行からスキャンしてベースを作る
    for line in lines:
        # 「1 1 岡崎 和久」のような車番と選手名のペアを探す
        base_match = re.search(r'([1-9])\s+([1-9])\s+([^\s\d\/]+(?:\s+[^\s\d\/]+)?)', line)
        if base_match:
            car_num = base_match.group(2)
            name = base_match.group(3).strip().replace(" ", "").replace("　", "")
            if car_num not in data_map:
                data_map[car_num] = {
                    "車番": car_num, "選手名": name, "競走得点": 0.0, "脚": "-", 
                    "S": 0, "B": 0, "逃": 0, "捲": 0, "差": 0, "マ": 0,
                    "勝率": 0.0, "1着": 0, "2着": 0, "3着": 0, "AI指数": 0.0
                }

    # 2. 各行の内容を解析して、該当する選手のデータにマッピング
    for line in lines:
        line = line.strip()
        if not line: continue
        
        # 行内の全数値（小数含む）と、その行に含まれる「選手名」を特定
        line_nums = re.findall(r'\d+\.\d+|\d+', line)
        target_player = None
        for c, p_info in data_map.items():
            # 選手名がその行に含まれているか（スペースを除去して比較）
            clean_line = line.replace(" ", "").replace("　", "")
            if p_info["選手名"] in clean_line:
                target_player = c
                break
        
        if not target_player: continue
        p = data_map[target_player]

        # --- A. 競走得点・決まり手セクションの判別 ---
        if len(line_nums) >= 8 and any(f >= 35.0 for f in [float(x) for x in line_nums if "." in x]):
            floats = [float(x) for x in line_nums if "." in x]
            ints = [int(x) for x in line_nums if "." not in x]
            p["競走得点"] = next((f for f in floats if 35.0 <= f <= 150.0), p["競走得点"])
            # 決まり手は通常、競走得点の後ろに6つ並ぶ
            if len(ints) >= 6:
                p["S"], p["B"], p["逃"], p["捲"], p["差"], p["マ"] = ints[-6:]

        # --- B. 脚質セクション ---
        leg_match = re.search(r'(逃|両|追|自在|追込)', line)
        if leg_match:
            p["脚"] = leg_match.group(1)

        # --- C. 勝率セクション (小数点第一位が3つ以上) ---
        rates = [float(x) for x in line_nums if "." in x and 0.0 <= float(x) <= 100.0 and len(x.split('.')[-1]) == 1]
        if len(rates) >= 3:
            p["勝率"] = rates[0]

        # --- D. 戦績セクション (1-3着回数) ---
        # 「1着 2着 3着 着外」という見出しがある付近、あるいは整数が4つ並んでいる箇所
        if len(line_nums) >= 5:
            ints = [int(x) for x in line_nums if "." not in x]
            # 行の中に「車番」が含まれているので、それ以降の4つを取得
            if len(ints) >= 5:
                p["1着"], p["2着"], p["3着"] = ints[2], ints[3], ints[4]

    return list(data_map.values())

def calculate_ai_score(players, line_raw):
    for p in players:
        # 指数計算：全項目をバランスよく評価
        p["AI指数"] = round(
            p["競走得点"] * 1.3 + 
            p["勝率"] * 1.2 + 
            p["B"] * 4.0 + 
            p["逃"] * 3.0 + 
            p["捲"] * 2.5 + 
            p["1着"] * 2.0 + p["2着"] * 1.0, 1
        )
    
    line_nums = re.findall(r'[1-9]', line_raw)
    sorted_p = sorted(players, key=lambda x: x["AI指数"], reverse=True)
    top_p = sorted_p[0] if sorted_p else None
    m_line = []
    if top_p and top_p["車番"] in line_nums:
        idx = line_nums.index(top_p["車番"])
        m_line = line_nums[idx+1 : idx+3]
    return sorted_p, m_line

# --- UI ---
st.info("出走表の各セクション（得点、勝率、戦績など）をすべてコピーして貼り付けてください。")
c1, c2 = st.columns([3, 1])
with c1: data_in = st.text_area("競輪データを一括貼り付け", height=400)
with c2: line_in = st.text_area("並び (← 5 2...)", height=400)

if st.button("AIフル解析実行", type="primary", use_container_width=True):
    players = extract_combined_data_v2(data_in)
    if players:
        sorted_p, m_line = calculate_ai_score(players, line_in)
        top = sorted_p[0]
        n = [p["車番"] for p in sorted_p]
        
        st.success(f"【AI本命】 {top['車番']} {top['選手名']} (指数: {top['AI指数']})")
        
        # 買い目生成
        b1 = m_line[0] if len(m_line) > 0 else n[1]
        b2 = m_line[1] if len(m_line) > 1 else (n[2] if n[2]!=b1 else n[3])
        
        col1, col2 = st.columns(2)
        with col1:
            st.success("🔥 本線 (スジ・裏)")
            st.write(f"**{top['車番']}-{b1}-{b2}** / **{b1}-{top['車番']}-{b2}**")
        with col2:
            st.warning("⚖️ 抑え・別線")
            st.write(f"**{top['車番']}-{b1}-{n[1] if n[1] not in [top['車番'],b1] else n[2]}**")

        st.divider()
        st.subheader("📊 解析データ統合確認")
        df = pd.DataFrame(sorted_p)
        st.dataframe(df[["車番", "選手名", "競走得点", "脚", "1着", "勝率", "B", "逃", "捲", "差", "マ", "AI指数"]], use_container_width=True)
    else:
        st.error("選手情報を特定できませんでした。コピーの範囲を確認してください。")
