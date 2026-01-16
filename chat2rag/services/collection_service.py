from chat2rag.core.enums import CollectionSortField, DocumentSortField, SortOrder
from chat2rag.core.exceptions import ValueAlreadyExist, ValueNoExist
from chat2rag.stores.qdrant import QAQdrantDocumentStore


class CollectionService:
    def _validate_collection(self, collection_name: str):
        """验证知识库是否存在"""
        if collection_name not in QAQdrantDocumentStore().get_collection_names():
            raise ValueNoExist(f"知识库<{collection_name}>不存在")

    def get_list(
        self,
        current: int,
        size: int,
        sort_by: CollectionSortField,
        sort_order: SortOrder,
        collection_name: str | None = None,
    ):
        # 获取所有数据
        collection_list = QAQdrantDocumentStore().get_collections()

        # 如果有搜索条件则过滤
        if collection_name:
            collection_list = [
                collection
                for collection in collection_list
                if collection_name.lower() in collection["collection_name"].lower()
                or collection["collection_name"] != "None"
            ]
        else:
            collection_list = [collection for collection in collection_list if collection["collection_name"] != "None"]

        # 排序
        collection_list.sort(key=lambda x: x[sort_by], reverse=(sort_order == SortOrder.DESC))

        # 计算分页
        total = len(collection_list)
        start_index = (current - 1) * size
        end_index = start_index + size
        paginated_collections = collection_list[start_index:end_index]
        return total, paginated_collections

    def create(self, collection_name: str):
        if collection_name in QAQdrantDocumentStore().get_collection_names():
            raise ValueAlreadyExist(f"知识库<{collection_name}>已存在")

        document_store = QAQdrantDocumentStore(collection_name)
        if not document_store.create:
            raise
        return True

    def update(self): ...

    def remove(self, collection_name: str):
        self._validate_collection(collection_name)
        QAQdrantDocumentStore(collection_name).delete_collection


class DocumentService:
    def get_list(
        self,
        collection_name: str,
        current: int,
        size: int,
        sort_by: DocumentSortField,
        sort_order: SortOrder,
        document_content: str | None,
    ):
        document_list = QAQdrantDocumentStore(collection_name).get_document_list

        # 内容过滤
        if document_content:
            document_list = [doc for doc in document_list if document_content.lower() in doc["content"].lower()]

        # 排序
        document_list.sort(key=lambda x: x[sort_by], reverse=(sort_order == SortOrder.DESC))

        # 计算分页
        total = len(document_list)
        start_index = (current - 1) * size
        end_index = start_index + size
        paginated_docs = document_list[start_index:end_index]

        return total, paginated_docs

    async def create(self, collection_name: str, doc_list: list):
        response = await QAQdrantDocumentStore(index=collection_name).write_documents(qa_document_list=doc_list)
        return response.get("writer", {}).get("documents_written", 0) // 2


collection_service = CollectionService()
document_service = DocumentService()
