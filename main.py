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
    
    # 파일 업로드 및 세션 상태 업데이트
    uploaded_file = st.sidebar.file_uploader("세션 상태 업로드", type="json")
    if uploaded_file is not None:
        session_state_json = uploaded_file.read().decode()
        session_state_dict = json.loads(session_state_json)
        uploaded_classes = session_state_dict.get("classes", [])
        uploaded_selected_classes = session_state_dict.get("selected_classes", [])
        
        # 업로드한 클래스와 현재 클래스 병합
        merged_classes = list(set(classes + uploaded_classes))
        merged_selected_classes = list(set(selected_classes + uploaded_selected_classes))
        
        class_codes = {class_name: session_state_dict.get(f"class_code_{class_name}", "") for class_name in merged_selected_classes}
        
        st.session_state["classes"] = merged_classes
        st.session_state["selected_classes"] = merged_selected_classes
        
        for class_name, code in class_codes.items():
            st.session_state[f"class_code_{class_name}"] = code
        
        st.success("세션 상태가 로드되었습니다.")
        
        
    
    col1, col2 = st.columns(2)
    
    with col1:
        # 사이드바에 클래스 추가 섹션 생성
        st.sidebar.title("클래스 관리")
        class_name = st.sidebar.text_input("클래스 이름 입력", key="class_name_input")
        if st.sidebar.button("클래스 추가", key="add_class") and class_name:
            # 클래스 이름을 classes 리스트에 추가
            if class_name not in classes:
                classes.append(class_name)
                st.session_state["classes"] = classes
                selected_classes = classes
        classes = st.session_state["classes"]
        
        # 사이드바에서 선택된 클래스들 가져오기 (기본적으로 모든 클래스 선택)
        if not selected_classes:
            selected_classes = st.session_state["classes"]
        print(classes, selected_classes)
        selected_classes = st.sidebar.multiselect("클래스 선택", options=classes, default=selected_classes, key="selected_classes")
        
        # 선택된 클래스들의 코드 입력 필드 표시
        class_codes = {}
        for class_name in selected_classes:
            class_codes[class_name] = st.text_area(f"{class_name} 코드 입력", key=f"class_code_{class_name}", height=50)
        
        # 저장 및 로드 버튼
        if st.sidebar.button("세션 상태 다운로드"):
            # 세션 상태를 일반 Python 딕셔너리로 변환
            session_state_dict = {
                "classes": classes,
                "selected_classes": selected_classes,
                **{f"class_code_{class_name}": code for class_name, code in class_codes.items()}
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