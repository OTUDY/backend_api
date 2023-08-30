from pydantic import BaseModel

class CreateMission(BaseModel):
    mission_name: str
    mission_desc: str
    mission_points: int
    mission_active_status: bool = True | False