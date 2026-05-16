import streamlit as st
import pandas as pd
import re

# --- ページ設定 ---
st.set_page_config(page_title="KEIRIN INVEST AI Ultimate", layout="wide")
st.title("🚴 KEIRIN INVEST AI Ultimate")
st.caption("【勝率反映・修正版】数値の位置構造から勝率・連対率を正確に抽出")

# --- 解析ロジック ---
def extract_players_full(text):
    players = []
    # 選手ごとのブロックを分割
    matches = list(re.finditer(r'([1-9])\s+([^\s\d\(\)（）]+)[\s\n]*[\(（](\d{2})[\)）][\s\n]*([^\s/]+)', text))
    
    for i, m in enumerate(matches):
        car_num, name, age, pref = m.groups()
        end_idx = matches[i+1].start() if i+1 < len(matches) else len(text)
        block = text[m.start():end_idx]
        
        # --- 1. 競走得点とギアの分離 ---
        # 競走得点は「府県/期別/級班」の直後に来ることが多い
        score_val = 0.0
        score_match = re.search(r'([3-9]\d\.\d{2}|1[0-4]\d\.\d{2})', block)
        if score_match:
            score_val = float(score_match.group(1))

        # ギア (3.0〜4.5の範囲)
        gear_val = "-"
        gear_match = re.search(r'([3-4]\.\d{2})', block)
        if gear_match:
            gear_val = gear_match.group(1)

        # --- 2. 勝率・連対率の抽出 (最重要修正) ---
        # ギア(3.92等)の後に現れる、小数点第一位までの数値を順番に取得
        # 例: 14.2  21.4  39.3
        float_rates = re.findall(r'(\d{1,3}\.\d)(?!\d)', block)
        # ギアや得点（小数点第二位）と混同しないよう正規表現を調整
        
        win_r, ren_r, san_r = 0.0, 0.0, 0.0
        if len(float_rates) >= 3:
            # 抽出された小数点第一位のリストから、順に勝率・連対率・3連対率を割り当て
            win_r = float(float_rates[0])
            ren_r = float(float_rates[1])
            san_r = float(float_rates[2])

        # --- 3. 戦績 (1着, 2着, 3着, 着外) ---
        stats = [0, 0, 0, 0]
        # 「4 2 5 17」のような並びを抽出
        stats_match = re.search(r'(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(?:逃|両|追|追込|自在)', block)
        if stats_match:
            stats = [int(x) for x in stats_match.groups()]
        
        # --- 4. 脚質・コメント ---
        leg_match = re.search(r'\n(逃|両|追)\n', block)
        leg_val = leg_match.group(1) if leg_match else "-"
        
        comment_val = "不明"
        comment_match = re.search(r'(?:逃|両|追|自在|追込)\s+\d\.\d{2}\s+([^\n\t]+)', block)
        if comment_match:
            comment_val = comment_match.group(1).strip()

        # --- 5. 決まり手（S B 逃 捲 差 マ） ---
        d = [0] * 6
        dec_match = re.findall(r'\n(\d+)\n(\d+)\n(\d+)\n(\d+)\n(\d+)\n(\d+)', block)
        if dec_match:
            d = [int(x) for x in dec_match[0]]

        players.append({
            "車番": car_num, "選手名": name, "競走得点": score_val, "府県": pref,
            "1着": stats[0], "2着": stats[1], "3着": stats[2], "着外": stats[3],
            "脚": leg_val, "ギア": gear_val, "コメント": comment_val,
            "勝率": win_r, "連対率": ren_r, "3連対率": san_r,
            "S": d[0], "B": d[1], "逃": d[2], "捲": d[3], "差": d[4], "マ": d[5]
        })
    return players

def calculate_ai_score(players, line_raw):
    for p in players:
        # 指数計算：勝率・連対率の重みを強化
        score = (p["競走得点"] * 1.0 + 
                 p["勝率"] * 2.5 +   # 勝率を2.5倍評価
                 p["連対率"] * 1.5 + # 連対率を1.5倍評価
                 p["B"] * 5.0 + 
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

# --- UI ---
c1, c2 = st.columns([3, 1])
with c1: data_in = st.text_area("競輪データを貼り付け", height=300)
with c2: line_in = st.text_area("並び (7 1 9...)", height=300)

if st.button("AIフル解析実行（勝率反映強化版）", type="primary", use_container_width=True):
    players = extract_players_full(data_in)
    if players:
        sorted_p, m_line = calculate_ai_score(players, line_in)
        top = sorted_p[0]
        n = [p["車番"] for p in sorted_p]
        
        st.success(f"的中期待値: {round(min(20 + (top['AI指数'] * 0.2), 98.8), 1)}% / 軸: {top['選手名']}")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.success("🔥 本線 (スジ重視)")
            b1 = m_line[0] if len(m_line) > 0 else n[1]
            b2 = m_line[1] if len(m_line) > 1 else (n[2] if n[2]!=b1 else n[3])
            st.write(f"**{top['車番']}-{b1}-{b2}**"); st.write(f"**{b1}-{top['車番']}-{b2}**")
            st.write(f"**{top['車番']}-{b1}-{n[1] if n[1] not in [top['車番'],b1] else n[2]}**")
            st.write(f"**{top['車番']}-{b2}-{b1}**")
        
        # 詳細データ表示
        st.divider()
        st.subheader("📊 解析データ詳細（勝率・連対率を反映）")
        st.dataframe(pd.DataFrame(sorted_p)[["車番", "選手名", "競走得点", "勝率", "連対率", "3連対率", "1着", "B", "AI指数"]], use_container_width=True)
    else:
        st.error("選手情報を解析できませんでした。")
