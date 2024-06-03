import threading
import time
import anthropic
import re
import pyperclip
import base64
import json
from streamlit_tree_select import tree_select
import streamlit as st
import os
import pathlib
import textwrap
import google.generativeai as genai
from google.api_core import retry
import concurrent.futures
import openai
from openai import AsyncOpenAI


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
            "label": self.get_label_with_icon(),
            "value": self.id,
            "code": self.code,
            "children": [child.to_dict() for child in self.children],
            "expand_disabled": self.is_leaf()
        }

    def is_leaf(self):
        return len(self.children) == 0

    def get_label_with_icon(self):
        file_extension_to_emoji = {
            '.py': '🐍',   # Python files
            '.cs': '🧩',   # C# files
            '.txt': '📄',  # Text files
            '.md': '📝',   # Markdown files
        }

        if os.path.isdir(self.id):
            return f"📁 {self.label}"
        else:
            if self.id.endswith('.Designer.cs'):
                return f"🎨 {self.label}"
            else:
                _, extension = os.path.splitext(self.id)
                return f"{file_extension_to_emoji.get(extension, '📄')} {self.label}"


def count_files_in_folder(path, allowed_extensions):
    count = 0
    for root, dirs, files in os.walk(path):
        for file in files:
            if os.path.splitext(file)[1] in allowed_extensions:
                count += 1
    return count


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


@st.cache_resource
def load_gemini_api_key(filepath):
    return pathlib.Path(filepath).read_text().strip()


@st.cache_resource
def load_favorite_directories(filepath="favorite_directories.txt"):
    try:
        with open(filepath, "r", encoding="utf-8") as file:
            directories = [line.strip()
                           for line in file.readlines() if line.strip()]
        return directories
    except FileNotFoundError:
        st.error("즐겨찾기 경로 파일이 존재하지 않습니다.")
        return []
    except Exception as e:
        st.error(f"즐겨찾기 경로 파일을 읽는 중 오류가 발생했습니다: {str(e)}")
        return []


def configure_genai(api_key):
    genai.configure(api_key=api_key)


def get_model(model_name):
    generation_config = {
        "temperature": 0.5,
        "top_p": 0.95,
        "top_k": 64,
        "max_output_tokens": 8192,
        "response_mime_type": "text/plain",
    }

    return genai.GenerativeModel(model_name=model_name, generation_config=generation_config)


def generate_markdown(model, context):
    prompt = f"""
    다음 지시사항을 엄격히 준수하여 주어진 텍스트를 Markdown 문서로 변환해 주세요:

    원본 텍스트의 내용을 절대로 변경하거나 추가, 삭제하지 마세요.

    단어, 문장, 단락 등 어떤 텍스트도 수정되어서는 안 됩니다.
    원본 텍스트의 의미와 메시지는 그대로 유지되어야 합니다.


    Markdown 문법을 사용하여 텍스트를 구조화하고 가독성을 높이세요.

    제목, 부제목, 목록, 인용구, 코드 블록 등 적절한 요소를 활용하세요.
    원본 텍스트의 구조와 흐름을 최대한 반영하도록 노력하세요.


    원본 텍스트 이외의 어떤 내용도 추가하지 마세요.

    설명, 해석, 의견 등 어떤 추가 정보도 포함해서는 안 됩니다.

    변환할 텍스트:
    {context}
    """
    response = model.generate_content(
        prompt, request_options={'retry': retry.Retry()})
    return response


def process_response(response):
    try:
        markdown_text = response.candidates[0].content.parts[0].text
        return markdown_text
    except KeyError:
        return ""


def display_markdown(markdown_text):
    display(Markdown(markdown_text))


def chunk_text(text, chunk_size=500, overlap_size=100):
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start = end - overlap_size
    return chunks


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


def write_file(file_path, content):
    try:
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(content)
    except Exception as e:
        print(f"Error writing to file: {file_path}")
        print(str(e))


def directory_to_tree(path, allowed_extensions=None, progress=None, processed_files=0, total_files=1):
    if allowed_extensions is None:
        allowed_extensions = ['.cs', '.py', '.txt', '.md']

    name = os.path.basename(path)
    if os.path.isdir(path):
        file_count = count_files_in_folder(path, allowed_extensions)
        name = f"{name} ({file_count}개 파일"  # 폴더 이름 뒤에 파일 개수 추가
    node = Node(name, id=path)

    if progress is None:
        total_files = count_files_in_directory(path, allowed_extensions)
        progress = st.progress(0)

    if os.path.isdir(path):
        children = os.listdir(path)
        folders = sorted(
            [child for child in children if os.path.isdir(os.path.join(path, child))])
        files = sorted(
            [child for child in children if not os.path.isdir(os.path.join(path, child))])
        sorted_children = folders + files  # 폴더가 파일보다 먼저 오도록 정렬

        for child in sorted_children:
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


@st.cache_resource
def load_openai_api_key():
    try:
        with open("openai_api_key.txt", "r") as file:
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
                    selected_codes.append(
                        f"########################\n 자료 이름 : {node.label} \n\n{file_content}")
            else:
                selected_codes.append(
                    f"########################\n 자료 이름 : {node.label} \n\n{node.code}")
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


def find_node_by_path(nodes, path):
    for node in nodes:
        if node.id == path:
            return node
        found_node = find_node_by_path(node.children, path)
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


def chunk_text(text, chunk_size=500, overlap_size=100):
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start = end - overlap_size
    return chunks


# 텍스트 길이에 따라 청크 크기를 자동으로 설정하는 함수 추가
def calculate_chunk_size(text_length, desired_chunks=6, overlap_size=100):
    if text_length <= 0 or desired_chunks <= 0:
        return 500  # 기본 청크 크기
    chunk_size = (text_length + (desired_chunks - 1)
                  * overlap_size) // desired_chunks
    return chunk_size


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


def process_column(client, model, messages):
    with st.chat_message("assistant"):
        stream = client.chat.completions.create(
            model=model,
            messages=[{"role": m["role"], "content": m["content"]}
                      for m in messages],
            stream=True,
        )
        response = st.write_stream(stream)
        return response


def main():
    try:
        st.set_page_config(page_title="트리 기반 자료 관리 시스템", layout="wide")
        st.title("트리 기반 자료 관리")

        if "nodes" not in st.session_state:
            st.session_state.nodes = [Node("START", "시작")]

        if "expanded_nodes" not in st.session_state:
            st.session_state.expanded_nodes = [
                node.id for node in st.session_state.nodes]

        favorite_directories = load_favorite_directories()

        with st.sidebar:
            st.subheader("즐겨찾기 경로")
            selected_favorite_directory = st.selectbox(
                "즐겨찾기 경로 선택", favorite_directories)
            if selected_favorite_directory:
                st.write(f"선택된 경로: {selected_favorite_directory}")

            # st.subheader("노드 관리")

            # st.subheader("노드 추가")
            node_labels_with_paths = extract_node_labels_with_paths(
                st.session_state.nodes)
            # parent_label = st.selectbox(
            #     "부모 노드 선택", [label for label, _ in node_labels_with_paths])
            # label = st.text_input("노드 레이블")
            # code = st.text_area("내용 내용")
            # if st.button("노드 추가"):
            #     if not is_label_exists(st.session_state.nodes, label):
            #         parent_path = next(
            #             path for label, path in node_labels_with_paths if label == parent_label)
            #         parent_node = find_node_by_path(
            #             st.session_state.nodes, parent_path)
            #         if parent_node:
            #             new_node = Node(label, code)
            #             parent_node.add_child(new_node)
            #             # .md 파일 생성
            #             file_path = os.path.join(parent_path, f"{label}.md")
            #             write_file(file_path, code)
            #             new_node.code = file_path
            #         else:
            #             new_node = Node(label, code)
            #             st.session_state.nodes.append(new_node)
            #             # .md 파일 생성
            #             file_path = f"{label}.md"
            #             write_file(file_path, code)
            #             new_node.code = file_path
            #         st.session_state.expanded_nodes.append(label)
            #     else:
            #         st.warning("중복된 노드 라벨입니다. 다른 라벨을 사용해주세요.")

            st.subheader("디렉토리 트리 추가")
            directory_path = st.text_input(
                "디렉토리 경로 입력", value=selected_favorite_directory)
            st_allowed_extensions = st.multiselect(
                "포함할 파일 확장자 선택", [".cs", ".py", ".txt", ".md"], default=[".cs", ".py", ".txt", ".md"])
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

            st.subheader("즐겨찾기 경로를 노드로 추가")
            if st.button("즐겨찾기 경로 노드 추가"):
                directory = selected_favorite_directory
                if os.path.exists(directory):
                    new_directory_node, _ = directory_to_tree(
                        directory, st_allowed_extensions)
                    st.session_state.nodes.append(new_directory_node)
                    st.session_state.expanded_nodes.append(
                        new_directory_node.id)
                else:
                    st.error(f"디렉토리 경로가 존재하지 않습니다: {directory}")
                st.rerun()

            if st.button("즐겨찾기 모든 경로 노드 추가"):
                for directory in favorite_directories:
                    if os.path.exists(directory):
                        new_directory_node, _ = directory_to_tree(
                            directory, st_allowed_extensions)
                        st.session_state.nodes.append(new_directory_node)
                        st.session_state.expanded_nodes.append(
                            new_directory_node.id)
                    else:
                        st.error(f"디렉토리 경로가 존재하지 않습니다: {directory}")
                st.rerun()

            # st.subheader("노드 수정")
            # edit_label = st.selectbox(
            #     "수정할 노드 선택", [label for label, _ in node_labels_with_paths])
            # edit_path = next(
            #     path for label, path in node_labels_with_paths if label == edit_label)
            # edit_node = find_node_by_path(st.session_state.nodes, edit_path)
            # if edit_node:
            #     edit_code = st.text_area("내용 내용 수정", value=edit_node.code)
            #     if st.button("노드 수정"):
            #         edit_node.code = edit_code
            #         # .md 파일 내용 수정
            #         if os.path.exists(edit_node.code):
            #             write_file(edit_node.code, edit_code)
            # else:
            #     st.warning("수정할 노드를 선택해주세요.")

            # st.subheader("노드 삭제")
            # delete_label = st.selectbox(
            #     "삭제할 노드 선택", [label for label, _ in node_labels_with_paths])
            # delete_path = next(
            #     path for label, path in node_labels_with_paths if label == delete_label)
            # if st.button("노드 삭제"):
            #     if remove_node(st.session_state.nodes, delete_path):
            #         st.session_state.expanded_nodes.remove(delete_path)

            # st.subheader("다운로드 및 업로드")
            # st.markdown(download_json_file(st.session_state.nodes,
            #             "nodes.json"), unsafe_allow_html=True)

            # uploaded_file = st.file_uploader("노드 구조 파일 업로드", type=["json"])
            # if uploaded_file is not None:
            #     json_data = uploaded_file.read().decode("utf-8")
            #     st.session_state.nodes = load_nodes_from_json(json_data)
            #     st.session_state.expanded_nodes = [
            #         node.id for node in st.session_state.nodes]

        if "checked_nodes" not in st.session_state:
            st.session_state.checked_nodes = []
        if "expanded_nodes" not in st.session_state:
            st.session_state.expanded_nodes = []

        tree_result = tree_select(
            [node.to_dict() for node in st.session_state.nodes],
            check_model='all',
            show_expand_all=False,
            expand_disabled=False,
            expanded=st.session_state.expanded_nodes,  # 추가 부분
            checked=st.session_state.checked_nodes  # 추가 부분
        )

        st.session_state.checked_nodes = tree_result.get('checked', [])
        st.session_state.expanded_nodes = tree_result.get('expanded', [])

        # st.code([node.to_dict() for node in st.session_state.nodes])
        prompts = load_prompts()

        selected_nodes = tree_result.get('checked', [])
        st.subheader("선택된 자료의 내용")

        # selected_nodes중 폴더가 아닌 파일만 선택하도록 함
        # \ 로 구분하고 마지막 조각에 .이 있으면 파일로 결정
        # 파일만 선택하는 함수
        def select_files(nodes):
            files = []
            for node in nodes:
                # \로 경로 구분
                parts = node.split("\\")
                # 마지막 조각에 .이 있으면 파일로 간주
                if "." in parts[-1]:
                    files.append(parts[-1])
            return files

        st.write(select_files(selected_nodes))

        request = st.text_area("요청 입력", height=100)

        global selected_code
        selected_code = get_selected_code(selected_nodes)
        prompt = f"{selected_code}\n\n"

        # 요청 프롬프트 앞에 선택하게 하는 부분 추가
        st.subheader("요청 프롬프트 앞에 위치시킬 노드를 선택하세요")
        selected_specific_node_label = st.selectbox(
            "특정 노드 선택", [label for label, _ in node_labels_with_paths])
        specific_node_path = next(
            path for label, path in node_labels_with_paths if label == selected_specific_node_label)
        specific_node = find_node_by_path(
            st.session_state.nodes, specific_node_path)

        specific_node_content = ""
        if specific_node:
            if os.path.exists(specific_node.code):
                specific_node_content = read_file(specific_node.code)
            else:
                specific_node_content = specific_node.code

        for prompt_name, prompt_content in prompts.items():
            use_prompt = st.checkbox(f"{prompt_name} 사용")
            if use_prompt:
                prompt += f"{prompt_content}\n\n"

        prompt += f"[요청: {request}]\n\n"

        # 특정 노드 내용을 마지막에 추가
        prompt += f"########################\n 자료 이름 : {
            specific_node.label} \n\n{specific_node_content}"

        st.session_state['prompt'] = prompt
        if st.button('프롬프트 복사'):
            pyperclip.copy(prompt)
        if st.button('프롬프트 확인'):
            st.code(prompt, language="python")

        tab1, tab2, tab3, tab4, tab5 = st.tabs(
            ["선택된 자료", "메타프롬프트 생성", "프롬프트 향상", "텍스트 변환", "다중 채팅"])
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

        with tab4:
            st.write("텍스트 정리")
            text_to_convert = st.text_area("변환할 텍스트 입력", height=200)

            # 텍스트 길이에 따른 청크 크기 자동 계산
            if text_to_convert:
                default_chunk_size = calculate_chunk_size(len(text_to_convert))
            else:
                default_chunk_size = 1000

            # 슬라이더를 사용하여 청크 크기와 오버랩 크기를 설정할 수 있도록 함
            max_chunk_size = 8000
            if default_chunk_size > max_chunk_size:
                default_chunk_size = max_chunk_size
            chunk_size = st.slider(
                "청크 크기", min_value=100, max_value=max_chunk_size, value=default_chunk_size, step=1000)
            over_lap_size = st.slider(
                "오버랩 크기", min_value=0, max_value=500, value=100, step=10)

            # 텍스트 길이 표시
            if text_to_convert:
                st.write(f"텍스트 길이: {len(text_to_convert)}")
                # 청크 개수
                chunks = chunk_text(
                    text_to_convert, chunk_size=chunk_size, overlap_size=over_lap_size)
                st.write(f"청크 개수: {len(chunks)}")

            if st.button("텍스트 정리"):
                api_key_filepath = 'gemini_api_key.txt'
                model_name = 'models/gemini-1.5-flash-latest'
                api_key = load_gemini_api_key(api_key_filepath)
                configure_genai(api_key)
                model = get_model(model_name)

                chunks = chunk_text(
                    text_to_convert, chunk_size=chunk_size, overlap_size=over_lap_size)
                max_concurrent_requests = 15

                progress_bar = st.progress(0)
                total_chunks = len(chunks)
                processed_chunks = 0

                with st.spinner(f"텍스트 정리 중..."):
                    with concurrent.futures.ThreadPoolExecutor(max_workers=max_concurrent_requests) as executor:
                        futures = []
                        for i, chunk in enumerate(chunks):
                            futures.append(
                                (i, executor.submit(generate_markdown, model, chunk)))
                            if (i + 1) % max_concurrent_requests == 0:
                                for index, future in futures:
                                    response = future.result()
                                    markdown_text = process_response(response)
                                    chunks[index] = markdown_text
                                    processed_chunks += 1
                                    progress_bar.progress(
                                        processed_chunks / total_chunks)
                                futures = []

                        # 남은 청크 처리
                        for index, future in futures:
                            response = future.result()
                            markdown_text = process_response(response)
                            chunks[index] = markdown_text
                            processed_chunks += 1
                            progress_bar.progress(
                                processed_chunks / total_chunks)

                    markdown_result = "\n\n".join(chunks)
                    inner_tab1, inner_tab2 = st.tabs(["코드", "마크다운"])
                    with inner_tab1:
                        st.code(markdown_result)
                    with inner_tab2:
                        st.markdown(markdown_result)

                    b64 = base64.b64encode(markdown_result.encode()).decode()
                    href = f'<a href="data:file/markdown;base64,{
                        b64}" download="markdown_result.md">마크다운 결과 다운로드</a>'
                    st.markdown(href, unsafe_allow_html=True)

        with tab5:
            # 프롬프트를 복수 개의 API에 전달하여 결과를 비교하는 기능 추가
            # text 로드
            openapi_key = load_openai_api_key()
            client = openai.Client(api_key=openapi_key)
            st.session_state['openai_model'] = "gpt-4o"

            st.session_state.messages = []

            st.session_state.messages.append(
                {"role": "user", "content": prompt})

            def process_column():
                with st.chat_message("assistant"):
                    stream = client.chat.completions.create(
                        model=st.session_state["openai_model"],
                        messages=[
                            {"role": m["role"], "content": m["content"]}
                            for m in st.session_state.messages
                        ],
                        stream=True,
                    )
                    response = st.write_stream(stream)
            number_of_tabs = st.slider("탭 수", 1, 4, 2)

            chat_tabs = st.tabs([f"탭 {i+1}" for i in range(number_of_tabs)])
            if st.button("전송"):
                for i in range(number_of_tabs):
                    with chat_tabs[i]:
                        process_column()

    except Exception as e:
        st.error(f"예기치 않은 오류가 발생했습니다: {str(e)}")


if __name__ == "__main__":
    main()
