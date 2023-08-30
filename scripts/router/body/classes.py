from pydantic import BaseModel

class ClassCreationForm(BaseModel):
    class_name: str
    level: int
    class_desc: str