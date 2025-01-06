import io
import time

import pandas as pd
import streamlit as st
import streamlit_antd_components as sac
from controller.knowledge_controller import knowledge_controller
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


def process_uploaded_file(file) -> pd.Series:
    """
    处理上传的Excel文件
    """
    df = pd.read_excel(file, header=0)
    return df.apply(lambda row: f"{row['问题']}: {row['答案']}", axis=1)


@st.dialog("确认删除知识", width="small")
def del_knowledge_dialog(collection, data):
    """
    弹出删除确认窗口
    """
    st.write([item["content"] for item in data])
    data_id = [item["id"] for item in data]
    if st.button("确认删除", use_container_width=True, type="primary"):
        knowledge_controller.delete_documents(collection, data_id)
        st.rerun()


@st.dialog("确认删除知识库", width="small")
def del_knowledge_store_dialog(name: str):
    """
    知识库删除确认窗口
    """
    st.write(f"知识库：{name}")
    if st.button("确认删除", use_container_width=True, type="primary"):
        knowledge_controller.del_collection(name)
        st.rerun()


def get_knowledge_doc(collection_name: str):
    """
    获取知识库文档数据到session
    """
    if "current" not in st.session_state:
        st.session_state.current = 1
    result = knowledge_controller.get_documents(
        collection_name,
        current=st.session_state.current,
    )
    st.session_state.doc_list, st.session_state.doc_total = result


def render_knowledge_table(collection: str):
    """渲染知识库表格"""
    get_knowledge_doc(collection)
    data_with_select = [{"select": False, **item} for item in st.session_state.doc_list]

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
        use_container_width=True,
    )


def render_upload_section(collection: str):
    """渲染上传区域"""
    st.markdown("---")
    st.markdown("### 上传知识")

    if "upload_complete" not in st.session_state:
        st.session_state.upload_complete = False

    st.download_button(
        "下载模板",
        data=create_knowledge_template(),
        file_name="知识库模板.xlsx",
        use_container_width=True,
        type="primary",
    )

    uploaded_file = st.file_uploader(
        "上传知识", type=["xlsx", "xls"], label_visibility="collapsed"
    )

    if uploaded_file:
        process_df = process_uploaded_file(uploaded_file)
        st.dataframe(process_df, hide_index=True, use_container_width=True)
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
                batch_data = process_df[start_idx:end_idx].tolist()

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
                knowledge_controller.add_document(collection, batch_data)

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
                use_container_width=True,
                type="primary",
            )

        # 上传完成后自动刷新
        if st.session_state.upload_complete:
            st.session_state.upload_complete = False
            st.rerun()


def main():
    """
    知识库管理页面
    """
    st.title(":material/auto_stories: 知识库管理")
    initialize_page()

    render_sidebar()

    knowledge_table = render_knowledge_table(st.session_state.collection_select)

    # 分页
    sac.pagination(
        st.session_state.doc_total,
        page_size=10,
        align="center",
        show_total=True,
        key="current",
        on_change=get_knowledge_doc,
        args=(st.session_state.collection_select),
    )

    # 删除选中知识
    delete_data = [item for item in knowledge_table if item["select"]]
    st.button(
        "删除选中知识",
        use_container_width=True,
        on_click=del_knowledge_dialog,
        args=(
            st.session_state.collection_select,
            delete_data,
        ),
    )
    render_upload_section(st.session_state.collection_select)


main()

# data_with_select = [{"select": False, **item} for item in st.session_state.doc_list]
# knowledge_control = st.data_editor(
#     data_with_select,
#     column_config={
#         "select": st.column_config.CheckboxColumn(
#             "选择",
#             help="选择要操作的知识",
#             default=False,
#         ),
#         "id": st.column_config.TextColumn("ID", width="small"),
#         "content": st.column_config.TextColumn("内容"),
#     },
#     hide_index=True,
#     use_container_width=True,
# )


# st.markdown("---")
# st.markdown("### 上传知识库")


# st.download_button(
#     "下载模板",
#     data=create_template(),
#     file_name="知识库模板.xlsx",
#     use_container_width=True,
#     type="primary",
# )

# uploader_file = st.file_uploader(
#     "上传知识库", type=["xlsx", "xls"], label_visibility="collapsed"
# )
# if uploader_file:
#     df = pd.read_excel(uploader_file, header=0)
#     process_df = df.apply(lambda row: ":".join([row["问题"], row["答案"]]), axis=1)
#     st.dataframe(process_df, hide_index=True, use_container_width=True)
#     st.markdown(f"知识总数：{len(process_df)}")
#     upload_columns = st.columns(3)
#     with upload_columns[1]:
#         submit_button = st.button(
#             "确认上传",
#             on_click=knowledge_controller.add_document,
#             args=(
#                 collection,
#                 process_df.tolist(),
#             ),
#             key="submit_knowledge",
#             use_container_width=True,
#             type="primary",
#         )
