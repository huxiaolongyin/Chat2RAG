import io
import time
from typing import List

import pandas as pd
import streamlit as st
import streamlit_antd_components as sac
from controller.knowledge_controller import knowledge_controller
from dataclass.document import QADocument
from utils.initialize import initialize_page
from utils.sidebar import render_sidebar


def create_knowledge_template():
    """
    创建知识库模板
    """
    df = pd.DataFrame(
        {
            "问题": ["示例1：如何使用产品A?", "示例2：  产品B的价格是多少?"],
            "答案": ["产品A的使用步骤是...", "产品B的价格为999元"],
        }
    )
    buffer = io.BytesIO()
    df.to_excel(buffer, index=False)
    return buffer.getvalue()


def export_documents():
    doc_list, _ = knowledge_controller.get_documents(
        collection_name=st.session_state["collection_select"],
        current=st.session_state["current"],
        size=9999,
    )

    if not doc_list:
        return None

    question = []
    answer = []

    for item in doc_list:
        content = item["content"]
        try:
            q, a = content.split(": ", 1)  # 使用maxsplit=1确保只分割第一个冒号
            question.append(q)
            answer.append(a)
        except ValueError:
            question.append("")
            answer.append(content)

    df = pd.DataFrame(
        {
            "问题": question,
            "答案": answer,
        }
    )

    buffer = io.BytesIO()
    df.to_excel(buffer, index=False)
    buffer.seek(0)  # 重置buffer位置到开始

    return buffer


def process_uploaded_file(file) -> List[QADocument]:
    """
    处理上传的Excel文件
    """
    df = pd.read_excel(file, header=0)
    result = []
    for _, row in df.iterrows():
        question = row["问题"]
        answer = row["答案"]
        result.append(QADocument(question=question, answer=answer))

    return result


@st.dialog("确认删除知识", width="small")
def del_knowledge_dialog(data):
    """
    弹出删除确认窗口
    """
    st.write([item["content"] for item in data])
    data_id = [item["id"] for item in data]
    if st.button("确认删除", width="stretch", type="primary"):
        knowledge_controller.delete_documents(
            st.session_state["collection_select"], data_id
        )
        st.rerun()


# @st.dialog("确认删除知识库", width="small")
# def del_knowledge_store_dialog(name: str):
#     """
#     知识库删除确认窗口
#     """
#     st.write(f"知识库：{name}")
#     if st.button("确认删除", width='stretch', type="primary"):
#         knowledge_controller.del_collection(name)
#         st.rerun()


def get_documents_list():
    """
    获取知识库文档数据到session
    """
    st.session_state["doc_list"], st.session_state["doc_total"] = (
        knowledge_controller.get_documents(
            collection_name=st.session_state["collection_select"],
            current=st.session_state["current"],
            document_content=st.session_state["document_content"],
        )
    )
    st.session_state["current"] = 1


def render_knowledge_table():
    """
    渲染知识库表格
    """
    get_documents_list()

    data_with_select = [
        {"select": False, **item} for item in st.session_state["doc_list"]
    ]

    return st.data_editor(
        data_with_select,
        column_config={
            "select": st.column_config.CheckboxColumn(
                "选择", help="选择要操作的知识", width="small"
            ),
            "id": st.column_config.TextColumn("ID", width="small"),
            "content": st.column_config.TextColumn("内容", width="large"),
        },
        hide_index=True,
        width="stretch",
    )


def render_upload_section():
    """渲染上传区域"""
    st.markdown("---")
    st.markdown("### 上传知识")

    if "upload_complete" not in st.session_state:
        st.session_state.upload_complete = False

    st.download_button(
        "下载模板",
        data=create_knowledge_template(),
        file_name="知识库模板.xlsx",
        width="stretch",
        type="primary",
    )

    uploaded_file = st.file_uploader(
        "上传知识", type=["xlsx", "xls"], label_visibility="collapsed"
    )

    if uploaded_file:
        process_document_list = process_uploaded_file(uploaded_file)

        questions = [item.question for item in process_document_list]
        answers = [item.answer for item in process_document_list]

        # 转换为Series以便使用isna()检测
        questions_series = pd.Series(questions)
        answers_series = pd.Series(answers)

        if questions_series.isna().any() or "" in questions:
            st.error("问题列不能包含空值")
            return False

        if answers_series.isna().any() or "" in answers:
            st.error("答案列不能包含空值")
            return False

        process_df = pd.DataFrame(
            {
                "问题": questions,
                "答案": answers,
            }
        )
        st.dataframe(process_df, hide_index=True, width="stretch")
        st.markdown(f"知识总数：{len(process_df)}")

        progress_bar = st.progress(0)
        status_text = st.empty()

        def upload_with_progress():
            total_records = len(process_df)
            batch_size = 4

            # 计算总批次数
            total_batches = (total_records + batch_size - 1) // batch_size

            # 记录开始时间
            start_time = time.time()

            for batch_num in range(total_batches):
                # 计算当前批次的起止索引
                start_idx = batch_num * batch_size
                end_idx = min(start_idx + batch_size, total_records)

                # 获取当前批次数据
                batch_data = process_document_list[start_idx:end_idx]

                # 计算预计剩余时间
                if batch_num > 0:
                    elapsed_time = time.time() - start_time
                    avg_time_per_batch = elapsed_time / batch_num
                    remaining_batches = total_batches - batch_num
                    estimated_time = avg_time_per_batch * remaining_batches
                    time_str = f"预计还需 {estimated_time:.1f} 秒"
                else:
                    time_str = "计算预计时间..."

                # 更新进度
                progress = int((batch_num + 1) / total_batches * 100)
                progress_bar.progress(progress)
                status_text.text(
                    f"正在上传第{start_idx+1}-{end_idx}条数据... {progress}% | {time_str}"
                )

                # 上传当前批次
                knowledge_controller.add_document(
                    st.session_state["collection_select"], batch_data
                )

            total_time = time.time() - start_time
            progress_bar.progress(100)
            status_text.text(f"上传完成!共{total_records}条数据,耗时{total_time:.1f}秒")
            st.session_state.upload_complete = True

        cols = st.columns(3)
        with cols[1]:
            st.button(
                "确认上传",
                on_click=upload_with_progress,
                key="submit_knowledge",
                width="stretch",
                type="primary",
            )

        # 上传完成后自动刷新
        if st.session_state.upload_complete:
            st.session_state.upload_complete = False
            st.rerun()


def render_search_bar():
    col1, col2 = st.columns([4, 1])  # 优化列宽比例

    with col1:
        st.text_input(
            label="知识搜索",  # 移除重复的标签
            placeholder="输入关键词搜索知识库...",  # 更友好的提示文本
            key="document_content",
        )

    with col2:
        st.write("")
        st.button(
            "🔍 搜索",  # 添加图标提升视觉效果
            width="stretch",
            on_click=get_documents_list,
            type="primary",  # 使用主要按钮样式
        )


def main():
    """
    知识库管理页面
    """
    st.title(":material/auto_stories: 知识库管理")
    initialize_page()
    render_sidebar()
    render_search_bar()

    knowledge_table = render_knowledge_table()

    # 分页
    sac.pagination(
        st.session_state["doc_total"],
        page_size=10,
        align="center",
        show_total=True,
        key="current",
        on_change=get_documents_list,
    )

    # 删除选中知识
    delete_data = [item for item in knowledge_table if item["select"]]
    st.button(
        "删除选中知识",
        width="stretch",
        on_click=del_knowledge_dialog,
        args=(delete_data,),
    )

    if st.session_state["doc_list"]:
        st.download_button(
            "导出知识库",
            data=export_documents(),
            file_name=f"{st.session_state['collection_select']}.xlsx",
            width="stretch",
            type="primary",
        )
    render_upload_section()


main()
