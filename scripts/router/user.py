from fastapi import APIRouter, HTTPException, Response, status, Depends
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import jwt
from .body.user import RegisterForm, LoginForm, AddStudent
from .body.token import UserKey
from passlib.context import CryptContext
import os
from datetime import timedelta, datetime
from cryptography.fernet import Fernet
import pyodbc
from .tool import Tool
# from dotenv import load_dotenv

# load_dotenv()

router = APIRouter(prefix='/user')
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/user/login")
SECRET = os.environ.get('key')
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
        payload = jwt.decode(token, SECRET, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        return username
    except jwt.PyJWTError:
        raise credentials_exception

# ------ index -------
@router.get("/")
def root() -> Response:
    content: dict = {
        "message": "Accessing user index route."
    }
    return JSONResponse(content=content)
# --------------------

# ------ Register ------
@router.post('/teacher/register/', tags=['user'])
def register(data: RegisterForm) -> Response:
    ''' Param
    '''
    conn = pyodbc.connect(connection_string)
    cursor = conn.cursor()
    user_check: any = cursor.execute(f"SELECT teacher_email FROM dbo.Teachers WHERE teacher_email = '{data.email}'").fetchone()

    #user_check: any = cursor.execute('SELECT * FROM dbo.Affiliations;')
    if user_check:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                'message': 'This user has already registered.'
            }
        )
    table = "dbo.Teachers"
    prefix = 'teacher'
    if data.role == 2:
        table = "dbo.Students"
        prefix = 'student'
    cipher = Fernet(SECRET.encode())
    aff_id = cursor.execute(f"SELECT aff_id FROM dbo.Affiliations WHERE aff_name = '{data.affiliation}'").fetchone()[0]
    if aff_id is None:
        cursor.execute(f'''INSERT INTO dbo.Affiliations (aff_name) VALUES ('{data.affiliation}')''')
        conn.commit()

        aff_id = cursor.execute(f''' SELECT aff_id FROM dbo.Affiliations WHERE aff_name = '{data.affiliation}' ''').fetchone()[0]
    cursor.execute(f'''INSERT INTO 
                    {table}
                    (
                        {prefix}_email, 
                        {prefix}_hashed_pwd, 
                        {prefix}_fname, 
                        {prefix}_surname, 
                        {prefix}_phone, 
                        role_id, 
                        aff_id
                    )
                    VALUES
                    (
                        '{data.email}', 
                        '{cipher.encrypt(data.pwd.encode()).decode()}', 
                        '{cipher.encrypt(data.fname.encode()).decode()}', 
                        '{cipher.encrypt(data.surname.encode()).decode()}', 
                        '{cipher.encrypt(data.phone.encode()).decode()}', 
                        {data.role}, 
                        {aff_id}
                    )
                ''')
    conn.commit()
    conn.close()
    return JSONResponse(
                status_code=status.HTTP_201_CREATED,
                content={
                    'message': 'Successfully registered',
                    'user': data.email,
                    'role': data.role
                }
            )
# -------------------

# ------ Token ------
@router.post("/login", tags=['user', 'teacher', 'student'])
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    conn = pyodbc.connect(connection_string)
    cursor = conn.cursor()
    data = ('test', 'test')
    if form_data.client_id == '2':
        print('User is student.')
        data = cursor.execute(f'''SELECT student_username, student_hashed_pwd FROM dbo.Students WHERE student_username = '{form_data.username}' ''').fetchone()
    elif form_data.client_id == '1':
        print('User is teacher.')
        data = cursor.execute(f'''SELECT teacher_email, teacher_hashed_pwd FROM dbo.Teachers WHERE teacher_email = '{form_data.username}' ''').fetchone()
    cipher = Fernet(SECRET.encode())
    decoded_pwd: str = cipher.decrypt(data[1].encode()).decode()
    if not data or form_data.password != decoded_pwd:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                'message': 'User has not registered.'
            }
        )
    access_token_expires = datetime.utcnow() + timedelta(minutes=15)
    access_token = Tool.create_token(
        data={"sub": form_data.username}, expires_delta=access_token_expires, secret=SECRET, algorithm='HS256'
    )
    print(f'| System notification | : User {form_data.username} has logged in @ {datetime.utcnow()}.')
    conn.close()
    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED, 
        content={
                    "message": "Login completed.", 
                    "access_token": access_token,
                    "token_type": "bearer",
                    'expired_time': str(access_token_expires)
        }
    )

# ------------------
@router.get("/teacher/get_teacher_detail", tags=['user', 'teacher'])
def get_current_user_detail(current_user: UserKey = Depends(get_current_user)) -> Response:
    conn = pyodbc.connect(connection_string)
    cursor = conn.cursor()
    user_data: any = cursor.execute(
        f'''SELECT dbo.Teachers.teacher_email, dbo.Teachers.teacher_fname, dbo.Teachers.teacher_surname,  dbo.Teachers.teacher_phone, dbo.Roles.role_name
            FROM dbo.Teachers 
            INNER JOIN dbo.Roles 
            ON dbo.Teachers.role_id = dbo.Roles.role_id
            WHERE teacher_email = '{current_user}'; '''
    ).fetchone()
    conn.close()
    cipher = Fernet(SECRET.encode())
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
        'email': user_data[0],
        'firstname': cipher.decrypt(user_data[1].encode()).decode(),
        'surname': cipher.decrypt(user_data[2].encode()).decode(),
        'phone': cipher.decrypt(user_data[3].encode()).decode(),
        'role': user_data[4]
    }
    )
# ------------------

# ------ Edit ------
@router.put("/teacher/edit_user_detail", tags=['user', 'teacher'])
def edit_detail(current_user: any = Depends(get_current_user), edit_form: RegisterForm = None) -> Response:
    if current_user != edit_form.email:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                'message': 'Unauthorized.'
            }
        )
    conn = pyodbc.connect(connection_string)
    cursor = conn.cursor()
    aff_id = cursor.execute(f"SELECT aff_id FROM dbo.Affiliations WHERE aff_name = '{edit_form.affiliation}'").fetchone()[0]
    cipher = Fernet(SECRET.encode())
    query: str = f'''
                        UPDATE dbo.Teachers
                        SET teacher_email = '{edit_form.email}',
                            teacher_hashed_pwd = '{cipher.encrypt(edit_form.pwd.encode()).decode()}', 
                            teacher_fname='{cipher.encrypt(edit_form.fname.encode()).decode()}', 
                            teacher_surname='{cipher.encrypt(edit_form.surname.encode()).decode()}', 
                            teacher_phone='{cipher.encrypt(edit_form.phone.encode()).decode()}', 
                            role_id={edit_form.role}, 
                            aff_id={aff_id} 
                        WHERE teacher_email = '{edit_form.email}'
                  '''
    cursor.execute(query)
    conn.commit()
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            'message': 'successfully editted.',
            'user': current_user,
            'updated_data': edit_form.__dict__
        }
    )
# -----------------

# ------ Update point ------
@router.get("/update_point", tags=['student'])
def update_point(user_email: str, points: int, current_user: UserKey = Depends(get_current_user)) -> Response:
    conn = pyodbc.connect(connection_string)
    cursor = conn.cursor()
    current_point = cursor.execute(f"SELECT student_points FROM dbo.Students WHERE student_username = '{user_email}'").fetchone()[0]
    query: str = f'''UPDATE dbo.Students SET student_points = {current_point + points} WHERE student_username = '{user_email}' '''
    cursor.execute(query)
    conn.commit()
    conn.close()
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            'message': 'successfully editted.',
            'user': current_user,
            'current_points': current_point + points
        }
    )
# --------------------------

# ------ Update class ------
@router.put("/update_class", tags=['student'])
def update_class(user_email: str, _class: str, current_user: UserKey = Depends(get_current_user)) -> Response:
    query: str = f'''UPDATE dbo.Students SET class_id = '{_class}' WHERE student_username = '{user_email}' '''
    conn = pyodbc.connect(connection_string)
    cursor = conn.cursor()
    cursor.execute(query)
    conn.commit()
    conn.close()
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            'message': 'successfully editted.',
            'user': current_user,
            'current_class': _class
        }
    )
# --------------------------

@router.get('/assign_class', tags=['teacher'])
def assign_class(teacher_email: str, _class: str, current_user: UserKey = Depends(get_current_user)) -> Response:
    conn = pyodbc.connect(connection_string)
    cursor = conn.cursor()
    cursor.execute(f'''INSERT INTO dbo.TeachersClassesRelationship (class_id, teacher_id) VALUES ('{_class}', '{teacher_email}')' ''')
    conn.close()
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            'message': 'successfully assigned.',
            'teacher': current_user,
            'assigned_class': _class
        }
    )

@router.get("/teacher/get_assigned_classes", tags=['user', 'teacher'])
def get_current_user_detail(current_user: UserKey = Depends(get_current_user)) -> Response:
    conn = pyodbc.connect(connection_string)
    cursor = conn.cursor()
    class_data: any = cursor.execute(
        f''' SELECT dbo.TeachersClassesRelationship.class_id, dbo.TeachersClassesRelationship.teacher_id, dbo.Classes.class_desc, dbo.ClassLevels.clv_name
                            FROM dbo.TeachersClassesRelationship 
                            INNER JOIN dbo.Classes
                            ON dbo.TeachersClassesRelationship.class_id = dbo.Classes.class_id
                            INNER JOIN dbo.ClassLevels
                            ON dbo.Classes.clv_id = dbo.ClassLevels.clv_id
                            WHERE dbo.TeachersClassesRelationship.teacher_id = '{current_user}' ''' 
    ).fetchall()
    conn.close()
    classes = []
    for j in class_data:
        class_object = {
            'class_name': j[0],
            'teacher': j[1],
            'class_desc': j[2],
            'class_level': j[3]
        }
        classes.append(class_object)
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={'classes': classes}
    )

@router.post('/student/register', tags=['student'])
def add_user(student_info: AddStudent) -> Response:
    conn = pyodbc.connect(connection_string)
    cursor = conn.cursor()
    cipher = Fernet(SECRET)
    student_check = cursor.execute(f''' SELECT student_username FROM dbo.Students WHERE student_username = '{student_info.username}' ''').fetchone()
    if student_check:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                'message': 'User has been registered, proceed to login.'
            }
        )
    cursor.execute(f'''
                       INSERT INTO dbo.Students
                       VALUES (
                          '{student_info.username}',
                          '{cipher.encrypt(student_info.firstname.encode()).decode()}',
                          '{cipher.encrypt(student_info.surname.encode()).decode()}',
                          0,
                          '{student_info.class_name}',
                          '{cipher.encrypt(student_info.pwd.encode()).decode()}'
                       ) 
                   ''')
    conn.commit()
    conn.close()
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            'message': 'created student account',
            'student_username': student_info.username
        }
    )

@router.get('/student/leaderboard', tags=['reward', 'student', 'redemption'])
async def get_leaderboard(current_user: any = Depends(get_current_user)) -> Response:
    conn = pyodbc.connect(connection_string)
    cursor = conn.cursor()
    result = cursor.execute('''  SELECT student_username, student_points
                                 FROM dbo.Students
                                 ORDER BY student_points DESC
                            ''')
    leaderboard = {}
    for score in result:
        leaderboard[score[0]] = {
            'points': score[1]
        }
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=leaderboard
    )
    