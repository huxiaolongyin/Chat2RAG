from datetime import datetime, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st
from controller.metric_controller import metric_controller


# ==================== 状态管理 ====================
def init_state():
    """初始化会话状态"""
    default_start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    default_end_date = datetime.now().strftime("%Y-%m-%d")

    defaults = {
        # Tab 选择
        "active_metric_tab": "指标列表",
        # 指标列表相关
        "metric_start_date": default_start_date,
        "metric_end_date": default_end_date,
        "metric_current_page": 1,
        "metric_page_size": 10,
        "collection_metric_select": "",
        "metrics_data": None,
        # 热门问题相关
        "hot_collection": "",
        "hot_days": 30,
        "hot_limit": 10,
        "hot_questions_data": None,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


# ==================== 数据加载 ====================
def load_metrics_data():
    """加载指标数据"""
    try:
        return metric_controller.get_metric_list(
            current=st.session_state.metric_current_page,
            size=st.session_state.metric_page_size,
            start_time=st.session_state.metric_start_date,
            end_time=st.session_state.metric_end_date,
            collection=st.session_state.collection_metric_select,
        )
    except Exception as e:
        st.error(f"加载指标数据失败: {str(e)}")
        return []


def load_hot_questions_data():
    """加载热门问题数据"""
    try:
        return metric_controller.get_hot_questions(
            st.session_state.hot_collection,
            st.session_state.hot_days,
            st.session_state.hot_limit,
        )
    except Exception as e:
        st.error(f"加载热门问题数据失败: {str(e)}")
        return []


# ==================== 侧边栏渲染 ====================
def render_sidebar():
    """根据当前 tab 渲染对应的侧边栏"""
    with st.sidebar:
        # Tab 选择器
        selected_tab = st.radio(
            "选择功能",
            options=["指标列表", "热门问题"],
            index=0 if st.session_state.active_metric_tab == "指标列表" else 1,
            key="tab_selector",
        )
        st.session_state.active_metric_tab = selected_tab

        # 根据选中的 tab 渲染对应的 sidebar 内容
        if selected_tab == "指标列表":
            render_metrics_sidebar_content()
        else:
            render_hot_questions_sidebar_content()


# ==================== 侧边栏筛选 ====================
def render_metrics_sidebar_content():
    """渲染指标列表的侧边栏筛选条件"""
    with st.sidebar:

        # 时间范围
        start_date = st.date_input(
            "开始日期",
            datetime.strptime(st.session_state.metric_start_date, "%Y-%m-%d"),
            key="metric_start_date_input",
        )
        st.session_state.metric_start_date = start_date.strftime("%Y-%m-%d")

        end_date = st.date_input(
            "结束日期",
            datetime.strptime(st.session_state.metric_end_date, "%Y-%m-%d"),
            key="metric_end_date_input",
        )
        st.session_state.metric_end_date = end_date.strftime("%Y-%m-%d")

        # 场景选择
        collections_list = st.session_state.get("collections_list", [])
        options = ["全部"] + collections_list
        selected = st.selectbox(
            "选择场景",
            options=options,
            index=(
                0
                if not st.session_state.collection_metric_select
                else (
                    options.index(st.session_state.collection_metric_select)
                    if st.session_state.collection_metric_select in options
                    else 0
                )
            ),
            key="collection_metric_select_input",
        )
        st.session_state.collection_metric_select = "" if selected == "全部" else selected

        # 分页设置
        col1, col2 = st.columns(2)
        with col1:
            current_page = st.number_input(
                "页码",
                min_value=1,
                value=st.session_state.metric_current_page,
                step=1,
                key="metric_page_input",
            )
            st.session_state.metric_current_page = current_page

        with col2:
            page_size = st.selectbox(
                "每页显示",
                options=[10, 20, 50, 100, 9999],
                index=(
                    [10, 20, 50, 100, 9999].index(st.session_state.metric_page_size)
                    if st.session_state.metric_page_size in [10, 20, 50, 100, 9999]
                    else 0
                ),
                key="metric_size_input",
            )
            st.session_state.metric_page_size = page_size

        # 查询按钮
        st.divider()
        if st.button("查询指标数据", use_container_width=True, type="primary"):
            with st.spinner("正在加载数据..."):
                st.session_state.metrics_data = load_metrics_data()
            st.rerun()


def render_hot_questions_sidebar_content():
    """渲染热门问题的侧边栏筛选条件"""
    with st.sidebar:

        # 知识库选择
        collections_list = st.session_state.get("collections_list", [])
        options = ["全部"] + collections_list
        selected = st.selectbox(
            "选择知识库",
            options=options,
            index=(
                0
                if not st.session_state.hot_collection
                else options.index(st.session_state.hot_collection) if st.session_state.hot_collection in options else 0
            ),
            key="hot_collection_input",
            help="留空表示所有知识库",
        )
        st.session_state.hot_collection = "" if selected == "全部" else selected

        # 时间范围
        days = st.number_input(
            "热点天数",
            min_value=1,
            max_value=365,
            value=st.session_state.hot_days,
            key="hot_days_input",
        )
        st.session_state.hot_days = days

        # 返回数量
        limit = st.number_input(
            "返回数据数",
            min_value=1,
            max_value=100,
            value=st.session_state.hot_limit,
            key="hot_limit_input",
        )
        st.session_state.hot_limit = limit

        # 查询按钮
        st.divider()
        if st.button("查询热门问题", use_container_width=True, type="primary"):
            with st.spinner("正在加载数据..."):
                st.session_state.hot_questions_data = load_hot_questions_data()
            st.rerun()


# ==================== 工具函数 ====================
def format_response_time(ms):
    """格式化响应时间"""
    if ms is None or pd.isna(ms):
        return "N/A"
    try:
        ms = float(ms)
        if ms < 1000:
            return f"{ms:.2f}ms"
        else:
            return f"{ms/1000:.2f}s"
    except (ValueError, TypeError):
        return "N/A"


def prepare_metrics_dataframe(metrics):
    """准备指标数据的 DataFrame"""
    if not metrics:
        return None

    df = pd.DataFrame(metrics)

    # 保留原始数值列用于图表（在重命名之前）
    if "firstResponseMs" in df.columns:
        df["firstResponseMs_raw"] = df["firstResponseMs"]
        df["firstResponseMs_formatted"] = df["firstResponseMs"].apply(format_response_time)

    if "totalMs" in df.columns:
        df["totalMs_raw"] = df["totalMs"]
        df["totalMs_formatted"] = df["totalMs"].apply(format_response_time)

    # 重命名列
    column_map = {
        "collections": "场景",
        "prompt": "提示词",
        "question": "问题",
        "answer": "回答",
        "firstResponseMs_formatted": "首次响应时间",
        "totalMs_formatted": "总响应时间",
        "model": "模型",
        "chatId": "对话ID",
        "chatRounds": "对话轮次",
        "tools": "工具调用",
        "precisionMode": "精准模式",
        "createTime": "创建时间",
    }

    # 只重命名存在的列
    rename_dict = {k: v for k, v in column_map.items() if k in df.columns}
    df = df.rename(columns=rename_dict)
    return df


# ==================== 指标列表渲染 ====================
def render_metrics_table(df):
    """渲染指标数据表格"""
    if df is None or df.empty:
        st.info("没有找到匹配的数据")
        return

    # 选择要显示的列
    display_columns = ["场景", "问题", "回答", "首次响应时间", "总响应时间", "模型", "对话轮次", "创建时间"]
    display_columns = [col for col in display_columns if col in df.columns]

    st.dataframe(
        df[display_columns],
        column_config={
            "问题": st.column_config.TextColumn("问题", width="medium"),
            "回答": st.column_config.TextColumn("回答", width="large"),
        },
        use_container_width=True,
        hide_index=True,
    )


def render_metrics_charts(df):
    """渲染指标统计图表"""
    if df is None or df.empty:
        return

    col1, col2 = st.columns(2)

    with col1:
        # 场景分布
        if "场景" in df.columns:
            collection_counts = df["场景"].value_counts().reset_index()
            collection_counts.columns = ["场景", "数量"]

            fig = px.pie(
                collection_counts,
                values="数量",
                names="场景",
                title="场景分布",
            )
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        # 模型分布
        if "模型" in df.columns:
            model_counts = df["模型"].value_counts().reset_index()
            model_counts.columns = ["模型", "数量"]

            fig = px.pie(
                model_counts,
                values="数量",
                names="模型",
                title="模型使用分布",
            )
            st.plotly_chart(fig, use_container_width=True)

    # 响应时间趋势
    if "创建时间" in df.columns and "firstResponseMs_raw" in df.columns:
        df_trend = df.copy()
        df_trend["创建时间"] = pd.to_datetime(df_trend["创建时间"])
        df_trend = df_trend.sort_values("创建时间")
        df_trend = df_trend.dropna(subset=["firstResponseMs_raw"])

        if not df_trend.empty:
            fig = px.line(
                df_trend,
                x="创建时间",
                y="firstResponseMs_raw",
                title="首次响应时间趋势",
                labels={"创建时间": "时间", "firstResponseMs_raw": "响应时间(ms)"},
                markers=True,
            )
            st.plotly_chart(fig, use_container_width=True)


def render_metrics_tab():
    """渲染指标列表标签页"""
    st.header("指标数据列表")

    # 初始加载数据
    if st.session_state.metrics_data is None:
        st.session_state.metrics_data = load_metrics_data()

    metrics = st.session_state.metrics_data
    df = prepare_metrics_dataframe(metrics)

    # 显示统计信息
    if df is not None and not df.empty:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("总记录数", len(df))
        with col2:
            if "场景" in df.columns:
                st.metric("场景数", df["场景"].nunique())
        with col3:
            if "模型" in df.columns:
                st.metric("模型数", df["模型"].nunique())
        with col4:
            if "firstResponseMs_raw" in df.columns:
                avg_time = df["firstResponseMs_raw"].mean()
                st.metric("平均响应时间", format_response_time(avg_time))

    st.divider()

    # 数据表格
    st.subheader("数据详情")
    render_metrics_table(df)

    st.divider()

    # 统计图表
    st.subheader("数据分析")
    render_metrics_charts(df)


# ==================== 热门问题渲染 ====================


def render_hot_questions_chart(df_hot):
    """渲染热门问题图表"""
    if df_hot is None or df_hot.empty:
        return

    fig = px.bar(
        df_hot,
        x="问题",
        y="提问次数",
        labels={"问题": "问题内容", "提问次数": "提问次数"},
        color="提问次数",
        color_continuous_scale="Blues",
        text="提问次数",
        title="热门话题统计",
    )
    fig.update_layout(
        xaxis_tickangle=-45,
        height=500,
        showlegend=False,
    )
    fig.update_traces(textposition="outside")
    st.plotly_chart(fig, use_container_width=True)


def render_hot_questions_details(raw_data):
    """渲染热门问题详细信息"""
    if not raw_data:
        return

    st.subheader("相似问题详情")

    for item in raw_data:
        with st.expander(f"{item['representative_question']} (共 {item['count']} 次)"):
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**聚类大小**: {item['cluster_size']}")
                st.write(f"**创建时间**: {item['create_time']}")
            with col2:
                st.write(f"**更新时间**: {item['update_time']}")

            if item.get("similar_questions"):
                st.write("**相似问题列表**:")
                similar_df = pd.DataFrame(
                    [
                        {
                            "问题": q["text"],
                            "知识库": q["collection"],
                            "出现次数": q["count"],
                        }
                        for q in item["similar_questions"]
                    ]
                )
                st.dataframe(similar_df, use_container_width=True, hide_index=True)


def render_hot_questions_tab():
    """渲染热门问题标签页"""
    st.header("热门问题分析")

    # 初始加载数据
    if st.session_state.hot_questions_data is None:
        st.session_state.hot_questions_data = load_hot_questions_data()

    raw_data = st.session_state.hot_questions_data

    if not raw_data:
        st.info("没有找到热门问题数据")
        return

    # 准备数据
    df_hot = pd.DataFrame(
        [
            {
                "问题": item["representative_question"],
                "提问次数": item["count"],
                "聚类大小": item["cluster_size"],
                "更新时间": item["update_time"],
            }
            for item in raw_data
        ]
    )

    # 显示统计信息
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("热门问题数", len(df_hot))
    with col2:
        st.metric("总提问次数", df_hot["提问次数"].sum())
    with col3:
        st.metric("平均提问次数", f"{df_hot['提问次数'].mean():.1f}")

    st.divider()

    # 图表展示
    st.subheader("热门话题统计")
    render_hot_questions_chart(df_hot)

    st.divider()

    # 数据表格
    st.subheader("详细数据")
    st.dataframe(df_hot, use_container_width=True, hide_index=True)

    st.divider()

    # 相似问题详情
    render_hot_questions_details(raw_data)


# ==================== 主入口 ====================
def render():
    """主渲染函数"""
    init_state()

    # 渲染 sidebar
    render_sidebar()

    # st.title("指标监控")

    # 根据 sidebar 选择显示对应内容
    if st.session_state.active_metric_tab == "指标列表":
        render_metrics_tab()
    else:
        render_hot_questions_tab()


render()
