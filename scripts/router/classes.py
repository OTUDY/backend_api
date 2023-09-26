from .crud import SQLManager
from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer
from .body.classes import ClassCreationForm
from .body.user import AddStudentObject
import jwt
import os
import pyodbc
from .body.user import AddStudent
from cryptography.fernet import Fernet
from typing import List

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
                    ''' % (driver,
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
    clv_id = cursor.execute(
        f"SELECT clv_id FROM dbo.ClassLevels WHERE clv_name = '{data.level}'").fetchone()[0]
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
    conn = pyodbc.connect(connection_string)
    cursor = conn.cursor()
    clv_id = cursor.execute(
        f"SELECT clv_id FROM dbo.ClassLevels WHERE clv_name = '{data.level}'").fetchone()[0]
    query: str = f'''
                        UPDATE Classes SET clv_id = {clv_id}, class_desc = '{data.class_desc}'
                        WHERE class_id = '{data.class_name}'
                  '''
    cursor.execute(query)
    conn.commit()
    conn.close()
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            'message': 'successfully updated class.',
            'class': data.__dict__
        }
    )


@router.put('/assign_mission', tags=['class'])
def assign_mission(_class: str, mission_name: str, current_user: any = Depends(get_current_user)) -> Response:
    conn = pyodbc.connect(connection_string)
    cursor = conn.cursor()
    cursor.execute(
        f'''INSERT INTO ClassMissionRelationship (class_id, mission_name) VALUES ('{_class}', '{mission_name}') ''')
    conn.commit()
    conn.close()
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            'message': 'successfully assigned.',
            'class': _class,
            'mission': mission_name
        }
    )


@router.delete('/delete_class', tags=['class'])
async def delete_class(_class: str, current_user: any = Depends(get_current_user)) -> Response:
    conn = pyodbc.connect(connection_string)
    cursor = conn.cursor()
    cursor.execute(
        f'''DELETE FROM dbo.ClassesActivitiesRelationship WHERE class_id = '{_class}' ''')
    cursor.execute(
        f'''DELETE FROM dbo.ClassMissionRelationship WHERE class_id = '{_class}' ''')
    cursor.execute(
        f'''DELETE FROM dbo.TeachersClassesRelationship WHERE class_id = '{_class}' ''')
    cursor.execute(
        f'''DELETE FROM dbo.StudentsClassesRelationship WHERE class_id = '{_class}' ''')
    cursor.execute(f'''DELETE FROM dbo.Classes WHERE class_id = '{_class}' ''')
    conn.commit()
    conn.close()
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            'message': 'successfully deleted',
            'class': _class,
        }
    )


@router.get('/get_class_meta_data', tags=['class'])
def get_meta_data(_class: str, current_user: any = Depends(get_current_user)) -> Response:
    conn = pyodbc.connect(connection_string)
    cursor = conn.cursor()
    cursor.execute(f''' SELECT  dbo.StudentsClassesRelationship.student_id, 
                                dbo.Classes.class_id, 
                                dbo.ClassLevels.clv_name, 
                                dbo.Missions.mission_name,
                                dbo.Missions.mission_subject,
                                dbo.Missions.mission_active_status,
                                dbo.TeachersClassesRelationship.teacher_id,
                                dbo.ClassesActivitiesRelationship.act_name,
                                dbo.Students.student_fname,
                                dbo.Students.student_surname,
                                dbo.Missions.mission_points,
                                dbo.Missions.mission_desc
                        FROM dbo.Classes
                        LEFT JOIN dbo.StudentsClassesRelationship
                        ON dbo.StudentsClassesRelationship.class_id = dbo.Classes.class_id
                        LEFT JOIN dbo.Students
                        ON dbo.Students.student_username = dbo.StudentsClassesRelationship.student_id
                        LEFT JOIN dbo.Missions
                        ON dbo.Classes.class_id = dbo.Missions.mission_created_in_class
                        LEFT JOIN dbo.ClassLevels
                        ON dbo.Classes.clv_id = dbo.ClassLevels.clv_id
                        LEFT JOIN dbo.TeachersClassesRelationship
                        ON dbo.TeachersClassesRelationship.class_id = dbo.StudentsClassesRelationship.class_id
                        LEFT JOIN dbo.ClassesActivitiesRelationship
                        ON dbo.ClassesActivitiesRelationship.class_id = dbo.Classes.class_id
                        WHERE dbo.Classes.class_id = '{_class}' 
                    '''
                   )
    result = cursor.fetchall()
    cipher = Fernet(SECRET_KEY.encode())
    if not result:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                'message': 'Class not found.'
            }
        )
    students = []
    teachers = []
    missions = []
    activities = []
    _added_missions = []
    _added_students = []
    for class_data in result:
        if class_data[0] != None:
            if class_data[0] not in _added_students:
                students.append({
                'studentId': class_data[0],
                'firstName': cipher.decrypt(class_data[8].encode()).decode(),
                'surName': cipher.decrypt(class_data[9].encode()).decode()
            })
                _added_students.append(class_data[0])
        if class_data[3] not in _added_missions:
            missions.append(
                {
                    'name': class_data[3],
                    'tags': class_data[4],
                    'reward_points': class_data[10],
                    'description': class_data[11]
                }
            )
            _added_missions.append(class_data[3])
        
        if class_data[6] != None:
            if class_data[6] not in teachers:
                teachers.append(class_data[6])
        if class_data[7] != None:
            if class_data[7] not in activities:
                activities.append(class_data[7])
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
    conn.close()
    _added_missions.clear()
    _added_students.clear()
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=response_data
    )


@router.put('/remove_students', tags=['class', 'student'])
async def remove_students(students: List[str], _class: str ,current_user: any = Depends(get_current_user)) -> Response:
    conn = pyodbc.connect(connection_string)
    cursor = conn.cursor()
    for student in students:
        cursor.execute(
            f''' DELETE FROM dbo.StudentsClassesRelationship WHERE student_id = '{student}' AND class_id = '{_class}' ''')
    conn.commit()
    conn.close()
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            'message': 'successfully removed students.',
            'removed_students': students
        }
    )


@router.get('/get_all_classes', tags=['class', 'student'])
async def get_all_classes(current_user: any = Depends(get_current_user)) -> Response:
    conn = pyodbc.connect(connection_string)
    cursor = conn.cursor()
    result = cursor.execute(f'''SELECT class_id, class_name, clv_name, class_desc 
                                FROM dbo.Classes
                                INNER JOIN dbo.ClassLevels
                                ON dbo.Classes.clv_id = dbo.ClassLevels.clv_id 
                    '''
                            )\
        .fetchall()
    if not result:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                'message': 'Class not found.'
            }
        )

    classes = {}
    for _class in result:
        classes[_class[0]] = {
            'class_name': _class[1],
            'class_level': _class[2],
            'description': _class[3]
        }

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=classes
    )


@router.post('/add_student', tags=['class', 'student'])
async def add_student(current_user: any = Depends(get_current_user), data: AddStudentObject = None) -> Response:
    conn = pyodbc.connect(connection_string)
    cursor = conn.cursor()
    cipher = Fernet(SECRET_KEY.encode())
    try:
        if cursor.execute(f''' SELECT student_username FROM dbo.Students WHERE student_username = '{data.fname}.{data.surname[0:3]}' ''').fetchone() is None:
            cursor.execute(f''' INSERT INTO dbo.Students 
                                            (student_username, student_fname, student_surname, student_points, student_hashed_pwd, student_net_points) 
                                VALUES ('{data.fname}.{data.surname[0:3]}', '{cipher.encrypt(data.fname.encode()).decode()}', '{cipher.encrypt(data.surname.encode()).decode()}', 0, '{cipher.encrypt('11110000'.encode()).decode()}', 0) ''')
            conn.commit()
        cursor.execute(
            f''' INSERT INTO dbo.StudentsClassesRelationship VALUES ('{data.fname}.{data.surname[0:3]}', '{data.class_id}', {data.inclass_id}) ''')
        conn.commit()
        conn.close()
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                'message': f'student {data.username} has been added to class {data.class_id}'
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


@router.get('/add_student/join/', tags=['class', 'student'])
async def add_student_by_link(class_id: str, current_user: any = Depends(get_current_user)) -> Response:
    conn = pyodbc.connect(connection_string)
    cursor = conn.cursor()
    try:
        cursor.execute(
            f''' UPDATE dbo.Students SET class_id = '{class_id}' WHERE student_username = '{current_user}' ''')
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                'message': f'student {current_user} has been added to class {class_id}'
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
