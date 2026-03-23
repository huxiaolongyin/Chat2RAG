from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from chat2rag.core.logger import get_logger

logger = get_logger(__name__)


class TenantMiddleware(BaseHTTPMiddleware):
    """租户上下文中间件"""

    async def dispatch(self, request: Request, call_next):
        tenant_code = request.headers.get("X-Tenant-Code")
        if tenant_code:
            request.state.tenant_code = tenant_code

        response = await call_next(request)
        return response
