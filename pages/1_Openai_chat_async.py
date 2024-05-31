import streamlit as st
import asyncio
from openai import AsyncOpenAI

# openai_api_key.txt 파일에서 API 키를 읽어오기
api_key = open("openai_api_key.txt", "r").read()
try:
    client = AsyncOpenAI(api_key=api_key)
except:
    client = AsyncOpenAI()

st.set_page_config(
    page_title="OpenAI Async Stream Demo",
    layout="wide",
)

# 사용자가 입력한 프롬프트를 받는 텍스트 영역
prompt = st.text_area(
    "Input Prompt", st.session_state.get('prompt', ''), height=500)

# 에세이 수를 선택하는 슬라이더
num_essays = st.slider("Number of Essays", min_value=1, max_value=10, value=4)
generate = st.button("Generate")

# 에세이를 표시할 플레이스홀더를 여러 컬럼에 배치
placeholders = []

for i in range(0, num_essays, 2):
    cols = st.columns(2)
    for col in cols:
        if len(placeholders) < num_essays:
            placeholders.append((col.empty(), col.empty()))

# 에세이 생성 함수


async def generate_essay(title_placeholder, content_placeholder, prompt, essay_number):
    title_placeholder.subheader(f"Output {essay_number + 1}")
    stream = await client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "system", "content": "You are a helpful assistant."},
                  {"role": "user", "content": prompt}],
        stream=True,
        max_tokens=4096
    )
    streamed_text = ""
    async for chunk in stream:
        chunk_content = chunk.choices[0].delta.content
        if chunk_content is not None:
            streamed_text += chunk_content
            content_placeholder.info(streamed_text)

# 메인 함수


async def main():
    tasks = [
        generate_essay(title_placeholder, content_placeholder,
                       prompt=prompt, essay_number=i)
        for i, (title_placeholder, content_placeholder) in enumerate(placeholders)
    ]
    await asyncio.gather(*tasks)

# 버튼이 눌리면 메인 함수 실행
if generate:
    asyncio.run(main())
