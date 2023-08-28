from fastapi import APIRouter, HTTPException, Response, status, Depends
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import jwt
from .crud import SQLiteManager as sql
from .body.user import RegisterForm, LoginForm
from .body.token import UserKey
from passlib.context import CryptContext
import os
import bcrypt
from .tool import Tool
from datetime import timedelta, datetime

router = APIRouter(prefix='/user')
crud = sql("default.sqlite")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/user/login")
SECRET = os.environ.get("key")
ALGORITHM = 'HS256'

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
    user_check: any = crud.get(f''' SELECT user_email FROM Users WHERE user_email = "{data.email}"''')
    if user_check:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                'message': 'This user has already registered.'
            }
        )
    _bytes = data.pwd.encode('utf-8')
    salt = bcrypt.gensalt()
    aff_id = crud.get(f"SELECT aff_id FROM Affiliations WHERE aff_name = '{data.affiliation}'")[0][0]
    if crud.add(f'''INSERT INTO 
                    Users
                    (
                        user_email, 
                        user_hashed_pwd, 
                        user_fname, 
                        user_surname, 
                        user_phone, 
                        role_id, 
                        aff_id,
                        user_points
                    )
                    VALUES
                    (
                        "{data.email}", 
                        "{bcrypt.hashpw(_bytes, salt)}", 
                        "{data.fname}", 
                        "{data.surname}", 
                        "{data.phone}", 
                        {data.role}, 
                        {aff_id},
                        0
                    )
                '''):
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
    user_data = Tool.get_user_detail(crud, form_data.username, login=True)
    access_token_expires = datetime.utcnow() + timedelta(minutes=15)
    access_token = Tool.create_token(
        data={"sub": form_data.username}, expires_delta=access_token_expires, secret=SECRET, algorithm='HS256'
    )
    return JSONResponse(status_code=status.HTTP_202_ACCEPTED, 
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
    data = Tool.get_user_detail(crud, current_user, False)
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            'message': 'Successfully fetched',
            'fetched_data': data
        }
    )
# ------------------

# ------ Edit ------
@router.post("/edit_user_detail", tags=['user'])
def edit_detail(current_user: any = Depends(get_current_user), edit_form: RegisterForm = None) -> Response:
    if current_user != edit_form.email:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                'message': 'Unauthorized.'
            }
        )
    aff_id = crud.get(f"SELECT aff_id FROM Affiliations WHERE aff_name = '{edit_form.affiliation}'")[0][0]
    query: str = f'''
                        UPDATE Users
                        SET user_email = "{edit_form.email}", 
                            user_fname="{edit_form.fname}", 
                            user_surname="{edit_form.surname}", 
                            user_phone="{edit_form.phone}", 
                            role_id={edit_form.role}, 
                            aff_id={aff_id} 
                        WHERE user_email = "{current_user}"
                  '''
    crud.edit(query)
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            'message': 'successfully editted.',
            'user': current_user,
            'data': edit_form.dict()
        }
    )
# -----------------

# ------ Update point ------
@router.get("/update_point", tags=['student'])
def update_point(user_email: str, points: int, current_user: UserKey = Depends(get_current_user)) -> Response:
    current_point = crud.get(f"SELECT user_points FROM Users WHERE user_email = '{user_email}'")[0][0]
    query: str = f'UPDATE Users SET user_points = {current_point + points} WHERE user_email = "{user_email}"'
    crud.edit(query)
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
@router.get("/update_class", tags=['student'])
def update_class(user_email: str, _class: str, current_user: UserKey = Depends(get_current_user)) -> Response:
    query: str = f'UPDATE Users user_student_class = "{_class}" WHERE user_email = "{user_email}'
    crud.edit(query)
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
    crud.add(f'INSERT INTO TeacherClassRelationship (class_id, teacher_id) VALUES ("{_class}", "{teacher_email}")')
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            'message': 'successfully assigned.',
            'teacher': current_user,
            'assigned_class': _class
        }
    )