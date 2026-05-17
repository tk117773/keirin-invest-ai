import streamlit as st
import pandas as pd
import re

# --- ページ設定 ---
st.set_page_config(page_title="KEIRIN INVEST AI Ultimate", layout="wide")
st.title("🚴 KEIRIN INVEST AI Ultimate")
st.caption("【和歌山/Kドリームス形式】改行された数値を正確に紐付け解析")

def extract_combined_data_v3(text):
    data_map = {}
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    
    # 1. 選手リストの作成（まず全選手を特定する）
    for i, line in enumerate(lines):
        # 「1 1 岡崎 和久」または「7 櫻井 宏智」のような形式を抽出
        m = re.search(r'^([1-7])\s+([1-7])?\s*([^\s\d\/]{2,10}(?:\s+[^\s\d\/]+)?)', line)
        if m:
            car_num = m.group(2) if m.group(2) else m.group(1)
            name = m.group(3).replace(" ", "").replace("　", "")
            if car_num not in data_map:
                data_map[car_num] = {
                    "車番": car_num, "選手名": name, "競走得点": 0.0, "脚": "-", "ギア": "-",
                    "S": 0, "B": 0, "逃": 0, "捲": 0, "差": 0, "マ": 0,
                    "勝率": 0.0, "1着": 0, "2着": 0, "3着": 0, "着外": 0
                }

    # 2. 数値の紐付け（選手名の後の行にある数値を解析）
    for i, line in enumerate(lines):
        clean_line = line.replace(" ", "").replace("　", "")
        for c, p in data_map.items():
            if p["選手名"] in clean_line:
                # 選手名が見つかったら、その行および「次の行」を調べる
                context = line
                if i + 1 < len(lines):
                    context += " " + lines[i+1]
                
                nums = re.findall(r'\d+\.\d+|\d+', context)
                
                # --- A. 競走得点・決まり手セクション ---
                # 84.50 0 0 0 0 0 0 のような並び
                if any(35.0 <= float(x) <= 150.0 for x in nums if "." in x):
                    p["競走得点"] = next(float(x) for x in nums if 35.0 <= float(x) <= 150.0)
                    ints = [int(x) for x in nums if "." not in x]
                    if len(ints) >= 6:
                        p["S"], p["B"], p["逃"], p["捲"], p["差"], p["マ"] = ints[-6:]

                # --- B. 脚質・ギアセクション ---
                leg_m = re.search(r'(逃|両|追|自在|追込)', context)
                if leg_m: p["脚"] = leg_m.group(1)
                gear_m = re.search(r'([3-4]\.\d{2})', context)
                if gear_m: p["ギア"] = gear_m.group(1)

                # --- C. 勝率セクション ---
                # 11.1 33.3 44.4 のような並び
                rates = [float(x) for x in nums if "." in x and float(x) < 35.0]
                if len(rates) >= 3:
                    p["勝率"] = rates[0]

                # --- D. 戦績セクション (1着 2着 3着 着外) ---
                # 選手名の後の行に 2 4 2 10 のように整数が並ぶ
                ints_potential = [int(x) for x in nums if "." not in x]
                # 車番(c)の後の4つの数字を戦績とみなす
                try:
                    c_idx = -1
                    for idx, val in enumerate(ints_potential):
                        if val == int(c): c_idx = idx
                    if c_idx != -1 and len(ints_potential) > c_idx + 4:
                        p["1着"] = ints_potential[c_idx+1]
                        p["2着"] = ints_potential[c_idx+2]
                        p["3着"] = ints_potential[c_idx+3]
                        p["着外"] = ints_potential[c_idx+4]
                except: pass

    return list(data_map.values())

def calculate_ai_score(players, line_raw):
    for p in players:
        # 指数計算
        score = (p["競走得点"] * 1.5 + p["勝率"] * 1.2 + p["B"] * 4.0 + 
                 p["逃"] * 3.0 + p["1着"] * 2.5 + p["2着"] * 1.0)
        p["AI指数"] = round(score, 1)
    
    line_nums = re.findall(r'[1-7]', line_raw)
    sorted_p = sorted(players, key=lambda x: x["AI指数"], reverse=True)
    top_p = sorted_p[0] if sorted_p else None
    m_line = []
    if top_p and top_p["車番"] in line_nums:
        idx = line_nums.index(top_p["車番"])
        m_line = line_nums[idx+1 : idx+3]
    return sorted_p, m_line

# --- UI ---
st.info("和歌山競輪の出走表（得点・脚質・勝率・戦績すべて）をコピーして貼り付けてください。")
data_in = st.text_area("競輪データ貼り付け", height=400)
line_in = st.text_input("並び予想 (例: 3 7 4 5 2 6 1)", value="")

if st.button("🚀 和歌山データ解析実行", type="primary"):
    players = extract_combined_data_v3(data_in)
    if players:
        sorted_p, m_line = calculate_ai_score(players, line_in)
        top = sorted_p[0]
        n = [p["車番"] for p in sorted_p]
        
        st.success(f"【AI軸】 {top['車番']} {top['選手名']} (指数: {top['AI指数']})")
        
        # 買い目表示（簡易）
        b1 = m_line[0] if len(m_line) > 0 else n[1]
        b2 = m_line[1] if len(m_line) > 1 else (n[2] if n[2]!=b1 else n[3])
        st.code(f"3連単推奨: {top['車番']}-{b1}-{b2}, {top['車番']}-{b1}-{n[1] if n[1] not in [top['車番'],b1] else n[2]}")

        st.divider()
        st.subheader("📊 解析結果テーブル")
        st.dataframe(pd.DataFrame(sorted_p)[["車番", "選手名", "競走得点", "脚", "1着", "2着", "3着", "B", "逃", "捲", "勝率", "AI指数"]], use_container_width=True)
