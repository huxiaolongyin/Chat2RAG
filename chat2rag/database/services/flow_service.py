from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from chat2rag.database.models import FlowData
from chat2rag.database.services.base_service import BaseService


# 为创建和更新操作定义Pydantic模型
class FlowDataCreate(BaseModel):
    name: str
    desc: Optional[str] = None
    current_version: Optional[int] = 1
    flow_json: Optional[Dict[str, Any]] = None


class FlowDataUpdate(BaseModel):
    name: Optional[str] = None
    desc: Optional[str] = None
    current_version: Optional[int] = None
    flow_json: Optional[Dict[str, Any]] = None


class FlowDataService(BaseService[FlowData, FlowDataCreate, FlowDataUpdate]):
    def get_by_name(self, db, name: str) -> Optional[FlowData]:
        """根据名称获取流程数据"""
        return db.query(self.model).filter(self.model.name == name).first()

    def get_multi_by_name(
        self, db, name: str, skip: int = 0, limit: int = 100
    ) -> List[FlowData]:
        """根据名称模糊匹配获取多个流程数据"""
        return (
            db.query(self.model)
            .filter(self.model.name.contains(name))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_with_pagination(
        self, db, page: int = 1, page_size: int = 20, name: Optional[str] = None
    ):
        """分页获取流程数据，可选择按名称过滤"""
        filters = []
        if name:
            filters.append(self.model.name.contains(name))

        items, total = self.get_paginated(
            db, page=page, page_size=page_size, filters=filters
        )

        return self._build_paginator(items, total, page, page_size)

    def _build_paginator(self, items, total, page, page_size):
        """构建分页结果对象"""
        from chat2rag.database.services.base_service import Paginator

        return Paginator(items, total, page, page_size)

    def get_flows_structure(self, db) -> List[Dict[str, Any]]:
        """
        获取所有流程并转换为指定结构
        """
        flows = self.get_multi(db, skip=0, limit=1000)
        result = []

        for flow in flows:
            if flow.flow_json:
                # 转换为指定结构
                flow_structure = {
                    "name": flow.name,
                    "desc": flow.desc or "",
                    "states": [],
                    "config": {},
                }

                node_id_map = {}
                # 处理states和config
                flow_json = flow.flow_json
                if isinstance(flow_json, dict):
                    for node in flow_json.get("nodes", []):

                        # state
                        state_name = node["data"].get("stateName")

                        if node.get("type") == "start":
                            state_name = "init"
                        if node.get("type") == "end":
                            state_name = "quit"

                        node_id_map[node["id"]] = state_name
                        flow_structure["states"].append(state_name)

                        # config
                        if node.get("isAuto") == True:
                            flow_structure["config"][state_name] = {
                                "response": node["data"]["response"],
                                "conditions": [{"trigger": "auto"}],
                            }
                        elif state_name == "quit":
                            flow_structure["config"][state_name] = {
                                "response": node["data"]["response"]
                            }
                        else:
                            flow_structure["config"][state_name] = {
                                "response": node["data"]["response"],
                                "conditions": node["data"]["conditions"],
                            }

                    for edge in flow_json.get("edges", []):
                        source_state_name = node_id_map[edge["source"]]
                        target_state_name = node_id_map[edge["target"]]
                        state_node = flow_structure["config"][source_state_name]
                        state_node.get("conditions")[0][
                            "next_state"
                        ] = target_state_name

                result.append(flow_structure)

        return result
