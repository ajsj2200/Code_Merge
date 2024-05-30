import streamlit as st
import asyncio
from openai import AsyncOpenAI

# openai_api_key.txt load
api_key = open("openai_api_key.txt", "r").read()
try:
    client = AsyncOpenAI(api_key=api_key)
except:
    client = AsyncOpenAI()

st.set_page_config(
    page_title="OpenAI Async Stream Demo",
    layout="wide",
)

prompt = st.text_area("input prompt", st.session_state['prompt'])

num_essays = st.slider("Number of Essays", min_value=1, max_value=10, value=4)

placeholders = [(st.empty(), st.empty()) for _ in range(num_essays)]
generate = st.button("Generate")


async def generate_essay(title_placeholder, content_placeholder, prompt, essay_number):
    title_placeholder.subheader(f"Essay {essay_number + 1}")
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


async def main():
    tasks = [
        generate_essay(title_placeholder, content_placeholder,
                       prompt=prompt, essay_number=i)
        for i, (title_placeholder, content_placeholder) in enumerate(placeholders)
    ]
    await asyncio.gather(*tasks)

if generate:
    asyncio.run(main())
