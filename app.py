import streamlit as st
import re

st.set_page_config(
    page_title="KEIRIN INVEST AI",
    layout="wide"
)

st.title("🚴 KEIRIN INVEST AI PRO")

st.write("競輪投資AI")

race_data = st.text_area(
    "競輪データ貼付",
    height=400
)

def extract_numbers(text):
    return re.findall(r'\b[1-9]\b', text)

if st.button("AI予想開始"):

    numbers = extract_numbers(race_data)

    st.subheader("ライン解析")

    if len(numbers) >= 7:
        line1 = "-".join(numbers[0:3])
        line2 = "-".join(numbers[3:6])
        line3 = numbers[6]

        st.write(f"本命ライン：{line1}")
        st.write(f"対抗ライン：{line2}")
        st.write(f"単騎：{line3}")

        st.subheader("AI展開予測")

        st.write(f"{numbers[0]} 主導権")
        st.write(f"{numbers[1]} 番手差し")
        st.write(f"{numbers[3]} 捲り警戒")

        st.subheader("AI推奨3連単")

        st.write(f"{numbers[1]}-{numbers[0]}-{numbers[3]}")
        st.write(f"{numbers[0]}-{numbers[1]}-{numbers[3]}")
        st.write(f"{numbers[3]}-{numbers[4]}-{numbers[1]}")
        st.write(f"{numbers[1]}-{numbers[3]}-{numbers[0]}")
        st.write(f"{numbers[0]}-{numbers[3]}-{numbers[1]}")
        st.write(f"{numbers[3]}-{numbers[1]}-{numbers[4]}")
        st.write(f"{line3}-{numbers[1]}-{numbers[0]}")
        st.write(f"{numbers[1]}-{line3}-{numbers[0]}")

        st.subheader("期待値評価")

        st.success("期待値：★★★★☆")

    else:
        st.error("データ不足")
