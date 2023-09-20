from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer
from .body.reward import CreateReward
from .crud import SQLiteManager
import jwt
from datetime import datetime
import os
import pyodbc

router = APIRouter(prefix='/reward')
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/user/login")
SECRET_KEY = os.environ.get('key')
ALGORITHM = 'HS256'
driver = pyodbc.drivers()
if driver:
    print(driver)
    driver = driver[-1]
connection_string = '''Driver={%s};
                       Server=tcp:%s,%d;
                       Database=%s;
                       Uid=%s;
                       Pwd=%s;
                       Encrypt=yes;
                       TrustServerCertificate=no;Connection Timeout=300;
                    '''%(driver,
                         os.environ.get('AZURE_SQL_SERVER'),
                         int(os.environ.get('AZURE_SQL_PORT')), 
                         os.environ.get('AZURE_SQL_DATABASE'), 
                         os.environ.get('AZURE_SQL_USER'), 
                         os.environ.get('AZURE_SQL_PASSWORD'))
conn = pyodbc.connect(connection_string)
cursor = conn.cursor()

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
    query: str = f''' INSERT INTO dbo.Rewards (reward_name, reward_desc, reward_spent_points, reward_active_status, class_id)
                      VALUES ('{data.reward_name}', '{data.reward_desc}', {data.reward_spent_points}, {int(data.reward_active_status)}, '{data.class_id}') '''
    cursor.execute(query)
    conn.commit()
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            'message': 'successfully created a reward.',
            'reward': data.__dict__
        }
    )

@router.get('/get_reward_detail/', tags=['rewards'])
def get_reward_detail(reward_name: str, _class: str, current_user: any = Depends(get_current_user)) -> Response:
    result = cursor.execute(f"SELECT * FROM dbo.Rewards WHERE reward_name = '{reward_name}' AND class_id = '{_class}'").fetchone()
    if not result:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                'message': 'reward not found.'
            }
        )
    response = {
        'reward_name': result[0],
        'reward_desc': result[1],
        'reward_pic': result[2],
        'reward_spent_points': result[3],
        'reward_active_status': result[4],
        'class_id': result[5]
    }
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            'reward': response
        }
    )

@router.put('/update_reward_detail', tags=['rewards'])
def update_reward(current_user: any = Depends(get_current_user), data: CreateReward = None) -> Response:
    cursor.execute(f'''UPDATE dbo.Rewards SET reward_name = '{data.reward_name}', 
                                   reward_desc = '{data.reward_desc}', 
                                   reward_pic = '{data.reward_pic}', 
                                   reward_spent_points = {data.reward_spent_points}, 
                                   reward_active_status = {int(data.reward_active_status)},
                                   class_id = '{data.class_id}'
                  WHERE reward_name = '{data.reward_name}' AND class_id = '{data.class_id}' '''
    )
    conn.commit()
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            'message': 'Successfully updated the reward.',
            'reward': data.__dict__
        }
    )

@router.delete('/reward_name', tags=['rewards'])
async def delete_reward(reward_name: str, _class: str, current_user: any = Depends(get_current_user)) -> Response:
    try: 
        cursor.execute(f"DELETE FROM dbo.Rewards WHERE reward_name = '{reward_name}' AND class_id = '{_class}'")
        conn.commit()
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                'message': f'successfully deleted reward {reward_name}'
            }
        )
    except:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                'message': 'reward is not found.'
            }
        )

@router.get('/redeem', tags=['rewards', 'redemption'])
def redeem(user_email: str, reward_name: str, current_user: any = Depends(get_current_user)) -> Response:
    redeem_point = cursor.execute(f'''SELECT reward_spent_points FROM dbo.Rewards WHERE reward_name = '{reward_name}' ''').fetchone()[0]
    current_point = cursor.execute(f'''SELECT student_points FROM dbo.Students WHERE student_username = '{user_email}' ''').fetchone()[0]
    if current_point < redeem_point:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                'message': 'student has not enough points to redeem.'
            }
        )
    try :
        #cursor.execute(f'''UPDATE Users SET user_points = {current_point - redeem_point} WHERE user_email = '{user_email}' ''')
        cursor.execute(f'''INSERT INTO RewardsRedemption (student_id, reward_id, timestamp, status) VALUES ('{user_email}', '{reward_name}', '{str(datetime.utcnow())}', 2)''')
        conn.commit()
        teacher = cursor.execute(f''' SELECT teacher_id 
                                      FROM dbo.TeachersClassesRelationship
                                      INNER JOIN dbo.Students
                                      ON dbo.Students.class_id = dbo.TeachersClassesRelationship.class_id
                                      WHERE dbo.Students.student_username = '{user_email}' ''')\
                        .fetchone()[0]
        
        # Doing notify logic

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                'message': 'pending approval for this redeem, waiting for teacher to approve.',
                'redeemer': user_email,
                'approver': teacher
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                'message': 'Unable to proceed.',
                'error': str(e)
            }
        )

@router.get('/get_all_rewards', tags=['rewards'])
def get_all_reward(_class: str, current_user: any = Depends(get_current_user)) -> Response:
    _result = cursor.execute(f'''SELECT * FROM dbo.Rewards WHERE class_id = '{_class}' ''').fetchall()
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

@router.get('/get_all_pending_approval_redemptions', tags=['rewards', 'redemption'])
async def get_all_pending_approval_redemptions(_class: str, current_user: any = Depends(get_current_user)) -> Response:
    _result = cursor.execute(f'''SELECT student_id, reward_id, status, timestamp, reward_desc, reward_spent_points
                                FROM dbo.RewardsRedemption
                                INNER JOIN dbo.Rewards
                                ON dbo.Rewards.reward_name = dbo.RewardsRedemption.reward_id
                                WHERE dbo.RewardsRedemption.status = 2 AND class_id = '{_class}' ''').fetchall()
    redeems = {}
    for index, redempt in enumerate(_result):
        key = f'reward_{index}'
        redeems[key] = {
            'redeemer': redempt[0],
            'reward': redempt[1],
            'redeemed_time': redempt[3],
            'reward_desc': redempt[4],
            'reward_points': redempt[5]
        }
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            'redeems': redeems
        }
    )
    
@router.get('/update_redemption_status', tags=['rewards', 'redemption'])
async def update_status(redeemer: str, reward_id: str, status_: str, _class: str, current_user: any = Depends(get_current_user)) -> Response:
    if status_ == 'deny': 
        try :
            cursor.execute(f''' UPDATE dbo.RewardsRedemption 
                                SET status = 0
                                WHERE reward_id = '{reward_id}' AND student_id = '{redeemer}' AND class_id = '{_class}' ''')
            conn.commit()
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    'message': 'Redemption request has been denied.'
                }
            )
        except Exception as e:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    'message': 'Unable to proceed, try again or check your query.',
                    'error': str(e)
                }
            )
    elif status_ == 'approve': 
        try :
            current_points = cursor.execute(f''' SELECT student_points - reward_spent_points
                                                FROM dbo.Students
                                                INNER JOIN dbo.RewardsRedemption
                                                ON dbo.RewardsRedemption.student_id = dbo.Students.student_username
                                                INNER JOIN dbo.Rewards
                                                ON dbo.RewardsRedemption.reward_id = dbo.Rewards.reward_name
                                                WHERE dbo.RewardsRedemption.student_id = '{redeemer}' AND dbo.RewardsRedemption.reward_id = '{reward_id}' AND dbo.RewardsRedemption.class_id = '{_class}'
                                            ''')\
                                            .fetchone()[0]
            cursor.execute(f''' UPDATE dbo.RewardsRedemption 
                                SET status = 1
                                WHERE reward_id = '{reward_id}' AND student_id = '{redeemer}' AND class_id = '{_class}' ''')
            cursor.execute(f''' UPDATE dbo.Students
                                SET student_points = {current_points}
                                WHERE student_username = '{redeemer}'
                            ''')
            conn.commit()
            
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    'message': 'Redemption request has been approved'
                }
            )
        except Exception as e:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    'message': 'Unable to proceed, try again or check your query.',
                    'error': str(e)
                }
            )
    