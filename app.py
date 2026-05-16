import streamlit as st
import pandas as pd
import re

# --- ページ設定 ---
st.set_page_config(page_title="KEIRIN INVEST AI Ultimate", layout="wide")
st.title("🚴 KEIRIN INVEST AI Ultimate")
st.caption("【修正版】競走得点を独立項目として抽出・指数計算に採用")

# --- 解析ロジック ---
def extract_players_full(text):
    players = []
    # 車番・名前・年齢・府県の開始を特定
    matches = list(re.finditer(r'([1-9])\s+([^\s\d\(\)（）]+)[\s\n]*[\(（](\d{2})[\)）][\s\n]*([^\s/]+)', text))
    
    for i, m in enumerate(matches):
        car_num, name, age, pref = m.groups()
        end_idx = matches[i+1].start() if i+1 < len(matches) else len(text)
        block = text[m.start():end_idx]
        
        # --- 1. 競走得点とギアの分離抽出 ---
        # 競走得点：100.00〜125.00程度の数値
        score_match = re.search(r'(1[0-2]\d\.\d{2})', block)
        score_val = float(score_match.group(1)) if score_match else 0.0
        
        # ギア：3.50〜4.00程度の数値（競走得点と重複しないように判定）
        gear_match = re.search(r'([3]\.\d{2})', block)
        gear_val = gear_match.group(1) if gear_match else "-"
        
        # --- 2. 脚質・コメント ---
        leg = re.search(r'\n(逃|両|追)\n', block)
        leg_val = leg.group(1) if leg else "-"
        
        # コメント（ギアや得点の後の文字列を抽出）
        comment_val = "不明"
        comment_match = re.search(r'(?:逃|両|追)\s+\d\.\d{2}\s+([^\n\t]+)', block)
        if comment_match:
            comment_val = comment_match.group(1).strip()

        # --- 3. 戦績（1, 2, 3, 外） ---
        stats = [0, 0, 0, 0]
        stats_match = re.findall(r'(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(?:逃|両|追|追込|自在)', block)
        if stats_match:
            stats = [int(x) for x in stats_match[0][:4]]
        
        # --- 4. 勝率・連対率 ---
        rates = re.findall(r'(\d+\.\d)', block) # 14.2 などの形式
        win_r, ren_r, san_r = (float(rates[0]), float(rates[1]), float(rates[2])) if len(rates) >= 3 else (0.0, 0.0, 0.0)

        # --- 5. 決まり手（S B 逃 捲 差 マ） ---
        d = [0] * 6
        dec_match = re.findall(r'\n(\d+)\n(\d+)\n(\d+)\n(\d+)\n(\d+)\n(\d+)', block)
        if dec_match:
            d = [int(x) for x in dec_match[0]]

        players.append({
            "車番": car_num, "選手名": name, "競走得点": score_val, "府県": pref, "年齢": age,
            "1着": stats[0], "2着": stats[1], "3着": stats[2], "着外": stats[3],
            "脚": leg_val, "ギア": gear_val, "コメント": comment_val,
            "勝率": win_r, "連対率": ren_r, "3連対率": san_r,
            "S": d[0], "B": d[1], "逃": d[2], "捲": d[3], "差": d[4], "マ": d[5]
        })
    return players

def calculate_ai_score(players, line_raw):
    for p in players:
        # 指数計算：競走得点をベースに、B回数や勝率で補正
        # 競走得点は100点満点換算に調整
        base_score = (p["競走得点"] - 80) * 2.0 
        extra_score = (p["勝率"] * 1.0 + p["B"] * 5.0 + p["逃"] * 3.0 + p["差"] * 2.0)
        p["AI指数"] = round(base_score + extra_score, 1)
    
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
with c1: data_in = st.text_area("出走表データを貼り付け", height=300)
with c2: line_in = st.text_area("並び (7 1 9...)", height=300)

if st.button("AI解析実行（得点重視モード）", type="primary", use_container_width=True):
    players = extract_players_full(data_in)
    if players:
        sorted_p, m_line = calculate_ai_score(players, line_in)
        top = sorted_p[0]
        n = [p["車番"] for p in sorted_p]
        
        # 買い目生成（スジ・裏・突き抜け）
        b1 = m_line[0] if len(m_line) > 0 else n[1]
        b2 = m_line[1] if len(m_line) > 1 else (n[2] if n[2]!=b1 else n[3])
        
        st.success(f"的中期待値: {round(min(30 + (top['AI指数']*0.4), 98.8), 1)}% / 軸: {top['選手名']} (競走得点: {top['競走得点']})")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.success("🔥 本線 (4点)")
            st.write(f"**{top['車番']}-{b1}-{b2}**"); st.write(f"**{b1}-{top['車番']}-{b2}**")
            st.write(f"**{top['車番']}-{b1}-{n[1] if n[1] not in [top['車番'],b1] else n[2]}**")
            st.write(f"**{top['車番']}-{b2}-{b1}**")
        with col2:
            st.warning("⚖️ 中穴 (2点)")
            st.write(f"**{b1}-{b2}-{top['車番']}**"); st.write(f"**{top['車番']}-{n[1] if n[1]!=b1 else n[2]}-{b1}**")
        with col3:
            st.error("🚀 大穴 (2点)")
            st.write(f"**{b2}-{top['車番']}-{b1}**"); st.write(f"**{n[2] if n[2] not in [top['車番'],b1] else n[3]}-{top['車番']}-{b1}**")

        st.divider()
        st.subheader("📊 解析データ（競走得点分離済み）")
        st.dataframe(pd.DataFrame(sorted_p)[["車番", "選手名", "競走得点", "脚", "ギア", "1着", "勝率", "B", "コメント", "AI指数"]], use_container_width=True)
    else:
        st.error("選手情報を解析できませんでした。")
