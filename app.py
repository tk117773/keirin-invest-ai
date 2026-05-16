import streamlit as st
import pandas as pd
import re

# --- ページ設定 ---
st.set_page_config(page_title="KEIRIN INVEST AI Ultimate", layout="wide")
st.title("🚴 KEIRIN INVEST AI Ultimate")
st.caption("【全項目抽出・安定版】決まり手・戦績・得点を確実に反映")

def extract_players_final(text):
    players = []
    # 選手ごとの開始（車番・名前）を特定
    matches = list(re.finditer(r'([1-9])\s+([^\s\d\(\)（）]+)[\s\n]*[\(（](\d{2})[\)）][\s\n]*([^\s/]+)', text))
    
    for i, m in enumerate(matches):
        car_num, name, age, pref = m.groups()
        end_idx = matches[i+1].start() if i+1 < len(matches) else len(text)
        block = text[m.start():end_idx]
        
        # --- 1. 全ての数値を抽出しリスト化 ---
        # 連続した空白や改行を一旦スペース1つに置換して扱いやすくする
        clean_block = re.sub(r'\s+', ' ', block)
        all_nums = re.findall(r'\d+\.\d+|\d+', clean_block)
        
        # --- 2. 競走得点・ギアの抽出 ---
        score_val = 0.0
        gear_val = "-"
        for n in all_nums:
            f = float(n)
            if 35.0 <= f <= 150.0: score_val = f
            elif 3.0 <= f <= 4.5 and "." in n: gear_val = n

        # --- 3. 戦績（1着, 2着, 3着, 着外）と脚質 ---
        # 「逃」「追」などの脚質の直前にある4つの数字を探す
        stats = [0, 0, 0, 0]
        leg_val = "-"
        leg_match = re.search(r'(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(逃|両|追|自在|追込|逃げ)', clean_block)
        if leg_match:
            stats = [int(x) for x in leg_match.groups()[:4]]
            leg_val = leg_match.group(5)

        # --- 4. 決まり手（S B 逃 捲 差 マ）の抽出ロジック改良 ---
        # 「決まり手」は通常、勝率（小数点数値）の直前に6つ連続する整数
        # ブロック内から整数だけを抜き出して、パターンの位置を特定する
        ints_only = re.findall(r'(?<!\.)\b(\d{1,2})\b(?!\.)', block) # 小数点を含まない1-2桁の整数
        
        # 競輪データの構造上、後ろの方にある6つの数字が決まり手であることが多い
        dec = [0] * 6
        if len(ints_only) >= 6:
            # データの並び順（通常は S-B-逃-捲-差-マ）
            # 戦績データ（stats）を除いた後の数字から6つ取得
            dec = [int(x) for x in ints_only[-6:]] 

        # --- 5. 勝率・連対率（小数点第一位） ---
        # 14.2 などの形式を特定
        rates = [float(n) for n in all_nums if "." in n and 5.0 < float(n) < 95.0 and n != gear_val]
        win_r, ren_r, san_r = (rates[0], rates[1], rates[2]) if len(rates) >= 3 else (0.0, 0.0, 0.0)

        players.append({
            "車番": car_num, "選手名": name, "競走得点": score_val,
            "1着": stats[0], "2着": stats[1], "3着": stats[2], "着外": stats[3],
            "脚": leg_val, "ギア": gear_val,
            "勝率": win_r, "連対率": ren_r, "3連対率": san_r,
            "S": dec[0], "B": dec[1], "逃": dec[2], "捲": dec[3], "差": dec[4], "マ": dec[5]
        })
    return players

def calculate_ai_score(players, line_raw):
    for p in players:
        # 指数計算：B（バック）と勝率、逃げ・捲りの数値を大幅に加点
        score = (p["競走得点"] * 1.0 + 
                 p["勝率"] * 1.5 + 
                 p["B"] * 4.5 +   # バック回数の価値を最大化
                 p["逃"] * 3.0 + 
                 p["捲"] * 2.5 + 
                 p["1着"] * 2.0)
        p["AI指数"] = round(score, 1)
    
    line_order = line_raw.split()
    sorted_p = sorted(players, key=lambda x: x["AI指数"], reverse=True)
    top_p = sorted_p[0]
    m_line = []
    if top_p["車番"] in line_order:
        idx = line_order.index(top_p["車番"])
        m_line = line_order[idx+1 : idx+3]
    return sorted_p, m_line

# --- UI部 ---
c1, c2 = st.columns([3, 1])
with c1: data_in = st.text_area("出走表を貼り付け", height=300)
with c2: line_in = st.text_area("並び (7 1 9...)", height=300)

if st.button("AIフル解析・データ反映実行", type="primary", use_container_width=True):
    players = extract_players_final(data_in)
    if players:
        sorted_p, m_line = calculate_ai_score(players, line_in)
        top = sorted_p[0]
        n = [p["車番"] for p in sorted_p]
        
        st.success(f"的中期待値: {round(min(20 + (top['AI指数']*0.2), 99.0), 1)}% / 軸: {top['選手名']}")
        
        col1, col2, col3 = st.columns(3)
        b1 = m_line[0] if len(m_line) > 0 else n[1]
        b2 = m_line[1] if len(m_line) > 1 else (n[2] if n[2]!=b1 else n[3])
        with col1:
            st.success("🔥 本線 (スジ・裏)")
            st.write(f"**{top['車番']}-{b1}-{b2}**")
            st.write(f"**{b1}-{top['車番']}-{b2}**")
            st.write(f"**{top['車番']}-{b1}-{n[1] if n[1] not in [top['車番'],b1] else n[2]}**")
        
        st.divider()
        st.subheader("📊 解析データ詳細（反映チェック）")
        # 表示する列を整理
        df_display = pd.DataFrame(sorted_p)
        st.dataframe(df_display[["車番", "選手名", "1着", "2着", "3着", "脚", "S", "B", "逃", "捲", "差", "マ", "勝率", "AI指数"]], use_container_width=True)
    else:
        st.error("選手情報を解析できませんでした。コピーの範囲（車番からコメントまで）を確認してください。")
