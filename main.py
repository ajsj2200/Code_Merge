import streamlit as st
import json
from io import BytesIO


def download_session_state(classes, selected_classes, class_codes):
    session_state_dict = {
        "classes": classes,
        "selected_classes": selected_classes,
        **{
            f"class_code_{class_name}": code for class_name, code in class_codes.items()
        },
    }

    session_state_json = json.dumps(session_state_dict)
    bio = BytesIO(session_state_json.encode())
    bio.seek(0)

    download_button = st.sidebar.download_button(
        label="세션 상태 다운로드",
        data=bio,
        file_name="session_state.json",
        mime="application/json",
    )


def load_session_state(classes):
    uploaded_file = st.sidebar.file_uploader("세션 상태 업로드", type="json")
    if uploaded_file is not None and "session_state_loaded" not in st.session_state:
        session_state_json = uploaded_file.read().decode()
        session_state_dict = json.loads(session_state_json)
        uploaded_classes = session_state_dict.get("classes", [])
        merged_classes = list(set(classes + uploaded_classes))
        class_codes = {
            class_name: session_state_dict.get(f"class_code_{class_name}", "")
            for class_name in uploaded_classes
        }
        st.session_state["classes"] = merged_classes
        for class_name, code in class_codes.items():
            if f"class_code_{class_name}" not in st.session_state:
                st.session_state[f"class_code_{class_name}"] = code
        st.success("세션 상태가 로드되었습니다.")
        st.session_state["session_state_loaded"] = True
    return st.session_state["classes"]


def initialize_session_state():
    if "classes" not in st.session_state:
        st.session_state["classes"] = []
    if "selected_classes" not in st.session_state:
        st.session_state["selected_classes"] = []
    return st.session_state["classes"], st.session_state["selected_classes"]


def manage_classes(classes, selected_classes, class_name):
    if class_name not in classes:
        classes.append(class_name)
        st.session_state["classes"] = classes
        selected_classes = classes.copy()  # 복사본 할당
    else:
        st.sidebar.error(f"{class_name}는 이미 추가된 자료입니다.")
    return classes, selected_classes


def remove_class(classes, selected_classes, class_name):
    if class_name in classes:
        classes.remove(class_name)
        selected_classes.remove(
            class_name) if class_name in selected_classes else None
        st.session_state["classes"] = classes
        st.session_state["selected_classes"] = selected_classes
    return classes, selected_classes


def load_prompts(USE_COMMENT_PROMPT, USE_SYSTEM_PROMPT):
    return {
        "comment": (
            open("comment prompt.txt", "r", encoding="utf-8").read()
            if USE_COMMENT_PROMPT
            else ""
        ),
        "system": (
            open("system prompt.txt", "r", encoding="utf-8").read()
            if USE_SYSTEM_PROMPT
            else ""
        ),
        "instruction": open("instruction prompt.txt", "r", encoding="utf-8").read(),
    }


def get_content(
    classes,
    class_display_options,
    class_codes,
    USE_INSTRUCTION_PROMPT,
    USE_COMMENT_PROMPT,
    USE_SYSTEM_PROMPT,
    prompts,
    question,
):
    user_content = f"[요청: {question}]"
    selected_classes = [
        class_name for class_name in classes if class_display_options[class_name]
    ]
    st.session_state["selected_classes"] = selected_classes
    st.write(selected_classes)
    code_contents = "\n\n".join(
        [
            f"################ {class_name} 코드:\n{class_codes[class_name]}"
            for class_name in selected_classes
        ]
    )
    if USE_INSTRUCTION_PROMPT:
        content = f"{code_contents}\n[User Instruction] \n\n[{
            prompts['instruction']}]\n\n{user_content}"
    else:
        content = f"{code_contents}\n{user_content}"
    if USE_COMMENT_PROMPT:
        content = f"{prompts['comment']}\n\n [위 코딩 가이드를 참고하여 아래 코드에 주석을 한국어로 달아주세요.]\n\nCode : \n\n{
            code_contents}"
    if USE_SYSTEM_PROMPT:
        content = f"System instruction : {prompts['system']}\n\n사용자가 제공한 코드 : \n\n{
            code_contents}\n\n{prompts['instruction']}]\n\n{user_content}\n\n한국어로 대답해줘. 코드는 위에 있어."
    return content


def main():
    st.set_page_config(page_title="Code Input and Copy UI", layout="wide")
    st.title("코드 입력 및 복사 UI")

    # 세션 상태 초기화
    classes, selected_classes = initialize_session_state()

    # 세션 초기화 버튼 추가
    if st.sidebar.button("세션 초기화"):
        st.session_state.clear()
        classes = []
        selected_classes = []
        st.experimental_rerun()

    # 파일 업로드 및 세션 상태 업데이트
    classes = load_session_state(classes)

    # 사이드바에 자료 추가 및 삭제 섹션 생성
    st.sidebar.title("자료 관리")
    class_name = st.sidebar.text_input("자료 이름 입력", key="class_name_input")

    # 자료 추가 버튼
    if st.sidebar.button("자료 추가", key="add_class") and class_name:
        classes, selected_classes = manage_classes(
            classes, selected_classes, class_name
        )

    # 자료 삭제 버튼
    if st.sidebar.button("자료 삭제", key="delete_class") and class_name:
        classes, selected_classes = remove_class(
            classes, selected_classes, class_name
        )

    classes = st.session_state["classes"]

    # 사이드바에 자료 리스트 표시
    st.sidebar.title("자료 리스트")
    class_display_options = {}
    for i, class_name in enumerate(classes):
        class_display_options[class_name] = st.sidebar.checkbox(
            class_name, value=True, key=f"display_{i}"
        )

    st.write(st.session_state["classes"])

    # 모든 자료의 코드 입력 필드 표시
    class_codes = {}
    # classes에 값이 있는 경우 수행
    if classes:
        tabs = st.tabs(classes)

        for i, class_name in enumerate(classes):
            with tabs[i]:
                class_codes[class_name] = st.text_area(
                    f"{class_name} 코드 입력",
                    height=150,
                    key=f"class_code_{class_name}",
                )

        # 저장 및 로드 버튼
        if st.sidebar.button("세션 상태 다운로드"):
            download_session_state(classes, selected_classes, class_codes)

    # 요청 입력 필드
    question = st.text_area("요청 입력", height=150)

    # 언어 선택
    LANGUAGE = "python" if not st.checkbox("C++ 사용") else "cpp"

    # 프롬프트 설정
    USE_INSTRUCTION_PROMPT = True
    USE_COMMENT_PROMPT = st.checkbox("주석 사용")
    USE_SYSTEM_PROMPT = st.checkbox("시스템 프롬프트 사용")

    # 프롬프트 파일 불러오기
    prompts = load_prompts(USE_COMMENT_PROMPT, USE_SYSTEM_PROMPT)

    if st.button("요청과 선택된 자료 내용들 복사"):
        content = get_content(
            classes,
            class_display_options,
            class_codes,
            USE_INSTRUCTION_PROMPT,
            USE_COMMENT_PROMPT,
            USE_SYSTEM_PROMPT,
            prompts,
            question,
        )

        # 클립보드에 복사
        st.success("아래 복사 버튼을 누르세요.")
        st.code(content, language=LANGUAGE)


if __name__ == "__main__":
    main()
