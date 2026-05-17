import streamlit as st
import pandas as pd
import re

# --- ページ設定 ---
st.set_page_config(page_title="KEIRIN INVEST AI Ultimate", layout="wide")
st.title("🚴 KEIRIN INVEST AI Ultimate")
st.caption("【URLデータ統合版】Kドリームス等の出走表を丸ごとコピペで全自動解析")

def extract_combined_data_ultimate(text):
    data_map = {}
    lines = text.split('\n')
    
    # 1. 選手名と車番を紐付け（ベース作成）
    for line in lines:
        # 車番 選手名 府県 などの並びから抽出
        base_match = re.search(r'([1-9])\s+([1-9])\s+([^\s\d\/]+(?:\s+[^\s\d\/]+)?)', line)
        if not base_match:
            # 車番と名前だけのパターン
            base_match = re.search(r'([1-9])\s+([^\s\d\/]{2,10})', line)
            
        if base_match:
            car_num = base_match.group(1)
            name = base_match.group(len(base_match.groups())).strip().replace(" ", "").replace("　", "")
            if car_num not in data_map and len(name) > 1:
                data_map[car_num] = {
                    "車番": car_num, "選手名": name, "競走得点": 0.0, "脚": "-", 
                    "S": 0, "B": 0, "逃": 0, "捲": 0, "差": 0, "マ": 0,
                    "勝率": 0.0, "2連対率": 0.0, "3連対率": 0.0,
                    "1着": 0, "2着": 0, "3着": 0, "AI指数": 0.0
                }

    # 2. 各行から数値を抽出し、選手名で合体させる
    for line in lines:
        line_nums = re.findall(r'\d+\.\d+|\d+', line)
        if not line_nums: continue
        
        # この行がどの選手のデータか特定
        target_player = None
        clean_line = line.replace(" ", "").replace("　", "")
        for c, p_info in data_map.items():
            if p_info["選手名"] in clean_line:
                target_player = c
                break
        
        if not target_player: continue
        p = data_map[target_player]

        # 数値のリストを浮動小数点に変換
        floats = [float(x) for x in line_nums]
        ints = [int(x) for x in line_nums if "." not in x]

        # --- A. 競走得点・決まり手 (35以上があれば得点セクション) ---
        if any(35.0 <= f <= 150.0 for f in floats):
            p["競走得点"] = next(f for f in floats if 35.0 <= f <= 150.0)
            # 得点の後に続く整数を決まり手として取得
            if len(ints) >= 6:
                p["S"], p["B"], p["逃"], p["捲"], p["差"], p["マ"] = ints[-6:]

        # --- B. 勝率・連対率 (小数点1位が3つ並ぶ) ---
        rates = [f for f in floats if 0.0 <= f <= 100.0 and len(str(f).split('.')[-1]) == 1 and f < 35.0]
        if len(rates) >= 3:
            p["勝率"], p["2連対率"], p["3連対率"] = rates[0], rates[1], rates[2]

        # --- C. 戦績 (1-3着) ---
        if "着外" in text or len(ints) >= 5:
            # 行の中に含まれる車番(target_player)を探し、その後の数字を拾う
            try:
                idx = ints.index(int(target_player))
                if len(ints) > idx + 4:
                    p["1着"], p["2着"], p["3着"] = ints[idx+1], ints[idx+2], ints[idx+3]
            except: pass

        # --- D. 脚質 ---
        leg_m = re.search(r'(逃|両|追|自在|追込)', line)
        if leg_m: p["脚"] = leg_m.group(1)

    return list(data_map.values())

def calculate_ai_score(players, line_raw):
    for p in players:
        # 指数ロジック（スジ・番手勝負・自力を多角的に評価）
        score = (p["競走得点"] * 1.5 + p["勝率"] * 1.2 + p["B"] * 4.0 + 
                 p["逃"] * 3.0 + p["捲"] * 2.5 + p["1着"] * 2.0 + p["2着"] * 1.0)
        p["AI指数"] = round(score, 1)
    
    line_nums = re.findall(r'[1-9]', line_raw)
    sorted_p = sorted(players, key=lambda x: x["AI指数"], reverse=True)
    top_p = sorted_p[0] if sorted_p else None
    m_line = []
    if top_p and top_p["車番"] in line_nums:
        idx = line_nums.index(top_p["車番"])
        m_line = line_nums[idx+1 : idx+3]
    return sorted_p, m_line

# --- UI ---
st.info("💡 使い方: URL先の出走表ページで『Ctrl+A（全選択）』→『Ctrl+C（コピー）』し、下の枠に貼り付けてください。")
data_in = st.text_area("出走表データを丸ごと貼り付け", height=300)
line_in = st.text_input("並び予想 (例: 5 2 6 1 3 7 4)", value="")

if st.button("🚀 AI解析・全データ統合実行", type="primary"):
    players = extract_combined_data_ultimate(data_in)
    if players:
        sorted_p, m_line = calculate_ai_score(players, line_in)
        top = sorted_p[0]
        n = [p["車番"] for p in sorted_p]
        
        st.success(f"【AI本命軸】 {top['車番']} {top['選手名']} (指数: {top['AI指数']})")
        
        # 買い目 8点
        b1 = m_line[0] if len(m_line) > 0 else n[1]
        b2 = m_line[1] if len(m_line) > 1 else (n[2] if n[2]!=b1 else n[3])
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.success("🔥 本線(スジ)")
            st.write(f"**{top['車番']}-{b1}-{b2}**")
            st.write(f"**{top['車番']}-{b1}-{n[1] if n[1] not in [top['車番'],b1,b2] else n[2]}**")
        with col2:
            st.warning("⚖️ 逆転(スジ裏)")
            st.write(f"**{b1}-{top['車番']}-{b2}**")
            st.write(f"**{b1}-{top['車番']}-{n[1] if n[1] not in [top['車番'],b1,b2] else n[2]}**")
        with col3:
            st.error("🚀 展開穴")
            st.write(f"**{top['車番']}-{b2}-{b1}**")
            st.write(f"**{b1}-{b2}-{top['車番']}**")

        st.divider()
        st.subheader("📊 統合解析データ（URLからのコピペ反映結果）")
        st.dataframe(pd.DataFrame(sorted_p)[["車番", "選手名", "競走得点", "脚", "1着", "勝率", "B", "逃", "捲", "差", "マ", "AI指数"]], use_container_width=True)
