from fastapi import status, HTTPException
from fastapi.responses import JSONResponse
from datetime import timedelta, datetime
import jwt

class Tool:
    
    def create_token(data: dict, expires_delta: timedelta, secret: str, algorithm: str) -> any:
        to_encode = data.copy()
        to_encode.update({"exp": expires_delta})
        encoded_jwt = jwt.encode(to_encode, secret, algorithm=algorithm)
        return encoded_jwt
    
    def decode_token(token: any, secret: str, algorithm: str) -> str:
        credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
        try:
            payload = jwt.decode(token, secret, algorithms=algorithm)
            return payload.get("sub")
        except jwt.PyJWTError:
            raise credentials_exception