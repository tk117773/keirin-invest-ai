import streamlit as st
import pandas as pd
import re

# --- ページ設定 ---
st.set_page_config(page_title="KEIRIN INVEST AI Ultimate", layout="wide")
st.title("🚴 KEIRIN INVEST AI Ultimate")
st.caption("【修正版】競走得点を最優先表示・データ抽出ロジックを強化")

def extract_players_final(text):
    players = []
    # 選手ごとの開始（車番・名前）を特定
    matches = list(re.finditer(r'([1-9])\s+([^\s\d\(\)（）]+)[\s\n]*[\(（](\d{2})[\)）][\s\n]*([^\s/]+)', text))
    
    for i, m in enumerate(matches):
        car_num, name, age, pref = m.groups()
        end_idx = matches[i+1].start() if i+1 < len(matches) else len(text)
        block = text[m.start():end_idx]
        
        # スペースを統一
        clean_block = re.sub(r'\s+', ' ', block)
        all_floats = re.findall(r'\d+\.\d+', clean_block)
        all_ints = re.findall(r'(?<!\.)\b(\d{1,3})\b(?!\.)', block)
        
        # --- 1. 競走得点の抽出 (35.00 - 150.00) ---
        score_val = 0.0
        gear_val = "-"
        for f_str in all_floats:
            f = float(f_str)
            if 35.0 <= f <= 150.0:
                score_val = f  # 競走得点
            elif 3.0 <= f <= 5.0:
                gear_val = f_str # ギア

        # --- 2. 戦績（1, 2, 3, 外） ---
        stats = [0, 0, 0, 0]
        leg_val = "-"
        # 「4 2 5 17 追」のようなパターンを狙う
        st_match = re.search(r'(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(逃|両|追|自在|追込|逃げ)', clean_block)
        if st_match:
            stats = [int(x) for x in st_match.groups()[:4]]
            leg_val = st_match.group(5)

        # --- 3. 決まり手（S B 逃 捲 差 マ） ---
        # 縦に並んだ数字を想定し、整数リストから末尾に近い部分を取得
        dec = [0] * 6
        if len(all_ints) >= 6:
            # 決まり手は通常ブロックの後半にあるため、後ろから特定
            dec = [int(x) for x in all_ints[-6:]]

        # --- 4. 勝率・連対率 ---
        rates = [float(n) for n in all_floats if 5.0 < float(n) < 95.0 and n != str(score_val) and n != gear_val]
        win_r, ren_r, san_r = (rates[0], rates[1], rates[2]) if len(rates) >= 3 else (0.0, 0.0, 0.0)

        players.append({
            "車番": car_num, "選手名": name, "競走得点": score_val,
            "脚": leg_val, "1着": stats[0], "2着": stats[1], "3着": stats[2],
            "S": dec[0], "B": dec[1], "逃": dec[2], "捲": dec[3], "差": dec[4], "マ": dec[5],
            "勝率": win_r, "ギア": gear_val
        })
    return players

def calculate_ai_score(players, line_raw):
    for p in players:
        # 指数計算
        score = (p["競走得点"] * 1.2 + p["勝率"] * 1.0 + p["B"] * 4.0 + p["逃"] * 3.0 + p["1着"] * 2.0)
        p["AI指数"] = round(score, 1)
    
    line_order = line_raw.split()
    sorted_p = sorted(players, key=lambda x: x["AI指数"], reverse=True)
    top_p = sorted_p[0] if sorted_p else None
    m_line = []
    if top_p and top_p["車番"] in line_order:
        idx = line_order.index(top_p["車番"])
        m_line = line_order[idx+1 : idx+3]
    return sorted_p, m_line

# --- UI部 ---
c1, c2 = st.columns([3, 1])
with c1: data_in = st.text_area("出走表を貼り付け", height=300)
with c2: line_in = st.text_area("並び (7 1 9...)", height=300)

if st.button("AIフル解析実行", type="primary", use_container_width=True):
    players = extract_players_final(data_in)
    if players:
        sorted_p, m_line = calculate_ai_score(players, line_in)
        top = sorted_p[0]
        n = [p["車番"] for p in sorted_p]
        
        st.success(f"軸予想: {top['車番']} {top['選手名']} (競走得点: {top['競走得点']})")
        
        # 買い目
        col1, col2, col3 = st.columns(3)
        b1 = m_line[0] if len(m_line) > 0 else n[1]
        b2 = m_line[1] if len(m_line) > 1 else (n[2] if n[2]!=b1 else n[3])
        with col1:
            st.success("🔥 本線")
            st.write(f"**{top['車番']}-{b1}-{b2}**")
            st.write(f"**{b1}-{top['車番']}-{b2}**")
        
        st.divider()
        st.subheader("📊 解析データ詳細（競走得点を左側に配置）")
        df_display = pd.DataFrame(sorted_p)
        # 列の順番を入れ替えて「競走得点」を最初の方に持ってくる
        target_cols = ["車番", "選手名", "競走得点", "脚", "1着", "2着", "3着", "B", "逃", "捲", "差", "マ", "AI指数"]
        st.dataframe(df_display[target_cols], use_container_width=True)
    else:
        st.error("選手情報を解析できませんでした。")
