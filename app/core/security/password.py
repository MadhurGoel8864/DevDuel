from passlib.context import CryptContext

# Password hashing configuration using bcrypt
pwd_context = CryptContext(schemes=["bcrypt_sha256"], deprecated="auto")


def hash_password(password: str) -> str:
    print(" password: ", password)
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    print(" password11: ", password)
    return pwd_context.verify(password, password_hash)
