import requests
import streamlit as st


@st.cache_data(ttl=1800)
def fetch_changelog():
    try:
        resp = requests.get("http://localhost:8000/api/v1/version/parsed", timeout=5)
        if resp.status_code == 200:
            return resp.json()["versions"]
        else:
            st.error(f"获取版本信息失败：{resp.status_code}")
            return []
    except Exception as e:
        st.error(f"请求异常：{e}")
        return []


def version_list():
    st.subheader("版本更新")

    versions = fetch_changelog()
    if not versions:
        st.caption("暂无版本信息。")
        return

    for v in versions:
        with st.expander(f"{v['version']} ({v['date']})", expanded=False):
            content = (
                v["changelog"]
                .replace("### Added", "### 🚀 New Features")
                .replace("### Changed", "### 🎄 Changed")
                .replace("### Fixed", "### 🐛 Bug Fixed")
                .replace("### Removed", "### 🪓 Removed")
            )
            st.markdown(content)
