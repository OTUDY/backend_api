from typing import List
from pydantic import BaseModel

class CreateMission(BaseModel):
    mission_id: str
    mission_name: str
    mission_desc: str
    mission_points: int
    mission_active_status: bool = True | False
    mission_class_id: str
    mission_expired_date: str
    slot_amount: int
    tags: List[str] = ['', '']