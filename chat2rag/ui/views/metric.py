from datetime import datetime, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st
from controller.metric_controller import metric_controller
from utils.initialize import initialize_page
from utils.sidebar import render_sidebar


def render_metrics_filters():
    """渲染指标过滤器"""

    col1, col2, col3, col4, col5 = st.columns(5)

    # 时间范围选择
    with col1:
        start_date = st.date_input(
            "开始日期",
            datetime.strptime(st.session_state.metric_start_date, "%Y-%m-%d"),
            key="metric_start_date_input",
        )
        st.session_state.metric_start_date = start_date.strftime("%Y-%m-%d")

    with col2:
        end_date = st.date_input(
            "结束日期",
            datetime.strptime(st.session_state.metric_end_date, "%Y-%m-%d"),
            key="metric_end_date_input",
        )
        st.session_state.metric_end_date = end_date.strftime("%Y-%m-%d")

    with col3:
        current_page = st.number_input(
            "页码",
            min_value=1,
            value=st.session_state.metric_current_page,
            step=1,
            key="metric_page_input",
        )
        st.session_state.metric_current_page = current_page

    with col4:
        page_size = st.selectbox(
            "每页显示",
            options=[10, 20, 50, 100, 9999],
            index=[10, 20, 50, 100, 9999].index(st.session_state.metric_page_size),
            key="metric_size_input",
        )
        st.session_state.metric_page_size = page_size
    with col5:
        options = [""]
        options.extend(st.session_state.collections_list)
        st.selectbox(
            "场景查询",
            options=options,
            key="collection_metric_select",
        )

    # 查询按钮
    if st.button("查询", width="stretch", type="primary"):
        st.session_state.metrics_data = load_metrics_data()
        st.rerun()


def load_metrics_data():
    """加载指标数据"""
    return metric_controller.get_metric_list(
        current=st.session_state.metric_current_page,
        size=st.session_state.metric_page_size,
        start_time=st.session_state.metric_start_date,
        end_time=st.session_state.metric_end_date,
        collection=st.session_state.collection_metric_select,
    )


def format_response_time(ms):
    """格式化响应时间"""
    if ms is None:
        return "N/A"
    if ms < 1000:
        return f"{ms:.2f}ms"
    else:
        return f"{ms/1000:.2f}s"


def render_metrics_table(metrics):
    """渲染指标数据表格"""
    if not metrics:
        st.info("没有找到匹配的数据")
        return

    # 将数据转换为DataFrame以便更好地显示
    df = pd.DataFrame(metrics)

    # 格式化响应时间
    if "firstResponseMs" in df.columns:
        df["firstResponseMs"] = df["firstResponseMs"].apply(format_response_time)
    if "totalMs" in df.columns:
        df["totalMs"] = df["totalMs"].apply(format_response_time)

    # 重命名列以便更好地显示
    column_map = {
        "collections": "场景",
        "prompt": "提示词",
        "question": "问题",
        "answer": "回答",
        "firstResponseMs": "首次响应时间 (ms)",
        "totalMs": "总响应时间 (ms)",
        "model": "模型",
        "chatId": "对话ID",
        "chatRounds": "对话轮次",
        "tools": "工具调用",
        "precisionMode": "精准模式",
        "createTime": "创建时间",
    }

    df = df.rename(columns=column_map)
    ordered_columns = [v for k, v in column_map.items() if v in df.columns]
    df = df[ordered_columns]

    # 显示数据表格
    st.dataframe(
        df,
        column_config={
            "问题": st.column_config.TextColumn(
                "问题",
                width="medium",
            ),
            "回答": st.column_config.TextColumn(
                "回答",
                width="large",
            ),
        },
        width="stretch",
        hide_index=True,
    )


def render_metrics_stats(metrics):
    """渲染指标统计图表"""

    df = pd.DataFrame(metrics)
    if not metrics or len(metrics) == 0:
        st.text("暂无数据")
        return

    tab1, tab2, tab3, tab4 = st.tabs(
        ["对话历史", "场景分布", "响应时间分析", "模型分布"]
    )
    with tab1:
        render_metrics_table(metrics)

    # 场景分布
    with tab2:
        if "collections" in df.columns:
            model_counts = df["collections"].value_counts().reset_index()
            model_counts.columns = ["collections", "count"]

            fig = px.pie(
                model_counts, values="count", names="collections", title="场景分布"
            )
            st.plotly_chart(fig, config={"width": "stretch"})

    # 响应时间分析
    with tab3:
        if "totalMs" in df.columns and "createTime" in df.columns:
            # 确保时间格式正确
            df["createTime"] = pd.to_datetime(df["createTime"])

            # 按时间排序
            df = df.sort_values("createTime")

            # 创建折线图
            fig = px.line(
                df,
                x="createTime",
                y="firstResponseMs",
                title="首次响应时间趋势",
                labels={"createTime": "时间", "firstResponseMs": "响应时间(ms)"},
                markers=True,  # 添加这个参数显示数据点
            )
            st.plotly_chart(fig, config={"width": "stretch"})
    # 模型使用分布
    with tab4:
        if "model" in df.columns:
            model_counts = df["model"].value_counts().reset_index()
            model_counts.columns = ["model", "count"]

            fig = px.pie(
                model_counts, values="count", names="model", title="模型使用分布"
            )
            st.plotly_chart(fig, config={"width": "stretch"})


def init_state():
    default_start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    default_end_date = datetime.now().strftime("%Y-%m-%d")
    if "metric_start_date" not in st.session_state:
        st.session_state.metric_start_date = default_start_date
    if "metric_end_date" not in st.session_state:
        st.session_state.metric_end_date = default_end_date
    if "metric_current_page" not in st.session_state:
        st.session_state.metric_current_page = 1
    if "metric_page_size" not in st.session_state:
        st.session_state.metric_page_size = 10
    if "collection_metric_select" not in st.session_state:
        st.session_state.collection_metric_select = ""
    # 加载数据
    if "metrics_data" not in st.session_state:
        st.session_state.metrics_data = load_metrics_data()


def metric_page():
    """指标页面主体"""
    # 初始化状态
    init_state()

    # 渲染数据表格
    # render_metrics_table(metrics)

    # 如果有数据，渲染统计图表
    render_metrics_stats(st.session_state.metrics_data)

    # 渲染过滤器
    render_metrics_filters()


def main():
    """
    指标分析页面
    """
    st.title(":chart_with_upwards_trend: 对话历史与分析")
    initialize_page()
    render_sidebar(load_metrics_data)
    metric_page()


if __name__ == "__main__":
    main()
