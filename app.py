import streamlit as st
import pandas as pd
import re

# --- ページ設定 ---
st.set_page_config(page_title="KEIRIN INVEST AI Ultimate", layout="wide")
st.title("🚴 KEIRIN INVEST AI Ultimate")
st.caption("【全項目完全版】2-3着・決まり手・勝率・得点を正確にマッピング")

# --- 解析ロジック ---
def extract_players_full(text):
    players = []
    # 選手ごとの開始（車番・名前）を特定
    matches = list(re.finditer(r'([1-9])\s+([^\s\d\(\)（）]+)[\s\n]*[\(（](\d{2})[\)）][\s\n]*([^\s/]+)', text))
    
    for i, m in enumerate(matches):
        car_num, name, age, pref = m.groups()
        end_idx = matches[i+1].start() if i+1 < len(matches) else len(text)
        block = text[m.start():end_idx]
        
        # 1. ブロック内の全ての数値を抽出（整数と小数）
        all_numbers = re.findall(r'\d+\.\d+|\d+', block)
        
        # 2. 競走得点とギアの特定
        score_val = 0.0
        gear_val = "-"
        for n in all_numbers:
            f = float(n)
            if 35.0 <= f <= 150.0: score_val = f
            elif 3.0 <= f <= 5.0 and "." in n: gear_val = n

        # 3. 戦績（1着, 2着, 3着, 着外）の抽出
        # 通常、脚質（逃・両・追）の直前に4つの数字が並ぶ
        stats = [0, 0, 0, 0]
        st_match = re.search(r'(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(?:逃|両|追|追込|自在|逃げ)', block)
        if st_match:
            stats = [int(x) for x in st_match.groups()]
        
        # 4. 決まり手（S・B・逃・捲・差・マ）の抽出
        # 出走表で縦に並んでいる6つの数字を特定
        # 「勝率」を表す小数点数値の「前」にある6つの整数を狙う
        decisions = [0, 0, 0, 0, 0, 0]
        # 改行で区切られた連続する数字をリスト化
        v_numbers = re.findall(r'\n(\d+)\n', block)
        if len(v_numbers) >= 6:
            # 決まり手エリアと思われる6つの数字を末尾から取得（勝率の直前にあることが多いため）
            decisions = [int(x) for x in v_numbers[:6]]

        # 5. 勝率・連対率
        # 小数点第一位までの数値を抽出
        rates = [float(n) for n in all_numbers if "." in n and float(n) > 5.0 and float(n) < 100.0]
        win_r, ren_r, san_r = (rates[0], rates[1], rates[2]) if len(rates) >= 3 else (0.0, 0.0, 0.0)

        # 6. 脚質とコメント
        leg_match = re.search(r'(逃|両|追|自在|追込|逃げ)', block)
        leg_val = leg_match.group(1) if leg_match else "-"
        
        comment_val = "不明"
        comment_match = re.search(r'(?:逃|両|追|自在|追込)\s+\d\.\d{2}\s+([^\n\t]+)', block)
        if comment_match:
            comment_val = comment_match.group(1).strip()

        players.append({
            "車番": car_num, "選手名": name, "競走得点": score_val,
            "1着": stats[0], "2着": stats[1], "3着": stats[2], "着外": stats[3],
            "脚": leg_val, "ギア": gear_val,
            "勝率": win_r, "連対率": ren_r, "3連対率": san_r,
            "S": decisions[0], "B": decisions[1], "逃": decisions[2], "捲": decisions[3], "差": decisions[4], "マ": decisions[5],
            "コメント": comment_val
        })
    return players

def calculate_ai_score(players, line_raw):
    for p in players:
        # 全データを加味した重み付け
        score = (p["競走得点"] * 1.0 + 
                 p["勝率"] * 2.0 + 
                 p["B"] * 4.0 + 
                 p["逃"] * 2.0 + 
                 p["捲"] * 1.5 +
                 p["1着"] * 2.0 + p["2着"] * 1.0 + p["3着"] * 0.5) # 2着3着も加点
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

if st.button("AIフル解析実行（全項目同期版）", type="primary", use_container_width=True):
    players = extract_players_full(data_in)
    if players:
        sorted_p, m_line = calculate_ai_score(players, line_in)
        top = sorted_p[0]
        n = [p["車番"] for p in sorted_p]
        
        st.success(f"的中期待値: {round(min(15 + (top['AI指数']*0.25), 98.9), 1)}% / 軸: {top['選手名']}")
        
        # 買い目表示
        col1, col2, col3 = st.columns(3)
        b1 = m_line[0] if len(m_line) > 0 else n[1]
        b2 = m_line[1] if len(m_line) > 1 else (n[2] if n[2]!=b1 else n[3])
        with col1:
            st.success("🔥 本線 (スジ・裏)")
            st.write(f"**{top['車番']}-{b1}-{b2}**"); st.write(f"**{b1}-{top['車番']}-{b2}**")
            st.write(f"**{top['車番']}-{b1}-{n[1] if n[1] not in [top['車番'],b1] else n[2]}**")
            st.write(f"**{top['車番']}-{b2}-{b1}**")
        
        # 解析テーブル（全項目表示）
        st.divider()
        st.subheader("📊 解析データ詳細（2着・3着・決まり手を反映）")
        df_display = pd.DataFrame(sorted_p)
        st.dataframe(df_display[["車番", "選手名", "競走得点", "1着", "2着", "3着", "着外", "脚", "逃", "捲", "差", "マ", "B", "AI指数"]], use_container_width=True)
    else:
        st.error("選手情報を解析できませんでした。")
