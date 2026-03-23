from fastapi import APIRouter, Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from chat2rag.core.deps import get_current_user
from chat2rag.core.security import sms_code_manager
from chat2rag.schemas.auth import (
    CurrentUserResponse,
    LoginRequest,
    LoginResponse,
    SmsCodeRequest,
    SmsLoginRequest,
)
from chat2rag.schemas.base import BaseResponse
from chat2rag.services.auth_service import auth_service

router = APIRouter()
security = HTTPBearer(auto_error=False)


@router.post("/login", response_model=BaseResponse[LoginResponse])
async def login(request: Request, data: LoginRequest):
    """用户名密码登录"""
    client_ip = request.client.host if request.client else None
    result = await auth_service.login(data, client_ip)
    if not result:
        return BaseResponse.error(msg="用户名或密码错误", code="4001", http_status=400)
    return BaseResponse(data=result)


@router.post("/sms-login", response_model=BaseResponse[LoginResponse])
async def sms_login(request: Request, data: SmsLoginRequest):
    """手机验证码登录"""
    client_ip = request.client.host if request.client else None
    result = await auth_service.sms_login(data, client_ip)
    if not result:
        return BaseResponse.error(
            msg="验证码错误或已过期", code="4002", http_status=400
        )
    return BaseResponse(data=result)


@router.post("/sms-code", response_model=BaseResponse)
async def send_sms_code(data: SmsCodeRequest):
    """发送短信验证码"""
    code = sms_code_manager.generate_code(data.phone)
    print(f"[DEV] 验证码: {code}, 手机号: {data.phone}")
    return BaseResponse(msg="验证码已发送")


@router.get("/me", response_model=BaseResponse[CurrentUserResponse])
async def get_current_user_info(
    current_user: CurrentUserResponse = Depends(get_current_user),
):
    """获取当前用户信息"""
    return BaseResponse(data=current_user)


@router.post("/logout", response_model=BaseResponse)
async def logout(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """登出（客户端删除Token即可）"""
    return BaseResponse(msg="登出成功")
