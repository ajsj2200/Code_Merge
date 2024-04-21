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

    st.sidebar.download_button(
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


def main():
    st.set_page_config(page_title="Code Input and Copy UI", layout="wide")
    st.title("코드 입력 및 복사 UI")

    # 세션 상태 초기화
    if "classes" not in st.session_state:
        st.session_state["classes"] = []
    if "selected_classes" not in st.session_state:
        st.session_state["selected_classes"] = []

    classes = st.session_state["classes"]
    selected_classes = st.session_state["selected_classes"]

    # 세션 초기화 버튼 추가
    if st.sidebar.button("세션 초기화"):
        st.session_state.clear()
        classes = []
        selected_classes = []
        st.experimental_rerun()

    # 파일 업로드 및 세션 상태 업데이트
    classes = load_session_state(classes)

    col1, col2 = st.columns(2)

    with col1:
        # 사이드바에 클래스 추가 및 삭제 섹션 생성
        st.sidebar.title("클래스 관리")
        class_name = st.sidebar.text_input("클래스 이름 입력", key="class_name_input")

        # 클래스 추가 버튼
        if st.sidebar.button("클래스 추가", key="add_class") and class_name:
            if class_name not in classes:
                classes.append(class_name)
                st.session_state["classes"] = classes
                selected_classes = classes.copy()  # 복사본 할당
            else:
                st.sidebar.error(f"{class_name}는 이미 추가된 클래스입니다.")

        # 클래스 삭제 버튼
        if st.sidebar.button("클래스 삭제", key="delete_class") and class_name:
            if class_name in classes:
                classes.remove(class_name)
                (
                    selected_classes.remove(class_name)
                    if class_name in selected_classes
                    else None
                )
                st.session_state["classes"] = classes
                st.session_state["selected_classes"] = selected_classes

        classes = st.session_state["classes"]

        # 사이드바에 클래스 리스트 표시
        st.sidebar.title("클래스 리스트")
        class_display_options = {}
        for i, class_name in enumerate(classes):
            class_display_options[class_name] = st.sidebar.checkbox(
                class_name, value=True, key=f"display_{i}"
            )

        st.write(st.session_state["classes"])

        # 모든 클래스의 코드 입력 필드 표시
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

        with col2:
            # 요청 입력 필드
            question = st.text_area("요청 입력", height=150)
            USE_INSTRUCTION_PROMPT = True
            USE_COMMENT_PROMPT = False
            USE_SYSTEM_PROMPT = False

            LANGUAGE = "python"
            if st.checkbox("C++ 사용"):
                LANGUAGE = "cpp"

            # 주석 사용 여부 선택
            if st.checkbox("주석 사용"):
                USE_COMMENT_PROMPT = True
                with open("comment prompt.txt", "r", encoding="utf-8") as f:
                    comment_prompt = f.read()

            # 시스템 프롬프트 사용 여부 선택
            if st.checkbox("시스템 프롬프트 사용"):
                USE_SYSTEM_PROMPT = True
                with open("system prompt.txt", "r", encoding="utf-8") as f:
                    system_prompt = f.read()

            # 복사 버튼
            if st.button("요청과 선택된 클래스 코드들 복사"):
                # 요청과 선택된 클래스들의 코드 내용 합치기
                with open("instruction prompt.txt", "r", encoding="utf-8") as f:
                    instruction_prompt = f.read()
                user_content = f"[요청: {question}]"
                code_contents = ""

                # selected_classes 리스트 초기화
                selected_classes = []

                # 현재 선택된 클래스만 selected_classes에 추가
                for class_name in classes:
                    if class_display_options[class_name]:
                        selected_classes.append(class_name)

                st.session_state["selected_classes"] = selected_classes

                st.write(st.session_state["selected_classes"])
                for class_name in st.session_state["selected_classes"]:
                    code_contents += f"################ {class_name} 코드:\n{class_codes[class_name]}\n\n"

                # instruction prompt 사용 여부에 따라 content 구성
                if USE_INSTRUCTION_PROMPT:
                    content = (
                        code_contents
                        + "[User Instruction] \n\n["
                        + instruction_prompt
                        + "]\n\n"
                        + user_content
                    )
                else:
                    content = code_contents + user_content

                if USE_COMMENT_PROMPT:
                    content = (
                        comment_prompt
                        + "\n\n [위 코딩 가이드를 참고하여 아래 코드에 주석을 한국어로 달아주세요.]\n\n"
                        + "Code : \n\n"
                        + code_contents
                    )

                if USE_SYSTEM_PROMPT:
                    content = (
                        "System instruction : "
                        + system_prompt
                        + "\n\n"
                        + "사용자가 제공한 코드 : \n\n"
                        + code_contents
                        + "\n\n"
                        + instruction_prompt
                        + "]\n\n"
                        + user_content
                        + "\n\n 한국어로 대답해줘. 코드는 위에 있어."
                    )

                # 클립보드에 복사
                st.success("아래 복사 버튼을 누르세요.")
                st.code(content, language=LANGUAGE)


if __name__ == "__main__":
    main()
