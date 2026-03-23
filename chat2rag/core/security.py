from datetime import datetime, timedelta
from typing import Any, Optional

import jwt
from passlib.context import CryptContext

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12,
    truncate_error=False,
)

SECRET_KEY = "chat2rag-secret-key-please-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """生成密码哈希"""
    return pwd_context.hash(password)


def create_access_token(
    data: dict[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """创建访问令牌"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict[str, Any]]:
    """解码访问令牌"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.PyJWTError:
        return None


class SmsCodeManager:
    """验证码管理器（简单实现，生产环境应使用Redis）"""

    def __init__(self):
        self._codes: dict[str, dict[str, Any]] = {}

    def generate_code(self, phone: str, code: Optional[str] = None) -> str:
        """生成验证码"""
        import random

        if code is None:
            code = "".join([str(random.randint(0, 9)) for _ in range(6)])

        self._codes[phone] = {
            "code": code,
            "expire_time": datetime.utcnow() + timedelta(minutes=5),
            "used": False,
        }
        return code

    def verify_code(self, phone: str, code: str) -> bool:
        """验证验证码"""
        if phone not in self._codes:
            return False

        code_info = self._codes[phone]
        if code_info["used"]:
            return False
        if datetime.utcnow() > code_info["expire_time"]:
            del self._codes[phone]
            return False
        if code_info["code"] != code:
            return False

        code_info["used"] = True
        return True

    def remove_code(self, phone: str) -> None:
        """移除验证码"""
        self._codes.pop(phone, None)


sms_code_manager = SmsCodeManager()
