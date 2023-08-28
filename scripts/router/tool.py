from .crud import SQLiteManager
from fastapi import status, HTTPException
from fastapi.responses import JSONResponse
from datetime import timedelta, datetime
import jwt

class Tool:
    def get_user_detail(crud: SQLiteManager, key: str, login: bool = False) -> dict:
        sql: str = f'SELECT * FROM Users WHERE user_email = "{key}"'
        try:
            result = crud.get(sql)
        except:
            raise JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED, content={'message': 'Invalid credential.'})
        response = {
            'user_email': result[0][0],
            'user_fname': result[0][2],
            'user_surname': result[0][3],
            'user_phone': result[0][4],
            'user_role': crud.get(f'SELECT role_name FROM Roles WHERE role_id = {result[0][5]}')[0][0],
            'user_affiliation': crud.get(f'SELECT aff_name FROM Affiliations WHERE aff_id = {result[0][6]}')[0][0]
        }
        return response
    
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