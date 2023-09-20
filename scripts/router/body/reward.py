from pydantic import BaseModel

class CreateReward(BaseModel):
    reward_name: str
    reward_desc: str
    reward_pic: str
    reward_spent_points: int
    reward_active_status: bool = True | False
    class_id: str