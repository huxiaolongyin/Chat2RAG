from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

# 测试数据
test_collection_name = "test_collection"
test_doc = "这是一个测试文档"


# 0. 测试接口状态
def test_get_collection_list():
    response = client.get("/api/v1/status")
    assert response.status_code == 200
    assert response.json()["msg"] == "OK"


# 1. 测试获取知识库列表
def test_get_collection_list():
    response = client.get("/api/v1/knowledge/collection")
    assert response.status_code == 200
    data = response.json()
    assert "collectionList" in data["data"]
    assert "total" in data["data"]
    assert "pages" in data["data"]


# 2. 测试创建知识库
def test_create_collection():
    # 创建知识库
    response = client.post(
        "/api/v1/knowledge/collection", params={"collectionName": test_collection_name}
    )
    assert response.status_code == 200
    assert response.json()["msg"] == "知识库创建成功"

    # 测试重复创建
    response = client.post(
        "/api/v1/knowledge/collection", params={"collectionName": test_collection_name}
    )
    assert response.status_code == 400
    assert response.json()["msg"] == "知识库已存在"


# 3. 测试添加文档
def test_create_doc():
    response = client.post(
        "/api/v1/knowledge/collection/docs",
        params={"collectionName": test_collection_name},
        json=[test_doc],
    )
    assert response.status_code == 200
    assert response.json()["msg"] == "知识创建成功"


# 4. 测试查询文档
def test_query_docs():
    response = client.get(
        "/api/v1/knowledge/query",
        params={"collectionName": test_collection_name, "query": "测试", "topK": 5},
    )
    assert response.status_code == 200
    assert "docList" in response.json()["data"]


# 5. 测试删除知识库
def test_delete_collection():
    response = client.delete(
        "/api/v1/knowledge/collection", params={"collectionName": test_collection_name}
    )
    assert response.status_code == 200
    assert response.json()["msg"] == "删除知识库成功"


# 6. 测试错误情况
def test_error_cases():
    # 测试不存在的知识库
    response = client.get(
        "/api/v1/knowledge/collection/docs",
        params={"collectionName": "not_exist_collection"},
    )
    assert response.status_code == 400
    assert response.json()["msg"] == "知识库不存在"


# 7. 测试分页和排序
def test_collection_list_with_params():
    response = client.get(
        "/api/v1/knowledge/collection",
        params={
            "current": 1,
            "size": 10,
            "sortBy": "collection_name",
            "sortOrder": "desc",
        },
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data["collectionList"]) <= 10
