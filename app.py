import streamlit as st
import pandas as pd
import re

# --- ページ設定 ---
st.set_page_config(page_title="KEIRIN INVEST AI Ultimate", layout="wide")
st.title("🚴 KEIRIN INVEST AI Ultimate")
st.caption("【新形式対応】バラバラのデータを統合・全項目をAI解析に反映")

def extract_combined_data(text):
    # 選手ごとにデータを格納する辞書
    data_map = {}

    # 1. 選手名と基本情報(車番)をキーとして登録
    # 「1 1 岡崎 和久」のような形式を抽出
    player_base = re.findall(r'([1-9])\s+([1-9])\s+([^\s\d]+(?:\s+[^\s\d]+)?)', text)
    for p in player_base:
        car_num, name = p[1], p[2].strip()
        if car_num not in data_map:
            data_map[car_num] = {"車番": car_num, "選手名": name, "競走得点": 0.0, "脚": "-", "ギア": "-", 
                                 "S": 0, "B": 0, "逃": 0, "捲": 0, "差": 0, "マ": 0,
                                 "勝率": 0.0, "2連対率": 0.0, "3連対率": 0.0,
                                 "1着": 0, "2着": 0, "3着": 0, "着外": 0}

    # 各セクションから数値を抽出
    lines = text.split('\n')
    
    for i, line in enumerate(lines):
        # --- A. 競走得点・決まり手セクション ---
        # 形式: 車番 選手名 府県... 競走得点 S B 逃 捲 差 マ
        m = re.search(r'([1-9])\s+([^\s\d]+(?:\s+[^\s\d]+)?)\s+.*\s+(\d{2}\.\d{2})\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)', line)
        if m:
            c = m.group(1)
            if c in data_map:
                data_map[c]["競走得点"] = float(m.group(3))
                data_map[c]["S"], data_map[c]["B"] = int(m.group(4)), int(m.group(5))
                data_map[c]["逃"], data_map[c]["捲"] = int(m.group(6)), int(m.group(7))
                data_map[c]["差"], data_map[c]["マ"] = int(m.group(8)), int(m.group(9))

        # --- B. 脚質・ギアセクション ---
        # 形式: 選手名 府県... 脚 ギア
        m_leg = re.search(r'([^\s\d]+(?:\s+[^\s\d]+)?)\s+.*\s+(逃|両|追)\s+(\d\.\d{2})', line)
        if m_leg:
            name_key = m_leg.group(1).strip()
            for c in data_map:
                if data_map[c]["選手名"] == name_key:
                    data_map[c]["脚"] = m_leg.group(2)
                    data_map[c]["ギア"] = m_leg.group(3)

        # --- C. 勝率セクション ---
        # 形式: 選手名 府県... 勝率 2連 3連
        m_rate = re.search(r'([^\s\d]+(?:\s+[^\s\d]+)?)\s+.*\s+(\d+\.\d)\s+(\d+\.\d)\s+(\d+\.\d)', line)
        if m_rate:
            name_key = m_rate.group(1).strip()
            for c in data_map:
                if data_map[c]["選手名"] == name_key:
                    data_map[c]["勝率"] = float(m_rate.group(2))
                    data_map[c]["2連対率"] = float(m_rate.group(3))
                    data_map[c]["3連対率"] = float(m_rate.group(4))

        # --- D. 1-3着 戦績セクション ---
        # 形式: 選手名 府県... 1着 2着 3着 着外
        m_stats = re.search(r'([^\s\d]+(?:\s+[^\s\d]+)?)\s+.*\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)', line)
        if m_stats and "着外" in text: # 戦績セクションであることの確認
            name_key = m_stats.group(1).strip()
            for c in data_map:
                if data_map[c]["選手名"] == name_key:
                    data_map[c]["1着"] = int(m_stats.group(2))
                    data_map[c]["2着"] = int(m_stats.group(3))
                    data_map[c]["3着"] = int(m_stats.group(4))
                    data_map[c]["着外"] = int(m_stats.group(5))

    return list(data_map.values())

def calculate_ai_score(players, line_raw):
    for p in players:
        # 指数計算：競走得点をベースに、B（バック）や勝率、決まり手で補正
        score = (p["競走得点"] * 1.5 + 
                 p["勝率"] * 2.0 + 
                 p["B"] * 4.0 + 
                 p["逃"] * 3.0 + 
                 p["1着"] * 2.5)
        p["AI指数"] = round(score, 1)
    
    # 並び予想からラインを解析 (例: ← 5 2 6 1 3 7 4)
    line_order = re.findall(r'[1-9]', line_raw)
    sorted_p = sorted(players, key=lambda x: x["AI指数"], reverse=True)
    
    top_p = sorted_p[0] if sorted_p else None
    m_line = []
    if top_p and top_p["車番"] in line_order:
        idx = line_order.index(top_p["車番"])
        m_line = line_order[idx+1 : idx+3] # 軸の後ろ2人を抽出
        
    return sorted_p, m_line

# --- UI ---
c1, c2 = st.columns([3, 1])
with c1: data_in = st.text_area("競輪データを全て貼り付け（複数セクション可）", height=400)
with c2: line_in = st.text_area("並び予想 (5 2 6...)", height=400)

if st.button("AIフル解析実行", type="primary", use_container_width=True):
    players = extract_combined_data(data_in)
    if players:
        sorted_p, m_line = calculate_ai_score(players, line_in)
        top = sorted_p[0]
        n = [p["車番"] for p in sorted_p]
        
        st.success(f"【AI軸予想】 {top['車番']} {top['選手名']} (競走得点: {top['競走得点']})")
        
        # 買い目（スジ・裏・突き抜け）
        col1, col2, col3 = st.columns(3)
        b1 = m_line[0] if len(m_line) > 0 else n[1]
        b2 = m_line[1] if len(m_line) > 1 else (n[2] if n[2]!=b1 else n[3])
        
        with col1:
            st.success("🔥 本線 (スジ重視)")
            st.write(f"**{top['車番']}-{b1}-{b2}**") # ライン決着
            st.write(f"**{b1}-{top['車番']}-{b2}**") # 番手差し
        with col2:
            st.warning("⚖️ 抑え")
            st.write(f"**{top['車番']}-{b1}-{n[1] if n[1] not in [top['車番'],b1] else n[2]}**")
        with col3:
            st.error("🚀 穴 (突き抜け)")
            st.write(f"**{b1}-{b2}-{top['車番']}**")

        st.divider()
        st.subheader("📊 解析データ統合テーブル（全項目反映済み）")
        df = pd.DataFrame(sorted_p)
        cols = ["車番", "選手名", "競走得点", "脚", "1着", "勝率", "B", "逃", "捲", "差", "マ", "AI指数"]
        st.dataframe(df[cols], use_container_width=True)
