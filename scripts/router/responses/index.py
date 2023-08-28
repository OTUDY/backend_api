from pydantic import BaseModel

class IndexResponse(BaseModel):
    status: int = 200,
    message: str = "Index root."
    data: dict = {}