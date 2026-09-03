from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from passlib.context import CryptContext
import os
from dotenv import load_dotenv

load_dotenv()

SECRET= os.getenv("SECRET")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
serializer = URLSafeTimedSerializer(SECRET)

def generate_reset_token(email: str) -> str:
    return serializer.dumps(email, salt="password-reset-salt")

def verify_reset_token(token: str, max_age: int = 3600) -> str | None:
    try:
        email = serializer.loads(token, salt="password-reset-salt", max_age=max_age)
        return email
    except (SignatureExpired, BadSignature):
        return None

def hash_password(password: str) -> str:
    return pwd_context.hash(password)