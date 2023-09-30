from pydantic import BaseModel

class CreateReward(BaseModel):
    reward_name: str
    reward_desc: str
    reward_pic: str
    reward_spent_points: int
    expired_date: str
    class_id: str
    amount: int

class EditRewardForm(BaseModel):
    reward_id: str
    reward_name: str
    reward_desc: str
    reward_pic: str
    reward_spent_points: int
    expired_date: str
    class_id: str
    amount: int