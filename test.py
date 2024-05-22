import os
import json
import streamlit as st
import google.generativeai as genai
import textwrap
# API 키 로드 함수


@st.cache_resource
def load_api_key():
    try:
        with open("gemini_api_key.txt", "r") as file:
            api_key = file.read().strip()
        return api_key
    except FileNotFoundError:
        st.error("API 키 파일이 존재하지 않습니다.")
        return ""
    except Exception as e:
        st.error(f"API 키 파일을 읽는 중 오류가 발생했습니다: {str(e)}")
        return ""

# 문장 완성 추천 함수


def generate_text(context, num_candidates=1, max_blocks=1):
    api_key = load_api_key()
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name='gemini-1.5-flash-latest')

    response = model.generate_content(
        textwrap.dedent(f"""
            Complete the following text with {max_blocks} sentence(s) per block. Provide {num_candidates} candidate(s) for each block.

            Context:
            {context}
        """),
        request_options={'max_candidates': num_candidates}
    )

    if response and response.candidates:
        completions = [candidate.text for candidate in response.candidates]
        return completions
    else:
        return ["추천 문장을 생성할 수 없습니다."]

# Streamlit 인터페이스


def main():
    st.title("AI 문장 완성 추천 시스템")

    context = st.text_area("문맥 입력", height=200)
    num_candidates = st.number_input(
        "후보 수", min_value=1, max_value=10, value=1)
    max_blocks = st.number_input("블록 수", min_value=1, max_value=5, value=1)

    if st.button("문장 추천 받기"):
        if context.strip() == "":
            st.error("문맥을 입력해주세요.")
        else:
            completions = generate_text(context, num_candidates, max_blocks)
            for i, completion in enumerate(completions):
                st.subheader(f"후보 {i+1}")
                st.write(completion)


if __name__ == "__main__":
    main()
