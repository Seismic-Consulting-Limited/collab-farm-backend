from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from passlib.context import CryptContext
import os
from dotenv import load_dotenv
import jwt
from datetime import datetime, timedelta
from typing import Optional

load_dotenv()

SECRET = os.getenv("SECRET")
ALGORITHM = "HS256"
VERIFICATION_TOKEN_EXPIRE_HOURS = 24

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
serializer = URLSafeTimedSerializer(SECRET)


def generate_reset_token(email: str) -> str:
    return serializer.dumps(email, salt="password-reset-salt")


def verify_reset_token(token: str, max_age: int = 3600) -> str | None:
    try:
        email = serializer.loads(
            token, salt="password-reset-salt", max_age=max_age)
        return email
    except (SignatureExpired, BadSignature):
        return None


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def create_email_verification_token(email: str) -> str:
    expire = datetime.utcnow() + timedelta(hours=VERIFICATION_TOKEN_EXPIRE_HOURS)
    payload = {
        "sub": email,
        "scope": "email_verification",
        "exp": expire,
    }
    return jwt.encode(payload, SECRET, algorithm=ALGORITHM)


def decode_email_verification_token(token: str) -> Optional[str]:
    try:
        payload = jwt.decode(token, SECRET, algorithms=[ALGORITHM])
        if payload.get("scope") != "email_verification":
            return None
        return payload.get("sub")
    except jwt.PyJWTError:
        return None
