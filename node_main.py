import streamlit as st
from streamlit_tree_select import tree_select


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
            "children": [child.to_dict() for child in self.children]
        }


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
            return True
        if remove_node(node.children, label):
            return True
    return False


def main():
    st.set_page_config(page_title="트리 기반 클래스 관리 시스템", layout="wide")
    st.title("트리 기반 클래스 관리")

    # 세션 상태 초기화
    if "nodes" not in st.session_state:
        st.session_state.nodes = [
            Node("클래스 A", "코드 내용 A"),
            Node("클래스 B", "코드 내용 B", [
                Node("하위 클래스 A", "하위 코드 내용 A"),
                Node("하위 클래스 B", "하위 코드 내용 B")
            ])
        ]

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
            parent_node = find_node(st.session_state.nodes, parent_label)
            if parent_node:
                parent_node.add_child(Node(label, code))
            else:
                st.session_state.nodes.append(Node(label, code))
            st.experimental_rerun()

        # 노드 삭제 폼
        st.subheader("노드 삭제")
        delete_label = st.selectbox(
            "삭제할 노드 선택", extract_node_labels(st.session_state.nodes))
        if st.button("노드 삭제"):
            if remove_node(st.session_state.nodes, delete_label):
                st.experimental_rerun()

    # 트리 선택 구성
    tree_result = tree_select(
        [node.to_dict() for node in st.session_state.nodes], check_model='all', show_expand_all=True, expanded=[node.to_dict() for node in st.session_state.nodes])

    # 선택된 노드 출력
    selected_nodes = tree_result.get('checked', [])
    if selected_nodes:
        st.subheader("선택된 클래스")
        for node_label in selected_nodes:
            node = find_node(st.session_state.nodes, node_label)
            if node:
                st.write(f"클래스 이름: {node.label}")
                st.code(node.code, language="python")
    else:
        st.write("선택된 클래스가 없습니다.")


if __name__ == "__main__":
    main()
