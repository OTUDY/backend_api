from pydantic import BaseModel

class ClassCreationForm(BaseModel):
    class_name: str
    level: str
    class_desc: str