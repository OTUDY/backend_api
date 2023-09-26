from datetime import datetime
from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer
from .body.token import UserKey
from .body.mission import CreateMission
from .crud import SQLiteManager, SQLManager
import jwt
import os
import pyodbc
from cryptography.fernet import Fernet

router = APIRouter(prefix='/mission')
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
def mission_root() -> Response:
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            'message': 'accessing mission root route.'
        }
    )

@router.post('/create_mission', tags=['missions'])
async def create_mission(current_user: UserKey = Depends(get_current_user), data: CreateMission = None) -> Response:
    conn = pyodbc.connect(connection_string)
    cursor = conn.cursor()
    tags: str = '[' + ', '.join(data.tags) + ']'
    query: str = f'''
        INSERT INTO dbo.Missions
        (mission_name, mission_desc, mission_points, mission_active_status, mission_expired_date, mission_created_in_class, mission_subject)
        VALUES
        ('{data.mission_name}', '{data.mission_desc}', '{data.mission_points}', {int(data.mission_active_status)}, '{data.mission_expired_date}', '{data.mission_class_id}', '{tags}')
    '''
    cursor.execute(query)
    conn.commit()
    conn.close()
    return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                'message': 'Successfully created the mission.',
                'created_mission': {
                    'name': data.mission_name,
                    'description': data.mission_desc,
                    'points': data.mission_points,
                    'active_status': data.mission_active_status,
                    'created_within_class': data.mission_class_id
                }
            }
        )
    
@router.get('/get_mission_detail/', tags=['missions'])
def get_mission_detail(mission_name: str, _class: str, current_user: UserKey = Depends(get_current_user)) -> Response:
    conn = pyodbc.connect(connection_string)
    cursor = conn.cursor()
    query: str = f'''SELECT * FROM dbo.Missions WHERE mission_name = '{mission_name}' AND mission_created_in_class = '{_class}' '''
    result = cursor.execute(query).fetchone()
    if not result:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                'message': 'Mission is not found.'
            }
        )
    response_body = {
                'name': result[0],
                'description': result[1],
                'redeem_points': result[2],
                'pic': result[3],
                'active_status': bool(result[4]),
                'expired_date': result[5],
                'created_in_class': result[6],
                'tags': result[7]
            }
    conn.close()
    return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                'message': 'Successfully fetched',
                'mission_data': response_body
            }
        )

@router.delete('/delete_mission', tags=['missions'])
async def delete_mission(mission_name: str, _class: str, current_user: any = Depends(get_current_user)) -> Response:
    conn = pyodbc.connect(connection_string)
    cursor = conn.cursor()
    cursor.execute(f''' DELETE FROM dbo.Missions WHERE mission_name = '{mission_name}' AND dbo.Missions.mission_created_in_class = '{_class}' ''')
    conn.commit()
    conn.close()
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            'message': f"successfully deleted mission {mission_name} "
        }
    )

@router.get('/get_all_missions', tags=['missions'])
def get_all_mission(_class: str, current_user: any = Depends(get_current_user)) -> Response:
    conn = pyodbc.connect(connection_string)
    cursor = conn.cursor()
    _result = cursor.execute(f'''SELECT * FROM dbo.Missions WHERE mission_created_in_class = '{_class}' ''').fetchall()
    missions = []
    for result in _result:
        status = False
        try:
            expired_date = ''
            if '/' in result[5]:
                expired_date = result[5].split('/')
            elif ' ' in result[5]:
                expired_date = result[5].split(' ')
            months_thai = {
                        "มกราคม": 1,
                        "กุมภาพันธ์": 2,
                        "มีนาคม": 3,
                        "เมษายน": 4,
                        "พฤษภาคม": 5,
                        "มิถุนายน": 6,
                        "กรกฎาคม": 7,
                        "สิงหาคม": 8,
                        "กันยายน": 9,
                        "ตุลาคม": 10,
                        "พฤศจิกายน": 11,
                        "ธันวาคม": 12
                    }

            months_english = {
                        "January": 1,
                        "February": 2,
                        "March": 3,
                        "April": 4,
                        "May": 5,
                        "June": 6,
                        "July": 7,
                        "August": 8,
                        "September": 9,
                        "October": 10,
                        "November": 11,
                        "December": 12
                    }

            if months_thai[expired_date[1]] is not None:
                expired_date[1] = months_thai[expired_date[1]]
            elif months_english[expired_date[1]] is not None:
                expired_date[1] = months_english[expired_date[1]]
            if datetime.now() < datetime(int(expired_date[2]), int(expired_date[1]), int(expired_date[0])):
                status = True
        except:
            status = "Error, this field requires datetime format."
        missions.append({
                'name': result[0],
                'description': result[1],
                'redeem_points': result[2],
                'pic': result[3],
                'active_status': status,
                'expired_date': result[5],
                'created_in_class': result[6],
                'tags': result[7]
            })
    conn.close()
    return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={'missions': missions}
        )

@router.put('/update_mission_detail', tags=['missions'])
async def update_mission(current_user: any = Depends(get_current_user), data: CreateMission = None) -> Response:
    conn = pyodbc.connect(connection_string)
    cursor = conn.cursor()
    query: str = f'''UPDATE dbo.Missions SET mission_desc = '{data.mission_desc}', 
                                         mission_points = {data.mission_points},  
                                         mission_active_status = {int(data.mission_active_status)},
                                         mission_expired_date = '{data.mission_expired_date}',
                                         mission_subject = '{'[' + ', '.join(data.tags) + ']'}'
                     WHERE mission_name = '{data.mission_name}' AND mission_created_in_class = '{data.mission_class_id}' '''
    cursor.execute(query)
    conn.commit()
    conn.close()
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            'message': 'successfully editted.',
            'mission': data.__dict__
        }
    )

@router.put('/upload_mission_image', tags=['missions'])
def upload_image(current_user: any = Depends(get_current_user), image: UploadFile = File(...), mission_name: str = None) -> Response:
    conn = pyodbc.connect(connection_string)
    cursor = conn.cursor()
    cursor.execute(f"UPDATE Missions SET mission_pic = {image}")
    conn.commit()
    conn.close()
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            'message': f"Updated mission {mission_name}'s image."
        }
    )

@router.get('/assign_mission_to_student', tags=['missions', 'student'])
async def assign_mission_to_student(mission_name: str, student_id: str, _class: str, current_user: any = Depends(get_current_user)) -> Response:
    conn = pyodbc.connect(connection_string)
    cursor = conn.cursor()
    try: 
        cursor.execute(f''' INSERT INTO dbo.StudentsMissionsRelationship
                            VALUES ('{student_id}', '{mission_name}', '{str(datetime.utcnow())}', 2, '{_class}')
                        ''')
        conn.commit()
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                'message': f'student {student_id} has started {mission_name}.'
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                'error': str(e)
            }
        )
    
@router.get('/update_mission_student_status', tags=['missions', 'student'])
async def update_mission_status(student_id: str, mission_name: str, status_: str, _class: str, current_user: any = Depends(get_current_user)) -> Response:
    conn = pyodbc.connect(connection_string)
    cursor = conn.cursor()
    if status_ == 'deny': 
        try :
            cursor.execute(f''' UPDATE dbo.StudentsMissionsRelationship 
                                SET status = 0
                                WHERE mission_name = '{mission_name}' AND student_id = '{student_id}' AND class_id = '{_class}' ''')
            conn.commit()
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    'message': 'Mission request has been denied.'
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
            current_points = cursor.execute(f''' SELECT student_points + mission_points
                                                FROM dbo.Students
                                                INNER JOIN dbo.StudentsMissionsRelationship
                                                ON dbo.StudentsMissionsRelationship.student_id = dbo.Students.student_username
                                                INNER JOIN dbo.Missions
                                                ON dbo.StudentsMissionsRelationship.mission_name = dbo.Missions.mission_name
                                                WHERE dbo.StudentsMissionsRelationship.student_id = '{student_id}' 
                                                AND dbo.StudentsMissionsRelationship.mission_name = '{mission_name}'
                                                AND dbo.StudentsMissionsRelationship.class_id = '{_class}'
                                            ''')\
                                            .fetchone()[0]
            cursor.execute(f''' UPDATE dbo.StudentsMissionsRelationship 
                                SET status = 1
                                WHERE mission_name = '{mission_name}' AND student_id = '{student_id}' ''')
            cursor.execute(f''' UPDATE dbo.Students
                                SET student_points = {current_points},
                                    student_net_points += {current_points}
                                WHERE student_username = '{student_id}'
                            ''')
            conn.commit()
            
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    'message': 'Mission request has been approved'
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
        
@router.get('/get_all_on_going_missions', tags=['missions', 'student'])
async def get_all_pending_approval_redemptions(_class: str, current_user: any = Depends(get_current_user)) -> Response:
    cipher = Fernet(SECRET_KEY.encode())
    conn = pyodbc.connect(connection_string)
    cursor = conn.cursor()
    _result = cursor.execute(f'''SELECT student_id, dbo.Missions.mission_name, status, start_date, mission_desc, mission_points, dbo.Students.student_fname, dbo.Students.student_surname
                                FROM dbo.StudentsMissionsRelationship
                                INNER JOIN dbo.Missions
                                ON dbo.Missions.mission_name = dbo.StudentsMissionsRelationship.mission_name
                                INNER JOIN dbo.Students
                                ON dbo.Students.student_username = dbo.StudentsMissionsRelationship.student_id
                                WHERE dbo.Missions.mission_created_in_class = '{_class}' ''').fetchall()
    redeems = []
    for index, redempt in enumerate(_result):
        key = f'missioner_{index}'
        redeems.append({
            'student': redempt[0],
            'firstname': cipher.decrypt(redempt[6].encode()).decode(),
            'surname': cipher.decrypt(redempt[7].encode()).decode(),
            'mission_name': redempt[1],
            'status': redempt[2],
            'started_date': redempt[3],
            'description': redempt[4],
            'points': redempt[5]
        })
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            'on_going_missions': redeems
        }
    )

@router.get('/get_on_going_missions_by_mission', tags=['missions', 'student'])
async def get_all_pending_approval_redemptions(_class: str, mission_name: str, current_user: any = Depends(get_current_user)) -> Response:
    conn = pyodbc.connect(connection_string)
    cipher = Fernet(SECRET_KEY.encode())
    cursor = conn.cursor()
    _result = cursor.execute(f'''SELECT student_id, dbo.Missions.mission_name, status, start_date, mission_desc, mission_points, dbo.Students.student_fname, dbo.Students.student_surname
                                FROM dbo.StudentsMissionsRelationship
                                INNER JOIN dbo.Missions
                                ON dbo.Missions.mission_name = dbo.StudentsMissionsRelationship.mission_name
                                INNER JOIN dbo.Students
                                ON dbo.Students.student_username = dbo.StudentsMissionsRelationship.student_id
                                WHERE dbo.StudentsMissionsRelationship.class_id = '{_class}' 
                                AND dbo.StudentsMissionsRelationship.mission_name = '{mission_name}' ''').fetchall()
    redeems = []
    for index, redempt in enumerate(_result):
        redeems.append({
            'student': redempt[0],
            'firstname': cipher.decrypt(redempt[6].encode()).decode(),
            'surname': cipher.decrypt(redempt[7].encode()).decode(),
            'mission_name': redempt[1],
            'status': redempt[2],
            'started_date': redempt[3],
            'description': redempt[5],
            'points': redempt[4]
        })
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            'on_going_missions': redeems
        }
    )