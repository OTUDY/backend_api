from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer
from .body.reward import CreateReward
from .crud import SQLiteManager
import jwt
from datetime import datetime
import os

router = APIRouter(prefix='/reward')
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/user/login")
SECRET_KEY = os.environ.get('key')
ALGORITHM = 'HS256'
crud = SQLiteManager('default.sqlite')

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        return username
    except jwt.PyJWTError:
        raise credentials_exception

@router.get('/')
def reward_root() -> Response:
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            'message': 'accessing reward index root.'
        }
    )

@router.post('/create_reward', tags=['rewards'])
def create_reward(current_user: any = Depends(get_current_user), data: CreateReward = None) -> Response:
    query: str = f''' INSERT INTO Rewards (reward_name, reward_desc, reward_pic, reward_spent_points, reward_active_status)
                      VALUES ("{data.reward_name}", "{data.reward_desc}", "{data.reward_pic}", {data.reward_spent_points}, {int(data.reward_active_status)})'''
    crud.add(query)
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            'message': 'successfully created a reward.',
            'reward': data.dict()
        }
    )

@router.get('/get_reward_detail/{reward_name}', tags=['rewards'])
def get_reward_detail(reward_name: str, current_user: any = Depends(get_current_user)) -> Response:
    result = crud.get(f"SELECT * FROM Rewards WHERE reward_name = '{reward_name}'")
    response = {
        'reward_name': result[0][0],
        'reward_desc': result[0][1],
        'reward_pic': result[0][2],
        'reward_spent_points': result[0][3],
        'reward_active_status': result[0][4]
    }
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            'reward': response
        }
    )

@router.post('/update_reward_detail', tags=['rewards'])
def update_reward(current_user: any = Depends(get_current_user), data: CreateReward = None) -> Response:
    crud.edit(f'''UPDATE Rewards SET reward_name = '{data.reward_name}', 
                                   reward_desc = '{data.reward_desc}', 
                                   reward_pic = '{data.reward_pic}', 
                                   reward_spent_points = {data.reward_spent_points}, 
                                   reward_active_status = {int(data.reward_active_status)}
                  WHERE reward_name = "{data.reward_name}"'''
    )
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            'message': 'Successfully updated the reward.',
            'reward': data.dict()
        }
    )

@router.get('/redeem', tags=['rewards'])
def redeem(user_email: str, reward_name: str, current_user: any = Depends(get_current_user)) -> Response:
    redeem_point = crud.get(f'SELECT reward_spent_points FROM Rewards WHERE reward_name = "{reward_name}"')[0][0]
    current_point = crud.get(f'SELECT user_points FROM Users WHERE user_email = "{user_email}"')[0][0]
    crud.edit(f'UPDATE Users SET user_points = {current_point - redeem_point} WHERE user_email = "{user_email}"')
    crud.add(f'INSERT INTO RewardsRedemption (student_id, reward_id, timestamp) VALUES ("{user_email}", "{reward_name}", "{datetime.utcnow()}")')
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            'user': user_email,
            'current_points': current_point - redeem_point,
            'redeem_time': str(datetime.utcnow())
        }
    )

@router.get('/all_rewards', tags=['rewards'])
def get_all_reward(current_user: any = Depends(get_current_user)) -> Response:
    _result = crud.get('SELECT * FROM Rewards')
    rewards = []
    for result in _result:
        rewards.append({
                'reward_name': result[0],
                'reward_desc': result[1],
                'reward_pic': result[2],
                'reward_spent_points': result[3],
                'reward_active_status': result[4]
            })
    return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={'rewards': rewards}
        )
