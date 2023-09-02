from .crud import SQLManager
from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer
from .body.classes import ClassCreationForm
import jwt
import os
import pyodbc

router = APIRouter(prefix='/class')
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
def class_root() -> Response:
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            'message': 'accessing class root.'
        }
    )

@router.post('/create_class', tags=['class'])
def create_class(current_user: any = Depends(get_current_user), data: ClassCreationForm = None) -> Response:
    conn = pyodbc.connect(connection_string)
    cursor = conn.cursor()
    clv_id = cursor.execute(f"SELECT clv_id FROM dbo.ClassLevels WHERE clv_name = '{data.level}'").fetchone()[0]
    query: str = f'''
                        INSERT INTO dbo.Classes (class_id, class_name, clv_id, class_desc) 
                        VALUES ('{data.class_name}', '{data.class_name}', {clv_id}, '{data.class_desc}')
                  '''
    cursor.execute(query)
    conn.commit()
    query2: str = f''' INSERT INTO dbo.TeachersClassesRelationship
                       VALUES ('{data.class_name}', '{current_user}')'''
    cursor.execute(query2)
    conn.commit()
    conn.close()
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            'message': 'successfully created class.',
            'class': data.__dict__,
            'assigned_teacher': current_user
        }
    )

@router.put('/update_class_detail', tags=['class'])
def update_class_detail(current_user: any = Depends(get_current_user), data: ClassCreationForm = None) -> Response:
    clv_id = crud.get(f"SELECT clv_id FROM dbo.ClassLevel WHERE '{data.level}'")[0][0]
    query: str = f'''
                        UPDATE Classes SET clv_id = {clv_id}, class_desc = '{data.class_desc}'
                        WHERE class_id = '{data.class_name}'
                  '''
    crud.operate(query, 'edit')
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            'message': 'successfully updated class.',
            'class': data.__dict__
        }
    )

@router.put('/assign_mission', tags=['class'])
def assign_mission(_class: str, mission_name: str, current_user: any = Depends(get_current_user)) -> Response:
    crud.operate(f'''INSERT INTO ClassMissionRelationship (class_id, mission_name) VALUES ('{_class}', '{mission_name}') ''', 'add')
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            'message': 'successfully assigned.',
            'class': _class,
            'mission': mission_name
        }
    )

@router.get('/get_class_meta_data', tags=['class'])
def get_meta_data(_class: str, current_user: any = Depends(get_current_user)) -> Response:
    conn = pyodbc.connect(connection_string)
    cursor = conn.cursor()
    cursor.execute(f''' SELECT  dbo.Students.student_username, 
                                dbo.Classes.class_id, 
                                dbo.ClassLevels.clv_name, 
                                dbo.Missions.mission_name,
                                dbo.Missions.mission_subject,
                                dbo.Missions.mission_active_status,
                                dbo.TeachersClassesRelationship.teacher_id
                        FROM dbo.Students
                        INNER JOIN dbo.Classes
                        ON dbo.Students.class_id = dbo.Classes.class_id
                        INNER JOIN dbo.ClassMissionRelationship
                        ON dbo.Classes.class_id = dbo.ClassMissionRelationship.class_id
                        INNER JOIN dbo.Missions
                        ON dbo.Missions.mission_name = dbo.ClassMissionRelationship.mission_name
                        INNER JOIN dbo.ClassLevels
                        ON dbo.Classes.clv_id = dbo.ClassLevels.clv_id
                        INNER JOIN dbo.TeachersClassesRelationship
                        ON dbo.TeachersClassesRelationship.class_id = dbo.Students.class_id
                        WHERE dbo.Classes.class_id = '{_class}' 
                    '''
                    )
    result = cursor.fetchall()
    if not result:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                'message': 'Class not found.'
            }
        )
    students = []
    teachers = []
    missions = {
        'mathematic': [],
        'chemistry': [],
        'thai': [],
        'english': []
    }
    activities = []
    for class_data in result:
        students.append(class_data[0])
        if class_data[-2] not in teachers:
            teachers.append(class_data[-2])
        missions[class_data[-3]].append(class_data[3])
        if class_data[-1] not in activities:
            activities.append(class_data[-1])
    class_level = class_data[2]
    response_data = {
        'className': _class,
        'classTeachers': teachers,
        'classStudents': students,
        'classMissions': missions,
        'classLevel': class_level,
        'classActivities': activities,
        'classGroups': []
    }
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=response_data
    )

    