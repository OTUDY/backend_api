from pydantic import BaseModel

class RegisterForm(BaseModel):
    email: str
    pwd: str
    fname: str
    surname: str
    phone: str
    role: int = 0 | 1 | 2
    affiliation: str
    class_id: str

class LoginForm(BaseModel):
    email: str
    pwd: str

class EditForm(BaseModel):
    email: str
    fname: str
    surname: str
    phone: str
    role: int = 0 | 1 | 2
    affiliation: str
    class_id: str
