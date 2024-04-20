import streamlit as st

def main():
    st.set_page_config(page_title="Code Input and Copy UI", layout="wide")

    st.title("코드 입력 및 복사 UI")

    col1, col2 = st.columns(2)

    with col1:
        # 사이드바에 클래스 추가 섹션 생성
        st.sidebar.title("클래스 관리")
        class_name = st.sidebar.text_input("클래스 이름 입력", key="class_name_input")
        if st.sidebar.button("클래스 추가", key="add_class") and class_name:
            # 클래스 이름을 세션 상태에 추가
            if "classes" not in st.session_state:
                st.session_state["classes"] = []
            st.session_state["classes"].append(class_name)

        # 사이드바에서 선택된 클래스들 가져오기 (기본적으로 모든 클래스 선택)
        selected_classes = st.sidebar.multiselect("클래스 선택", options=st.session_state.get("classes", []), default=st.session_state.get("classes", []), key="selected_classes")

        # 선택된 클래스들의 코드 입력 필드 표시
        class_codes = {}
        for class_name in selected_classes:
            class_codes[class_name] = st.text_area(f"{class_name} 코드 입력", key=f"class_code_{class_name}", height=50)

    with col2:
        # 요청 입력 필드
        question = st.text_area("요청 입력", height=150)

        # 복사 버튼
        if st.button("요청과 선택된 클래스 코드들 복사"):
            if selected_classes and all(class_codes.values()):
                # 요청과 선택된 클래스들의 코드 내용 합치기
                instruction_prompt = "\n\n[위 코드를 참고하여 요청에 대답하세요. 답변은 구체적이며 자세하게 합니다. 그리고 코드를 작성할 때는 코드의 가독성을 높이기 위해 주석을 사용하세요.]\n\n"
                content2 = f"[요청: {question}]"
                content = ""
                for class_name in selected_classes:
                    content += f"################ {class_name} 코드:\n{class_codes[class_name]}\n\n"
                content = content + instruction_prompt + content2

                # 클립보드에 복사
                st.code(content)
                st.success("요청과 선택된 클래스 코드들이 복사되었습니다.")
            else:
                st.warning("클래스를 선택하고 코드를 입력해주세요.")

if __name__ == "__main__":
    main()