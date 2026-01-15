from haystack.components.websearch import SerperDevWebSearch
from haystack.tools import ComponentTool


def doc_to_string(documents) -> str:
    """
    Handles the tool output before conversion to ChatMessage.
    """
    result_str = ""
    for document in documents:
        result_str += (
            f"File Content for {document.meta['link']}\n {document.content}\n\n"
        )

    if len(result_str) > 150_000:  # trim if the content is too large
        result_str = result_str[:150_000] + "...(large file can't be fully displayed)"

    return result_str


web_search = ComponentTool(
    component=SerperDevWebSearch(top_k=5),
    name="web_search",
    description="用于搜索2023年以后发生的热点事件的工具。当问题存在时效性时，可以使用此工具获取最新的信息。",
    outputs_to_string={"source": "documents", "handler": doc_to_string},
)
