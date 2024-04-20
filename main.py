import streamlit as st
import json
from io import BytesIO


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
    uploaded_file = st.sidebar.file_uploader("세션 상태 업로드", type="json")
    if uploaded_file is not None:
        session_state_json = uploaded_file.read().decode()
        session_state_dict = json.loads(session_state_json)
        uploaded_classes = session_state_dict.get("classes", [])

        # 업로드한 클래스와 현재 클래스 병합
        merged_classes = list(set(classes + uploaded_classes))

        class_codes = {
            class_name: session_state_dict.get(f"class_code_{class_name}", "")
            for class_name in uploaded_classes
        }

        st.session_state["classes"] = merged_classes

        for class_name, code in class_codes.items():
            st.session_state[f"class_code_{class_name}"] = code

        st.success("세션 상태가 로드되었습니다.")

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
        for class_name in classes:
            class_codes[class_name] = st.text_area(
                f"{class_name} 코드 입력", key=f"class_code_{class_name}", height=50
            )
            if class_display_options[class_name]:
                selected_classes.append(class_name)
            else:
                if class_name in selected_classes:
                    selected_classes.remove(class_name)

        st.session_state["selected_classes"] = selected_classes

        # 저장 및 로드 버튼
        if st.sidebar.button("세션 상태 다운로드"):
            # 세션 상태를 일반 Python 딕셔너리로 변환
            session_state_dict = {
                "classes": classes,
                "selected_classes": selected_classes,
                **{
                    f"class_code_{class_name}": code
                    for class_name, code in class_codes.items()
                },
            }
            # 딕셔너리를 JSON 형식으로 변환
            session_state_json = json.dumps(session_state_dict)
            # 문자열을 BytesIO 객체로 변환
            bio = BytesIO()
            bio.write(session_state_json.encode())
            bio.seek(0)  # 파일 포인터를 처음으로 이동
            # 파일 다운로드
            st.sidebar.download_button(
                label="세션 상태 다운로드",
                data=bio,
                file_name="session_state.json",
                mime="application/json",
            )

    with col2:
        # 요청 입력 필드
        question = st.text_area("요청 입력", height=150)
        USE_INSTRUCTION_PROMPT = True
        USE_COMMENT_PROMPT = False

        LANGUAGE = "python"
        if st.checkbox("C++ 사용"):
            LANGUAGE = "cpp"

        # 주석 사용 여부 선택
        if st.checkbox("주석 사용"):
            USE_COMMENT_PROMPT = True
            with open("comment prompt.txt", "r", encoding="utf-8") as f:
                comment_prompt = f.read()

        # 복사 버튼
        if st.button("요청과 선택된 클래스 코드들 복사"):
            # 요청과 선택된 클래스들의 코드 내용 합치기
            with open("instruction prompt.txt", "r", encoding="utf-8") as f:
                instruction_prompt = f.read()
            content2 = f"[요청: {question}]"
            content = ""

            # selected_classes 리스트 초기화
            selected_classes = []

            # 현재 선택된 클래스만 selected_classes에 추가
            for class_name in classes:
                if class_display_options[class_name]:
                    selected_classes.append(class_name)

            st.session_state["selected_classes"] = selected_classes

            st.write(st.session_state["selected_classes"])
            for class_name in st.session_state["selected_classes"]:
                content += f"################ {class_name} 코드:\n{class_codes[class_name]}\n\n"

            # instruction prompt 사용할건지 안할건지 선택
            if USE_INSTRUCTION_PROMPT:
                content = (
                    content
                    + "[User Instruction] \n\n["
                    + instruction_prompt
                    + "]\n\n"
                    + content2
                )
            else:
                content = content + content2

            if USE_COMMENT_PROMPT:
                content = (
                    comment_prompt
                    + "\n\n [위 주석 가이드를 참고하여 아래 코드에 주석을 달아주세요.]\n\n"
                    + "Code : \n\n"
                    + content2
                )

            # 클립보드에 복사
            st.success("아래 복사 버튼을 누르세요.")
            st.code(content, language=LANGUAGE)


if __name__ == "__main__":
    main()
