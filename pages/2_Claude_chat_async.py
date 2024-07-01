import streamlit as st
import asyncio
from anthropic import AsyncAnthropic
import pyperclip

# api_key.txt 파일에서 API 키를 읽어오기
api_key = open("api_key.txt", "r").read()
try:
    client = AsyncAnthropic(api_key=api_key)
except:
    client = AsyncAnthropic()

st.set_page_config(
    page_title="Anthropic Async Stream Demo",
    layout="wide",
)

# 세션 상태 초기화
if 'generate_clicked' not in st.session_state:
    st.session_state.generate_clicked = False
if 'all_results' not in st.session_state:
    st.session_state.all_results = ""

# 사용자가 입력한 프롬프트를 받는 텍스트 영역
prompt = st.text_area(
    "Input Prompt", st.session_state.get('prompt', ''), height=500)

# 에세이 수를 선택하는 슬라이더
num_essays = st.slider("Number of Essays", min_value=1, max_value=10, value=2)

# generate 버튼 클릭 시 동작하는 함수


def on_generate_click():
    st.session_state.generate_clicked = True


generate = st.button("Generate", on_click=on_generate_click)

# 에세이를 표시할 플레이스홀더를 여러 컬럼에 배치
placeholders = []

# 에세이가 1개면 1개의 컬럼에 배치
if num_essays == 1:
    cols = st.columns(1)
    for col in cols:
        placeholders.append((col.empty(), col.empty()))
else:
    for i in range(0, num_essays, 2):
        cols = st.columns(2)
        for col in cols:
            if len(placeholders) < num_essays:
                placeholders.append((col.empty(), col.empty()))

# 에세이 생성 함수


async def generate_essay(title_placeholder, content_placeholder, prompt, essay_number):
    title_placeholder.subheader(f"Output {essay_number + 1}")

    streamed_text = ""
    async with client.messages.stream(
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
        model="claude-3-5-sonnet-20240620",
    ) as stream:
        async for text in stream.text_stream:
            streamed_text += text
            # Changed from .info() to .markdown()
            content_placeholder.info(streamed_text)

    return streamed_text

# 메인 함수


async def main():
    tasks = [
        generate_essay(title_placeholder, content_placeholder,
                       prompt=prompt, essay_number=i)
        for i, (title_placeholder, content_placeholder) in enumerate(placeholders)
    ]
    results = await asyncio.gather(*tasks)
    return results

# 복사 기능


def copy_to_clipboard(text):
    pyperclip.copy(text)
    st.success("Content copied to clipboard!")


# generate 버튼이 클릭되었고, 아직 처리되지 않았다면 메인 함수 실행
if st.session_state.generate_clicked:
    results = asyncio.run(main())

    # 모든 결과를 하나의 문자열로 결합
    st.session_state.all_results = f"사용자 요청 : {prompt}\n\n"
    for i, result in enumerate(results, 1):
        st.session_state.all_results += f"{i}번 출력 : \n{result}\n\n"

    # generate_clicked 상태 재설정
    st.session_state.generate_clicked = False

summary_prompt = f"\n\n[위는 사용자와 AI간의 대화입니다. 이를 참고로 하고 스스로 새로운 내용도 추가하여 사용자의 요청에 대해 답변하세요. \n\n 사용자 요청 : {
    st.session_state.request}]"
final_results = st.session_state.all_results + summary_prompt
# 복사 버튼 추가
if st.button("Copy All Results"):
    summary_prompt = f"\n\n[위는 사용자와 AI간의 대화입니다. 이를 참고로 하고 스스로 새로운 내용도 추가하여 사용자의 요청에 대해 답변하세요. \n\n 사용자 요청 : {
        st.session_state.request}]"
    final_results = st.session_state.all_results + summary_prompt
    copy_to_clipboard(final_results)

# 결과 표시
st.write("모든 결과:")
st.text_area("", final_results, height=300)
