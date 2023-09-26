from pydantic import BaseModel, Field

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

class AddStudent(BaseModel):
    username: str
    pwd: str
    firstname: str
    surname: str
    class_name: str

class AddStudentByLink(BaseModel):
    username: str
    pwd: str
    firstname: str
    surname: str

class AddStudentObject(BaseModel):
    fname: str
    surname: str
    class_id: str
    inclass_id: int

class EditStudentObject(BaseModel):
    fname: str = Field("First name of the student: ")
    surname: str = Field("Last name of the student: ")
    inclass_no: int = Field("No.: ")
    original_id: str = Field('Original ID (e.g. FirstName.LastName): ')
    class_id: str = Field('Class ID: ')
    
