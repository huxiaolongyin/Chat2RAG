import pytest


@pytest.fixture
def pipeline():
    from chat2rag.core.pipelines.funciton import FunctionPipeline

    return FunctionPipeline(intention_model="Qwen2.5-14B")


def test_function_pipeline(pipeline):
    # 测试函数调用管道
    result = pipeline.run("今天天气怎么样")
    assert isinstance(result, dict)
    assert "tool_invoker" in result
    # assert "no_function_calls" in result
    # assert isinstance(result["function
