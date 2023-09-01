from fastapi import APIRouter, HTTPException, Response, status, Depends
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import jwt
from .body.user import RegisterForm, LoginForm
from .body.token import UserKey
from passlib.context import CryptContext
import os
from datetime import timedelta, datetime
from cryptography.fernet import Fernet
import pyodbc
from .tool import Tool

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
cipher = Fernet(SECRET.encode())
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
@router.post('/register/', tags=['user'])
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
    
    aff_id = cursor.execute(f"SELECT aff_id FROM dbo.Affiliations WHERE aff_name = '{data.affiliation}'").fetchone()[0]
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
@router.post("/login", tags=['user'])
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    conn = pyodbc.connect(connection_string)
    cursor = conn.cursor()
    data = cursor.execute(f'''SELECT student_email, student_hashed_pwd FROM dbo.Teachers WHERE user_email = '{form_data.username}' ''').fetchone()
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
@router.get("/get_user_detail", tags=['user'])
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
@router.put("/edit_user_detail", tags=['user'])
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
    aff_id = cursor.execute(f"SELECT aff_id FROM Affiliations WHERE aff_name = '{edit_form.affiliation}'").fetchone()[0]
    query: str = f'''
                        UPDATE Users
                        SET user_email = '{edit_form.email}', 
                            user_fname='{edit_form.fname}', 
                            user_surname='{edit_form.surname}', 
                            user_phone='{edit_form.phone}', 
                            role_id={edit_form.role}, 
                            aff_id={aff_id} 
                        WHERE user_email = '{current_user}'
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
    current_point = cursor.execute(f"SELECT user_points FROM Users WHERE user_email = '{user_email}'").fetchone()[0]
    query: str = f'''UPDATE Users SET user_points = {current_point + points} WHERE user_email = '{user_email}' '''
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
    query: str = f'''UPDATE Users user_student_class = '{_class}' WHERE user_email = '{user_email}' '''
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

@router.put('/assign_class', tags=['teacher'])
def assign_class(teacher_email: str, _class: str, current_user: UserKey = Depends(get_current_user)) -> Response:
    conn = pyodbc.connect(connection_string)
    cursor = conn.cursor()
    cursor.execute(f'''INSERT INTO TeacherClassRelationship (class_id, teacher_id) VALUES ('{_class}', '{teacher_email}')' ''')
    conn.close()
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            'message': 'successfully assigned.',
            'teacher': current_user,
            'assigned_class': _class
        }
    )

@router.get("/get_assigned_classes", tags=['user'])
def get_current_user_detail(current_user: UserKey = Depends(get_current_user)) -> Response:
    conn = pyodbc.connect(connection_string)
    cursor = conn.cursor()
    class_data: any = cursor.execute(
        f'''SELECT * FROM dbo.TeacherClassRelationship WHERE user_email = '{current_user}' '''
    ).fetchall()
    conn.close()
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=class_data
    )