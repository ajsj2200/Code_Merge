import streamlit as st
from streamlit_tree_select import tree_select
import json
import base64
import pyperclip


class Node:
    def __init__(self, label, code="", children=None):
        self.label = label
        self.code = code
        self.children = children or []

    def add_child(self, node):
        self.children.append(node)

    def remove_child(self, label):
        self.children = [
            child for child in self.children if child.label != label]

    def to_dict(self):
        return {
            "label": self.label,
            "value": self.label,
            "code": self.code,  # 'code' 키 추가
            "children": [child.to_dict() for child in self.children]
        }


def load_prompts():
    try:
        comment_prompt = open("comment_prompt.txt", "r",
                              encoding="utf-8").read()
        system_prompt = open("system_prompt.txt", "r", encoding="utf-8").read()
        instruction_prompt = open("instruction_prompt.txt",
                                  "r", encoding="utf-8").read()
        return comment_prompt, system_prompt, instruction_prompt
    except FileNotFoundError:
        st.error("프롬프트 파일 중 하나 이상이 존재하지 않습니다.")
        return "", "", ""
    except Exception as e:
        st.error(f"프롬프트 파일을 읽는 중 오류가 발생했습니다: {str(e)}")
        return "", "", ""


def get_selected_code(nodes, selected_nodes):
    selected_codes = []
    for node_label in selected_nodes:
        node = find_node(nodes, node_label)
        if node:
            selected_codes.append(f"########################\n 클래스 이름 : {
                                  node.label} \n\n{node.code}")
    return "\n\n".join(selected_codes)


def display_selected_codes(nodes):
    selected_codes = []
    for node_label in nodes:
        node = find_node(st.session_state.nodes, node_label)
        if node:
            selected_codes.append(f"클래스 이름 : {node.label} \n\n{node.code}")
    if selected_codes:
        code_text = "\n\n".join(selected_codes)
        st.code(code_text, language="python")
    else:
        st.write("선택된 클래스가 없습니다.")


def download_json_file(nodes, file_name):
    try:
        nodes_data = [node.to_dict() for node in nodes]
        json_data = json.dumps(nodes_data, indent=2)
        b64 = base64.b64encode(json_data.encode("utf-8")).decode("utf-8")
        href = f'<a href="data:file/json;base64,{
            b64}" download="{file_name}">노드 구조 다운로드</a>'
        return href
    except Exception as e:
        st.error(f"JSON 파일 다운로드 중 오류가 발생했습니다: {str(e)}")
        return ""


def load_nodes_from_json(json_data):
    try:
        nodes_data = json.loads(json_data)
        nodes = []
        for node_data in nodes_data:
            node = load_node_from_dict(node_data)
            nodes.append(node)
        return nodes
    except json.JSONDecodeError:
        st.error("유효하지 않은 JSON 형식입니다.")
        return []
    except Exception as e:
        st.error(f"JSON 데이터 로드 중 오류가 발생했습니다: {str(e)}")
        return []


def load_node_from_dict(node_data):
    node = Node(node_data['label'], node_data.get('code', ''))
    for child_data in node_data.get('children', []):
        child_node = load_node_from_dict(child_data)
        node.add_child(child_node)
    return node


def extract_node_labels(nodes):
    labels = []
    for node in nodes:
        labels.append(node.label)
        labels.extend(extract_node_labels(node.children))
    return labels


def find_node(nodes, label):
    for node in nodes:
        if node.label == label:
            return node
        found_node = find_node(node.children, label)
        if found_node:
            return found_node
    return None


def remove_node(nodes, label):
    for i, node in enumerate(nodes):
        if node.label == label:
            nodes.pop(i)
            remove_expanded_node(label)
            remove_expanded_children(node)
            return True
        if remove_node(node.children, label):
            return True
    return False


def remove_expanded_node(label):
    if label in st.session_state.expanded_nodes:
        st.session_state.expanded_nodes.remove(label)


def remove_expanded_children(node):
    for child in node.children:
        remove_expanded_node(child.label)
        remove_expanded_children(child)


def extract_all_node_labels(nodes):
    labels = []
    for node in nodes:
        labels.append(node.label)
        labels.extend(extract_all_node_labels(node.children))
    return labels


def load_prompts():
    comment_prompt = open("comment prompt.txt", "r", encoding="utf-8").read()
    system_prompt = open("system prompt.txt", "r", encoding="utf-8").read()
    instruction_prompt = open("instruction prompt.txt",
                              "r", encoding="utf-8").read()
    return comment_prompt, system_prompt, instruction_prompt


def is_label_exists(nodes, label):
    if label in extract_node_labels(nodes):
        return True
    return False


def main():
    try:
        st.set_page_config(page_title="트리 기반 클래스 관리 시스템", layout="wide")
        st.title("트리 기반 클래스 관리")

        # 세션 상태 초기화
        if "nodes" not in st.session_state:
            st.session_state.nodes = [
                Node("START", "시작")
            ]

        # 확장된 노드 상태 초기화
        if "expanded_nodes" not in st.session_state:
            st.session_state.expanded_nodes = [
                node.label for node in st.session_state.nodes]

        # 사이드바 구성
        with st.sidebar:
            st.subheader("노드 관리")

            # 노드 추가 폼
            st.subheader("노드 추가")
            parent_label = st.selectbox(
                "부모 노드 선택", extract_node_labels(st.session_state.nodes))
            label = st.text_input("노드 레이블")
            code = st.text_area("코드 내용")
            if st.button("노드 추가"):
                if not is_label_exists(st.session_state.nodes, label):
                    parent_node = find_node(
                        st.session_state.nodes, parent_label)
                    if parent_node:
                        parent_node.add_child(Node(label, code))
                    else:
                        st.session_state.nodes.append(Node(label, code))
                    st.session_state.expanded_nodes.append(
                        label)  # 추가된 노드를 expanded_nodes에 추가
                else:
                    st.warning("중복된 노드 라벨입니다. 다른 라벨을 사용해주세요.")

            # 노드 수정 폼 추가
            st.subheader("노드 수정")
            edit_label = st.selectbox(
                "수정할 노드 선택", extract_node_labels(st.session_state.nodes))
            edit_node = find_node(st.session_state.nodes, edit_label)
            if edit_node:
                edit_code = st.text_area("코드 내용 수정", value=edit_node.code)
                if st.button("노드 수정"):
                    edit_node.code = edit_code
            else:
                st.warning("수정할 노드를 선택해주세요.")

            # 노드 삭제 폼
            st.subheader("노드 삭제")
            delete_label = st.selectbox(
                "삭제할 노드 선택", extract_node_labels(st.session_state.nodes))
            if st.button("노드 삭제"):
                if remove_node(st.session_state.nodes, delete_label):
                    st.session_state.expanded_nodes.remove(
                        delete_label)  # 삭제된 노드를 expanded_nodes에서 제거

            # 다운로드 및 업로드 폼
            st.subheader("다운로드 및 업로드")
            st.markdown(download_json_file(st.session_state.nodes,
                        "nodes.json"), unsafe_allow_html=True)

            uploaded_file = st.file_uploader("노드 구조 파일 업로드", type=["json"])
            st.write("파일 업로드하고나서 삭제할 것")
            if uploaded_file is not None:
                json_data = uploaded_file.read().decode("utf-8")
                st.session_state.nodes = load_nodes_from_json(json_data)
                st.session_state.expanded_nodes = [
                    node.label for node in st.session_state.nodes]
                # st.rerun()

        # 트리 선택 구성
        tree_result = tree_select(
            [node.to_dict() for node in st.session_state.nodes],
            check_model='all',
            show_expand_all=True,
            expanded=extract_all_node_labels(st.session_state.nodes),
            checked=st.session_state.expanded_nodes
        )

        # 프롬프트 로드
        comment_prompt, system_prompt, instruction_prompt = load_prompts()

        # 프롬프트 사용 여부 체크박스
        use_comment_prompt = st.checkbox("주석 프롬프트 사용")
        use_system_prompt = st.checkbox("시스템 프롬프트 사용")
        use_instruction_prompt = st.checkbox("명령 프롬프트 사용", value=True)

        # 선택된 노드 출력
        selected_nodes = tree_result.get('checked', [])
        st.subheader("선택된 클래스의 코드")

        # 요청 입력
        request = st.text_area("요청 입력", height=100)

        # 프롬프트 생성
        selected_code = get_selected_code(
            st.session_state.nodes, selected_nodes)
        prompt = f"{selected_code}\n\n"

        if use_comment_prompt:
            prompt += f"{comment_prompt}\n\n"

        if use_system_prompt:
            prompt = f"{system_prompt}\n\n" + prompt

        if use_instruction_prompt:
            prompt += f"[User Instruction]\n{instruction_prompt}\n\n"

        prompt += f"[요청: {request}]"

        # 프롬프트 출력
        if st.button('프롬프트 복사'):
            pyperclip.copy(prompt)
        if st.button('프롬프트 확인'):
            st.code(prompt, language="python")
    except Exception as e:
        st.error(f"예기치 않은 오류가 발생했습니다: {str(e)}")


if __name__ == "__main__":
    main()
