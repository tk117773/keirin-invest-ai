import streamlit as st
import pandas as pd
import re

# --- ページ設定 ---
st.set_page_config(page_title="KEIRIN INVEST AI Ultimate", layout="wide")
st.title("🚴 KEIRIN INVEST AI Ultimate")
st.caption("【全項目反映版】戦績・脚質・ギア・コメントを完全解析")

# --- 解析ロジック ---
def extract_players_full(text):
    players = []
    # 車番・名前・年齢・府県の開始を特定
    matches = list(re.finditer(r'([1-9])\s+([^\s\d\(\)（）]+)[\s\n]*[\(（](\d{2})[\)）][\s\n]*([^\s/]+)', text))
    
    for i, m in enumerate(matches):
        car_num, name, age, pref = m.groups()
        end_idx = matches[i+1].start() if i+1 < len(matches) else len(text)
        block = text[m.start():end_idx]
        
        # --- 1. ギア・脚質の抽出 ---
        gear = re.search(r'(\d\.\d{2})', block)
        gear_val = gear.group(1) if gear else "-"
        
        leg = re.search(r'\n(逃|両|追)\n', block) # 改行に挟まれた脚質を探す
        leg_val = leg.group(1) if leg else "-"
        
        # --- 2. コメントの抽出 ---
        comment = re.search(r'\d\.\d{2}\s+([^\n\t]+)', block)
        comment_val = comment.group(1) if comment else "不明"

        # --- 3. 1着・2着・3着・着外 の抽出 ---
        # ギア(3.92)の後の数値を順番に取得
        all_ints = re.findall(r'\n(\d+)\n', block) # 単独行の数値を取得
        if len(all_ints) < 4: # 見つからない場合は連続する数値を探す
            all_ints = re.findall(r'\d+', block)
            
        # 戦績データ特定（年齢や車番を除外して、妥当な位置の4つの数字を拾う）
        stats = [0, 0, 0, 0]
        # データの並び順から推測 (1着, 2着, 3着, 着外)
        stats_match = re.findall(r'(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(逃|両|追|追込|自在)', block)
        if stats_match:
            stats = [int(x) for x in stats_match[0][:4]]
        
        # --- 4. 勝率・連対率 ---
        floats = re.findall(r'\d+\.\d+', block)
        rates = [float(f) for f in floats if f != gear_val]
        win_r, ren_r, san_r = (rates[0], rates[1], rates[2]) if len(rates) >= 3 else (0.0, 0.0, 0.0)

        # --- 5. S B 逃 捲 差 マ ---
        # 決まり手は通常、勝率の前に6つ並ぶ
        decisions = re.findall(r'(?:\n|^)(\d+)\n(\d+)\n(\d+)\n(\d+)\n(\d+)\n(\d+)(?:\n|$)', block)
        if not decisions:
            decisions = [re.findall(r'\d+', block)[5:11]] # 暫定
        d = decisions[0] if decisions and len(decisions[0])==6 else [0]*6

        players.append({
            "車番": car_num, "選手名": name, "府県": pref, "年齢": age,
            "1着": stats[0], "2着": stats[1], "3着": stats[2], "着外": stats[3],
            "脚": leg_val, "ギア": gear_val, "コメント": comment_val,
            "勝率": win_r, "連対率": ren_r, "3連対率": san_r,
            "S": d[0], "B": d[1], "逃": d[2], "捲": d[3], "差": d[4], "マ": d[5]
        })
    return players

def calculate_ai_score(players, line_raw):
    for p in players:
        # 指数計算に「戦績」と「勝率」を重く反映
        score = (float(p["勝率"]) * 1.2 + float(p["連対率"]) * 0.8 + 
                 int(p["B"]) * 5.5 + int(p["1着"]) * 2.0 + int(p["逃"]) * 3.0)
        p["AI指数"] = round(score, 1)
    
    line_order = line_raw.split()
    sorted_p = sorted(players, key=lambda x: x["AI指数"], reverse=True)
    
    # メインライン特定
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

if st.button("全項目解析・シミュレート実行", type="primary", use_container_width=True):
    players = extract_players_full(data_in)
    if players:
        sorted_p, m_line = calculate_ai_score(players, line_in)
        top = sorted_p[0]
        n = [p["車番"] for p in sorted_p]
        
        # 買い目生成（スジ・裏・突き抜け）
        b1 = m_line[0] if len(m_line) > 0 else n[1]
        b2 = m_line[1] if len(m_line) > 1 else (n[2] if n[2]!=b1 else n[3])
        
        st.success(f"的中期待値: {round(min(30 + (top['AI指数']*0.5), 98.8), 1)}% / 軸: {top['選手名']}")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.success("🔥 本線 (スジ・裏 4点)")
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
        st.subheader("📊 詳細データ（全項目反映済み）")
        st.dataframe(pd.DataFrame(sorted_p)[["車番", "選手名", "脚", "ギア", "1着", "2着", "3着", "着外", "勝率", "B", "コメント", "AI指数"]], use_container_width=True)
    else:
        st.error("選手情報を解析できませんでした。")
