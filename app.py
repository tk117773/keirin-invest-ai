import streamlit as st
import pandas as pd
import re

# --- ページ設定 ---
st.set_page_config(page_title="KEIRIN INVEST AI Ultimate", layout="wide")
st.title("🚴 KEIRIN INVEST AI Ultimate")
st.caption("【最終深化版】スジ裏・ライン独占・番手突き抜け 全パターン対応")

# --- 解析ロジック ---
def extract_players(text):
    players = []
    # 車番・名前・年齢・府県を抽出
    matches = list(re.finditer(r'([1-9])\s+([^\s\d\(\)（）]+)[\s\n]*[\(（](\d{2})[\)）][\s\n]*([^\s/]+)', text))
    for i, m in enumerate(matches):
        car_num, name, age, pref = m.groups()
        block = text[m.start():matches[i+1].start() if i+1 < len(matches) else len(text)]
        nums = re.findall(r"\d+\.\d+|\d+", block)
        floats = [float(n) for n in nums if "." in n]
        ints = [int(n) for n in nums if "." not in n and int(n) != int(age) and int(n) < 60]
        
        # 決まり手（S B 逃 捲 差 マ）
        s, b, ni, ma, sa, mi = 0, 0, 0, 0, 0, 0
        for j in range(len(ints) - 5):
            win = ints[j:j+6]
            if 0 < sum(win) < 120:
                s, b, ni, ma, sa, mi = win; break
        
        # 指標
        w, r, t = 0.0, 0.0, 0.0
        tf = [f for f in floats if f != 3.92]
        if len(tf) >= 3: w, r, t = tf[:3]

        players.append({"車番": car_num, "選手名": name, "年齢": int(age), "府県": pref, 
                        "S": s, "B": b, "逃": ni, "捲": ma, "差": sa, "マ": mi, 
                        "勝率": w, "連対率": r, "3連対率": t})
    return players

def calculate_logic(players, line_raw):
    # 個人スコア（自力・追込両面評価）
    for p in players:
        p["AIスコア"] = round(p["勝率"] * 1.5 + p["B"] * 6.0 + p["逃"] * 4.0 + p["差"] * 2.5 + p["マ"] * 2.0, 1)

    line_order = line_raw.split()
    sorted_p = sorted(players, key=lambda x: x["AIスコア"], reverse=True)
    top_p = sorted_p[0]
    
    # メインラインの特定（軸の前後）
    main_line = []
    idx = line_order.index(top_p["車番"]) if top_p["車番"] in line_order else -1
    
    # 軸が先頭の場合の後続を抽出
    if idx != -1:
        for i in range(idx + 1, min(idx + 4, len(line_order))):
            if line_order[i].isdigit(): main_line.append(line_order[i])
            else: break
            
    return sorted_p, main_line

# --- UI ---
c1, c2 = st.columns([3, 1])
with c1: data_in = st.text_area("出走表データを入力", height=250)
with c2: line_in = st.text_area("並び (7 1 9...)", height=250)

if st.button("AI解析・全展開シミュレート開始", type="primary", use_container_width=True):
    players = extract_players(data_in)
    if players:
        sorted_p, main_line = calculate_logic(players, line_in)
        top = sorted_p[0]
        n = [p["車番"] for p in sorted_p]
        
        # スジ展開の構築
        b1 = main_line[0] if len(main_line) > 0 else n[1]
        b2 = main_line[1] if len(main_line) > 1 else (n[2] if n[2] != b1 else n[3])
        
        # 買い目生成ロジック
        hon = [
            f"{top['車番']}-{b1}-{b2}", # ズブズブ（ライン決着）
            f"{b1}-{top['車番']}-{b2}", # 番手差し（裏）
            f"{top['車番']}-{b1}-{n[1] if n[1] not in [top['車番'], b1, b2] else n[2]}", # ライン＋別線
            f"{top['車番']}-{b2}-{b1}"  # 軸-3番手-番手
        ]
        
        chu = [
            f"{b1}-{b2}-{top['車番']}", # 番手-3番手-軸（突き抜け）
            f"{top['車番']}-{n[1] if n[1]!=b1 else n[2]}-{b1}" # 軸-別線-番手
        ]
        
        ana = [
            f"{b2}-{top['車番']}-{b1}", # 3番手強襲
            f"{n[2] if n[2] not in [top['車番'], b1] else n[3]}-{top['車番']}-{b1}" # 別線捲り
        ]

        # 表示
        st.success(f"的中期待値: {round(min(40 + (top['AIスコア']*0.4), 98.5), 1)}% / 軸: {top['選手名']}")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.success("🔥 本線 (スジ・番手差し 4点)")
            for b in hon: st.write(f"**{b}**")
        with col2:
            st.warning("⚖️ 中穴 (展開変位 2点)")
            for b in chu: st.write(f"**{b}**")
        with col3:
            st.error("🚀 大穴 (突き抜け 2点)")
            for b in ana: st.write(f"**{b}**")

        st.divider()
        st.subheader("📊 解析データ一覧")
        st.dataframe(pd.DataFrame(sorted_p)[["車番", "選手名", "AIスコア", "B", "逃", "差", "マ"]], use_container_width=True)
    else:
        st.error("選手情報を解析できませんでした。")
