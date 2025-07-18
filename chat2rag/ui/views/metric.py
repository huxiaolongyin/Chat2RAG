from datetime import datetime, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st
from controller.metric_controller import metric_controller
from utils.initialize import initialize_page
from utils.sidebar import render_sidebar


def render_metrics_filters():
    """渲染指标过滤器"""
    st.subheader("筛选条件")

    col1, col2 = st.columns(2)

    # 时间范围选择
    with col1:
        default_start_date = "2025-01-01"
        default_end_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

        if "metric_start_date" not in st.session_state:
            st.session_state.metric_start_date = default_start_date
        if "metric_end_date" not in st.session_state:
            st.session_state.metric_end_date = default_end_date

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

    # 分页控制
    col1, col2 = st.columns(2)
    with col1:
        if "metric_current_page" not in st.session_state:
            st.session_state.metric_current_page = 1

        current_page = st.number_input(
            "页码",
            min_value=1,
            value=st.session_state.metric_current_page,
            step=1,
            key="metric_page_input",
        )
        st.session_state.metric_current_page = current_page

    with col2:
        if "metric_page_size" not in st.session_state:
            st.session_state.metric_page_size = 10

        page_size = st.selectbox(
            "每页显示",
            options=[10, 20, 50, 100],
            index=[10, 20, 50, 100].index(st.session_state.metric_page_size),
            key="metric_size_input",
        )
        st.session_state.metric_page_size = page_size

    # 刷新按钮
    if st.button("查询", use_container_width=True, type="primary"):
        st.session_state.metrics_data = load_metrics_data()
        st.rerun()


def load_metrics_data():
    """加载指标数据"""
    return metric_controller.get_metric_list(
        current=st.session_state.metric_current_page,
        size=st.session_state.metric_page_size,
        start_time=st.session_state.metric_start_date,
        end_time=st.session_state.metric_end_date,
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
        "createTime": "创建时间",
        "model": "模型",
        "question": "问题",
        "answer": "回答",
        "firstResponseMs": "首次响应时间",
        "totalMs": "总响应时间",
    }

    df = df.rename(columns=column_map)

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
        use_container_width=True,
        hide_index=True,
    )


def render_metrics_stats(metrics):
    """渲染指标统计图表"""
    if not metrics or len(metrics) == 0:
        return

    st.subheader("指标统计")

    tab1, tab2, tab3 = st.tabs(["对话历史", "响应时间分析", "模型使用分布"])
    with tab1:
        # render_metrics_filters()
        render_metrics_table(metrics)
    with tab2:
        # 创建响应时间数据
        df = pd.DataFrame(metrics)

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
            st.plotly_chart(fig, use_container_width=True)

    with tab3:
        # 创建模型使用分布饼图
        if "model" in df.columns:
            model_counts = df["model"].value_counts().reset_index()
            model_counts.columns = ["model", "count"]

            fig = px.pie(
                model_counts, values="count", names="model", title="模型使用分布"
            )
            st.plotly_chart(fig, use_container_width=True)


def metric_page():
    """指标页面主体"""
    # 渲染过滤器
    render_metrics_filters()

    # 加载数据
    if "metrics_data" not in st.session_state:
        st.session_state.metrics_data = load_metrics_data()

    metrics = st.session_state.metrics_data

    # 渲染数据表格
    # render_metrics_table(metrics)

    # 如果有数据，渲染统计图表
    if metrics and len(metrics) > 0:
        render_metrics_stats(metrics)


def main():
    """
    指标分析页面
    """
    st.title(":chart_with_upwards_trend: 对话历史与分析")
    initialize_page()
    render_sidebar()
    metric_page()


if __name__ == "__main__":
    main()
