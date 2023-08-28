from pydantic import BaseModel

class Token(BaseModel):
    access_token: str
    token_type: str

class UserCredentials(BaseModel):
    email: str
    password: str

class Register(BaseModel):
    email: str
    password: str
    firstname: str
    surname: str
    user_type: int
    phone_number: str
