from pydantic import BaseModel

class ClassCreationForm(BaseModel):
    class_name: str
    level: str
    class_desc: str

class UpdateClassForm(BaseModel):
    id: str
    class_name: str
    level: str
    class_desc: str

class EditStudentForm(BaseModel):
    original_id: str 
    firstname: str
    lastname: str
    inclass_no: int
    class_id: str 