from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from chat2rag.api.schema import Error, Success
from chat2rag.database.connection import get_db
from chat2rag.database.models import FlowData
from chat2rag.database.services.base_service import Paginator
from chat2rag.database.services.flow_service import (
    FlowDataCreate,
    FlowDataService,
    FlowDataUpdate,
)

router = APIRouter()
flow_service = FlowDataService(FlowData)


@router.post("/add")
def create_flow(
    *, db: Session = Depends(get_db), flow_in: FlowDataCreate
) -> Dict[str, Any]:
    """
    创建新的流程数据
    """
    try:
        flow_service.create(db, flow_in)
        return Success(msg="流程创建成功")

    except Exception as e:
        return Error(msg=f"创建流程失败: {str(e)}")


@router.get("/{id}")
def get_flow(*, db: Session = Depends(get_db), id: int) -> Dict[str, Any]:
    """
    根据ID获取流程数据
    """
    flow = flow_service.get(db, id)
    if not flow:
        return Error(msg=f"流程数据不存在")

    return Success(
        msg="获取成功",
        data=flow.to_dict() if hasattr(flow, "to_dict") else flow.__dict__,
    )


@router.get("/", response_model=Dict[str, Any])
def get_flows(
    *,
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, le=100),
    name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    分页获取流程数据列表，支持按名称搜索
    """
    try:
        paginator = flow_service.get_with_pagination(
            db, page=page, page_size=page_size, name=name
        )
        # total =

        return Success(
            data={
                "prompt_list": paginator.to_dict(),
                "current": page,
                "size": page_size,
                # "total": total,
                # "pages": pages,
            },
        )
    except Exception as e:
        return Error(msg="获取流程列表失败")


@router.put("/{id}", response_model=Dict[str, Any])
def update_flow(
    *, db: Session = Depends(get_db), id: int, flow_in: FlowDataUpdate
) -> Dict[str, Any]:
    """
    更新流程数据
    """
    flow = flow_service.get(db, id)
    if not flow:
        return Error(msg="流程数据不存在")

    try:
        flow = flow_service.update(db, db_obj=flow, obj_in=flow_in)
        return Success(
            msg="更新成功",
            data=flow.to_dict() if hasattr(flow, "to_dict") else flow.__dict__,
        )
    except Exception as e:
        return Error(msg=f"更新流程失败: {str(e)}")


@router.delete("/{id}", response_model=Dict[str, Any])
def delete_flow(*, db: Session = Depends(get_db), id: int) -> Dict[str, Any]:
    """
    删除流程数据
    """
    flow = flow_service.get(db, id)
    if not flow:
        return Error(msg="流程数据不存在")
        # raise HTTPException(
        #     status_code=status.HTTP_404_NOT_FOUND, detail="流程数据不存在"
        # )

    try:
        flow_service.delete(db, id=id)
        return Success(msg="删除成功")
        # return {"code": 200, "message": "删除成功", "data": {}}
    except Exception as e:
        return Error(msg=f"删除流程失败: {str(e)}")
        # raise HTTPException(
        #     status_code=status.HTTP_400_BAD_REQUEST, detail=f"删除流程失败: {str(e)}"
        # )
