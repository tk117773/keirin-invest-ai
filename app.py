import streamlit as st
import pandas as pd
import re

# --- ページ設定 ---
st.set_page_config(page_title="KEIRIN INVEST AI Ultimate", layout="wide")
st.title("🚴 KEIRIN INVEST AI Ultimate")
st.caption("【データ形式最適化済】競走得点・戦績・決まり手を完全同期")

def extract_players_final(text):
    # 選手ごとの基本情報をまず抽出 (車番, 名前, 府県/年齢/期別/級班)
    player_data = {}
    
    # 選手基本情報の正規表現
    base_matches = re.findall(r'([1-9])\s+([1-9])\s+([^\n\t]+)\n([^\t\n]+)', text)
    if not base_matches:
        # 車番が1つ（枠番省略など）の場合の予備
        base_matches = re.findall(r'([1-9])\s+([^\n\t]+)\n([^\t\n]+)', text)

    # 1. 選手ごとにテキストを分割して解析
    # 「選手名」をキーにして、各ブロックから数値を集約する
    player_names = []
    for m in base_matches:
        name = m[1] if len(m) == 3 else m[2]
        name = name.strip()
        if name not in player_data:
            player_names.append(name)
            player_data[name] = {
                "車番": m[0] if len(m) == 3 else m[1],
                "名前": name,
                "詳細": m[1] if len(m) == 3 else m[2],
                "競走得点": 0.0, "S": 0, "B": 0, "逃": 0, "捲": 0, "差": 0, "マ": 0,
                "勝率": 0.0, "連対率": 0.0, "3連対率": 0.0,
                "1着": 0, "2着": 0, "3着": 0, "着外": 0
            }

    # 各数値データの抽出
    lines = text.split('\n')
    for name in player_names:
        for i, line in enumerate(lines):
            if name in line:
                # 次の行（府県など）とセットで数値を分析
                data_context = line + " " + (lines[i+1] if i+1 < len(lines) else "")
                nums = re.findall(r'\d+\.\d+|\d+', data_context)
                
                # A. 競走得点ブロック (得点, S, B, 逃, 捲, 差, マ)
                # 得点らしき数値 (35-150) があり、その後に整数が続く場合
                for j, n in enumerate(nums):
                    val = float(n)
                    if 35.0 <= val <= 150.0 and "." in n:
                        player_data[name]["競走得点"] = val
                        # その後の整数を決まり手として取得
                        rem = [int(x) for x in nums[j+1:] if "." not in x]
                        if len(rem) >= 6:
                            player_data[name]["S"], player_data[name]["B"], player_data[name]["逃"], \
                            player_data[name]["捲"], player_data[name]["差"], player_data[name]["マ"] = rem[:6]
                
                # B. 率ブロック (勝率, 2連, 3連)
                # 小数点が連続する箇所を探す
                floats = [float(x) for x in nums if "." in x and float(x) < 35.0]
                if len(floats) >= 3:
                    player_data[name]["勝率"], player_data[name]["連対率"], player_data[name]["3連対率"] = floats[:3]

                # C. 戦績ブロック (1, 2, 3, 外)
                # 名前の後の行に整数が4つ並んでいる箇所
                ints = [int(x) for x in nums if "." not in x and int(x) < 100]
                # 車番などの情報を除外するため、特定の並びを探す
                if len(ints) >= 5: # [車番, 1, 2, 3, 外] のような並び
                    player_data[name]["1着"], player_data[name]["2着"], \
                    player_data[name]["3着"], player_data[name]["着外"] = ints[1:5]

    return list(player_data.values())

def calculate_ai_score(players, line_raw):
    for p in players:
        # 指数計算
        score = (p["競走得点"] * 1.5 + p["勝率"] * 1.0 + p["B"] * 4.0 + p["逃"] * 2.0 + p["1着"] * 2.0)
        p["AI指数"] = round(score, 1)
    
    # 並びからライン先頭を特定
    line_groups = re.findall(r'[1-9]+', line_raw)
    sorted_p = sorted(players, key=lambda x: x["AI指数"], reverse=True)
    
    # 軸の決定
    top_p = sorted_p[0] if sorted_p else None
    
    # 軸のライン後続を特定
    m_line = []
    clean_line = "".join(line_groups)
    if top_p and top_p["車番"] in clean_line:
        idx = clean_line.find(top_p["車番"])
        m_line = list(clean_line[idx+1:idx+3])
        
    return sorted_p, m_line

# --- UI ---
c1, c2 = st.columns([3, 1])
with c1: data_in = st.text_area("出走表データを全て貼り付け", height=400)
with c2: line_in = st.text_area("並び (← 52 61...)", height=400)

if st.button("AI解析実行", type="primary", use_container_width=True):
    results = extract_players_final(data_in)
    if results:
        sorted_p, m_line = calculate_ai_score(results, line_in)
        top = sorted_p[0]
        n = [p["車番"] for p in sorted_p]
        
        st.success(f"軸予想: {top['車番']} {top['名前']} (得点: {top['競走得点']} / 指数: {top['AI指数']})")
        
        # 買い目生成
        col1, col2, col3 = st.columns(3)
        b1 = m_line[0] if len(m_line) > 0 else n[1]
        b2 = m_line[1] if len(m_line) > 1 else (n[2] if n[2]!=b1 else n[3])
        with col1:
            st.success("🔥 本線 (スジ・実力)")
            st.write(f"**{top['車番']}-{b1}-{b2}**")
            st.write(f"**{b1}-{top['車番']}-{b2}**")
            st.write(f"**{top['車番']}-{b1}-{n[1] if n[1] not in [top['車番'],b1] else n[2]}**")

        st.divider()
        st.subheader("📊 解析データ一覧（競走得点・戦績反映済み）")
        df = pd.DataFrame(sorted_p)
        # ユーザーが求める項目の順番に固定
        cols = ["車番", "名前", "競走得点", "1着", "2着", "3着", "S", "B", "逃", "捲", "差", "マ", "勝率", "AI指数"]
        st.dataframe(df[cols], use_container_width=True)
    else:
        st.error("データの解析に失敗しました。形式を確認してください。")
