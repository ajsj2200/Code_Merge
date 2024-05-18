import os
import streamlit as st
from streamlit_tree_select import tree_select
import json
import base64
import pyperclip
import re
import anthropic
import time


class Node:
    def __init__(self, label, code="", children=None, id=None):
        self.label = label
        self.code = code
        self.children = children or []
        self.id = id or label

    def add_child(self, node):
        self.children.append(node)

    def remove_child(self, label):
        self.children = [
            child for child in self.children if child.label != label]

    def to_dict(self):
        return {
            "label": self.label,
            "value": self.id,
            "code": self.code,
            "children": [child.to_dict() for child in self.children]
        }


def count_files_in_directory(path, allowed_extensions):
    total_files = 0
    for root, dirs, files in os.walk(path):
        for file in files:
            if os.path.splitext(file)[1] in allowed_extensions:
                total_files += 1
    return total_files


def read_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    except Exception as e:
        print(f"Error reading file: {file_path}")
        print(str(e))
        return None


def directory_to_tree(path, allowed_extensions=None, progress=None, processed_files=0, total_files=1):
    if allowed_extensions is None:
        allowed_extensions = ['.cs', '.py', '.txt', '.md']

    name = os.path.basename(path)
    node = Node(name, id=path)

    if progress is None:
        total_files = count_files_in_directory(path, allowed_extensions)
        progress = st.progress(0)

    if os.path.isdir(path):
        for child in os.listdir(path):
            child_path = os.path.join(path, child)
            try:
                child_node, processed_files = directory_to_tree(
                    child_path, allowed_extensions, progress, processed_files, total_files)
                if child_node.children or child_node.code:
                    node.add_child(child_node)
            except Exception as e:
                print(f"Error processing child node: {child_path}")
                print(str(e))
    else:
        file_extension = os.path.splitext(path)[1]
        if file_extension in allowed_extensions:
            node.code = path  # 파일 경로만 저장
            processed_files += 1
            progress.progress(processed_files / total_files)

    # 다 끝나면 progress bar 제거
    if processed_files == total_files:
        progress.empty()

    return node, processed_files


@st.cache_resource
def load_prompts():
    prompts = {}
    prompts_folder = "prompts"
    if not os.path.exists(prompts_folder):
        st.error(f"프롬프트 폴더 '{prompts_folder}'가 존재하지 않습니다.")
        return prompts

    for filename in os.listdir(prompts_folder):
        if filename.endswith(".txt"):
            filepath = os.path.join(prompts_folder, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as file:
                    prompts[filename] = file.read()
            except FileNotFoundError:
                st.error(f"{filepath} 파일이 존재하지 않습니다.")
                prompts[filename] = ""
            except Exception as e:
                st.error(f"{filepath} 파일을 읽는 중 오류가 발생했습니다: {str(e)}")
                prompts[filename] = ""

    return prompts


@st.cache_resource
def load_api_key():
    try:
        with open("api_key.txt", "r") as file:
            api_key = file.read().strip()
        return api_key
    except FileNotFoundError:
        st.error("API 키 파일이 존재하지 않습니다.")
        return ""
    except Exception as e:
        st.error(f"API 키 파일을 읽는 중 오류가 발생했습니다: {str(e)}")
        return ""


def get_selected_code(selected_nodes):
    selected_codes = []
    for node_label in selected_nodes:
        node = find_node(st.session_state.nodes, node_label)
        if node:
            if os.path.exists(node.code):  # 파일 경로가 유효한지 확인
                file_content = read_file(node.code)
                if file_content:
                    selected_codes.append(f"########################\n 자료 이름 : {
                                          node.label} \n\n{file_content}")
            else:
                selected_codes.append(f"########################\n 자료 이름 : {
                                      node.label} \n\n{node.code}")
    return "\n\n".join(selected_codes)


def display_selected_codes(nodes):
    selected_codes = []
    for node_label in nodes:
        node = find_node(st.session_state.nodes, node_label)
        if node:
            if os.path.exists(node.code):  # 파일 경로가 유효한지 확인
                file_content = read_file(node.code)
                if file_content:
                    selected_codes.append(
                        f"자료 이름 : {node.label} \n\n{file_content}")
            else:
                selected_codes.append(f"자료 이름 : {node.label} \n\n{node.code}")
    if selected_codes:
        code_text = "\n\n".join(selected_codes)
        st.text_area("선택된 자료의 내용", code_text, height=500)
    else:
        st.write("선택된 자료가 없습니다.")


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
    node = Node(node_data['label'], node_data.get(
        'code', ''), id=node_data.get('value', node_data['label']))
    for child_data in node_data.get('children', []):
        child_node = load_node_from_dict(child_data)
        node.add_child(child_node)
    return node


def extract_node_labels_with_paths(nodes):
    labels = []
    for node in nodes:
        labels.append((os.path.basename(node.id), node.id))
        labels.extend(extract_node_labels_with_paths(node.children))
    return labels


def find_node(nodes, id):
    for node in nodes:
        if node.id == id:
            return node
        found_node = find_node(node.children, id)
        if found_node:
            return found_node
    return None


def remove_node(nodes, id):
    for i, node in enumerate(nodes):
        if node.id == id:
            nodes.pop(i)
            remove_expanded_node(id)
            remove_expanded_children(node)
            return True
        if remove_node(node.children, id):
            return True
    return False


def remove_expanded_node(id):
    if id in st.session_state.expanded_nodes:
        st.session_state.expanded_nodes.remove(id)


def remove_expanded_children(node):
    for child in node.children:
        remove_expanded_node(child.id)
        remove_expanded_children(child)


def extract_all_node_labels(nodes):
    labels = []
    for node in nodes:
        labels.append(node.id)
        labels.extend(extract_all_node_labels(node.children))
    return labels


def is_label_exists(nodes, label):
    if label in extract_node_labels(nodes):
        return True
    return False


def find_node_by_path(nodes, path):
    for node in nodes:
        if node.id == path:
            return node
        found_node = find_node_by_path(node.children, path)
        if found_node:
            return found_node
    return None


def make_metaprompt(request):
    ANTHROPIC_API_KEY = load_api_key()
    MODEL_NAME = "claude-3-opus-20240229"
    CLIENT = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    metaprompt = open("meta_prompt.txt", "r", encoding="utf-8").read()
    TASK = request
    VARIABLES = ["CODE", "REQUEST"]

    variable_string = ""
    for variable in VARIABLES:
        variable_string += "\n{$" + variable.upper() + "}"

    prompt = metaprompt.replace("{{TASK}}", TASK)
    assistant_partial = "<Inputs>"
    if variable_string:
        assistant_partial += variable_string + "\n</Inputs>\n<Instructions Structure>"

    st.subheader("메타프롬프트 생성")
    st.write("아래 프롬프트를 사용하여 ChatGPT나 Claude와 대화를 진행하고, 결과를 복사하여 아래 텍스트 영역에 붙여넣으세요.")
    st.code(prompt + "\n" + assistant_partial, language="text")

    message = st.text_area("ChatGPT 또는 Claude 출력 결과를 붙여넣으세요.")
    if st.button('코드만 복사'):
        global selected_code
        pyperclip.copy(selected_code)
    if message.strip() != "":
        extracted_prompt_template = extract_prompt(message)
        variables = extract_variables(message)

        remove_floating_variables_prompt = open(
            "remove_floating_variables_prompt.txt", "r", encoding="utf-8").read()

        floating_variables = find_free_floating_variables(
            extracted_prompt_template)

        st.write(floating_variables)
        if st.button('프롬프트'):
            if len(floating_variables) > 0:
                extracted_prompt_template_old = extracted_prompt_template
                extracted_prompt_template_new = remove_inapt_floating_variables(
                    extracted_prompt_template, CLIENT, MODEL_NAME, remove_floating_variables_prompt)
                st.write("새로운 프롬프트 템플릿:")
                st.code(extracted_prompt_template_new, language="text")

        variable_values = {}
        for variable in variables:
            variable_values[variable] = st.text_area(
                f"변수 '{variable}'의 값을 입력하세요.")

        prompt_with_variables = extracted_prompt_template
        for variable in variable_values:
            prompt_with_variables = prompt_with_variables.replace(
                "{" + variable + "}", variable_values[variable])

        st.subheader("최종 프롬프트")
        if st.button('복사'):
            pyperclip.copy(prompt_with_variables + '한국어로 답변합니다.')
        st.write("위의 프롬프트를 사용하여 ChatGPT나 Claude와 대화를 진행하세요.")


def main():
    try:
        st.set_page_config(page_title="트리 기반 자료 관리 시스템", layout="wide")
        st.title("트리 기반 자료 관리")

        if "nodes" not in st.session_state:
            st.session_state.nodes = [Node("START", "시작")]

        if "expanded_nodes" not in st.session_state:
            st.session_state.expanded_nodes = [
                node.id for node in st.session_state.nodes]

        with st.sidebar:
            st.subheader("노드 관리")

            st.subheader("노드 추가")
            node_labels_with_paths = extract_node_labels_with_paths(
                st.session_state.nodes)
            parent_label = st.selectbox(
                "부모 노드 선택", [label for label, _ in node_labels_with_paths])
            label = st.text_input("노드 레이블")
            code = st.text_area("내용 내용")
            if st.button("노드 추가"):
                if not is_label_exists(st.session_state.nodes, label):
                    parent_path = next(
                        path for label, path in node_labels_with_paths if label == parent_label)
                    parent_node = find_node_by_path(
                        st.session_state.nodes, parent_path)
                    if parent_node:
                        parent_node.add_child(Node(label, code))
                    else:
                        st.session_state.nodes.append(Node(label, code))
                    st.session_state.expanded_nodes.append(label)
                else:
                    st.warning("중복된 노드 라벨입니다. 다른 라벨을 사용해주세요.")

            st.subheader("디렉토리 트리 추가")
            directory_path = st.text_input("디렉토리 경로 입력")
            st_allowed_extensions = st.multiselect(
                "포함할 파일 확장자 선택", [".cs", ".py", ".txt", "hwp", "csv", "pdf", ".md"], default=[".cs", ".py", ".txt"])
            if st.button("디렉토리 트리 추가"):
                if os.path.exists(directory_path):
                    # 디렉토리 경로와 일치하는 노드를 찾아서 삭제
                    nodes_to_remove = [
                        node for node in st.session_state.nodes if node.id.startswith(directory_path)]
                    for node in nodes_to_remove:
                        remove_node(st.session_state.nodes, node.id)

                    # 새롭게 디렉토리 트리를 추가
                    new_directory_node, _ = directory_to_tree(
                        directory_path, st_allowed_extensions)
                    st.session_state.nodes.append(new_directory_node)
                    st.session_state.expanded_nodes.append(
                        new_directory_node.id)
                else:
                    st.error("디렉토리 경로가 존재하지 않습니다.")

            st.subheader("노드 수정")
            edit_label = st.selectbox(
                "수정할 노드 선택", [label for label, _ in node_labels_with_paths])
            edit_path = next(
                path for label, path in node_labels_with_paths if label == edit_label)
            edit_node = find_node_by_path(st.session_state.nodes, edit_path)
            if edit_node:
                edit_code = st.text_area("내용 내용 수정", value=edit_node.code)
                if st.button("노드 수정"):
                    edit_node.code = edit_code
            else:
                st.warning("수정할 노드를 선택해주세요.")

            st.subheader("노드 삭제")
            delete_label = st.selectbox(
                "삭제할 노드 선택", [label for label, _ in node_labels_with_paths])
            delete_path = next(
                path for label, path in node_labels_with_paths if label == delete_label)
            if st.button("노드 삭제"):
                if remove_node(st.session_state.nodes, delete_path):
                    st.session_state.expanded_nodes.remove(delete_path)

            st.subheader("다운로드 및 업로드")
            st.markdown(download_json_file(st.session_state.nodes,
                                           "nodes.json"), unsafe_allow_html=True)

            uploaded_file = st.file_uploader("노드 구조 파일 업로드", type=["json"])
            if uploaded_file is not None:
                json_data = uploaded_file.read().decode("utf-8")
                st.session_state.nodes = load_nodes_from_json(json_data)
                st.session_state.expanded_nodes = [
                    node.id for node in st.session_state.nodes]

        tree_result = tree_select(
            [node.to_dict() for node in st.session_state.nodes],
            check_model='all',
            show_expand_all=True,
            # 처음 노드의 1단계만 열림
            # expanded=[st.session_state.nodes[0].label],
            # expanded=extract_all_node_labels(st.session_state.nodes),
            # checked=st.session_state.expanded_nodes
        )

        prompts = load_prompts()

        selected_nodes = tree_result.get('checked', [])
        st.subheader("선택된 자료의 내용")

        request = st.text_area("요청 입력", height=100)

        global selected_code
        selected_code = get_selected_code(selected_nodes)
        prompt = f"{selected_code}\n\n"

        for prompt_name, prompt_content in prompts.items():
            use_prompt = st.checkbox(f"{prompt_name} 사용")
            if use_prompt:
                prompt += f"{prompt_content}\n\n"

        prompt += f"[요청: {request}]"

        if st.button('프롬프트 복사'):
            pyperclip.copy(prompt)
        if st.button('프롬프트 확인'):
            st.code(prompt, language="python")

        tab1, tab2, tab3 = st.tabs(["선택된 자료", "메타프롬프트 생성", "프롬프트 향상"])
        with tab1:
            display_selected_codes(selected_nodes)
        with tab2:
            make_metaprompt(request)

        with tab3:
            st.write("프롬프트 향상")
            user_prompt = st.text_area("프롬프트 입력", height=100)

            ANTHROPIC_API_KEY = load_api_key()
            MODEL_NAME = "claude-3-sonnet-20240229"
            CLIENT = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

            if st.button("프롬프트 향상"):
                improve_prompt = open(
                    "prompt_improvement.txt", "r", encoding="utf-8").read()
                message = CLIENT.messages.create(
                    model=MODEL_NAME,
                    messages=[{'role': "user", "content": improve_prompt.replace(
                        "{$REQUEST}", user_prompt)}],
                    max_tokens=4096,
                    temperature=0
                ).content[0].text
                st.write(message)
                pyperclip.copy(message)

    except Exception as e:
        st.error(f"예기치 않은 오류가 발생했습니다: {str(e)}")


if __name__ == "__main__":
    main()
