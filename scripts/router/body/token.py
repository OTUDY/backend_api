from pydantic import BaseModel

class UserKey(BaseModel):
    user_key: str