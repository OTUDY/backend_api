from fastapi import APIRouter, HTTPException, Response, status, Depends
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import jwt
from .body.user import RegisterForm, LoginForm, AddStudent, EditStudentObject
from .body.token import UserKey
from passlib.context import CryptContext
import os
from datetime import timedelta, datetime
from cryptography.fernet import Fernet
from .tool import Tool
from .crud import DynamoManager
from dotenv import load_dotenv

load_dotenv()

router = APIRouter(prefix='/user')
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/user/login")
SECRET = os.environ.get('key')
ALGORITHM = 'HS256'
crud = DynamoManager('Users')

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
@router.post('/user/register/', tags=['user'])
def register(data: RegisterForm) -> Response:
    ''' Param
    '''
    user_check: any = crud.get(id=data.email)
    if user_check is not None:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                'message': 'This user has already registered.'
            }
        )
    role = 'teacher'
    if data.role == 2:
        role = 'student'
    cipher = Fernet(SECRET.encode())
    try:
        crud.insert([{
            "id": data.email,
            'firstName': cipher.encrypt(data.fname.encode()).decode(),
            'lastName': cipher.encrypt(data.surname.encode()).decode(),
            'phone': cipher.encrypt(data.phone.encode()).decode(),
            'affiliation': data.affiliation,
            'role': role
        }])
        return JSONResponse(
                status_code=status.HTTP_201_CREATED,
                content={
                    'message': 'Successfully registered',
                    'user': data.email,
                    'role': data.role
                }
            )
    except Exception as e:
        return str(e)
# -------------------

# ------ Token ------
@router.post("/login", tags=['user'])
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    if form_data.client_id == '2':
        print('User is student.')
        data = crud.get(id=form_data.username)
    elif form_data.client_id == '1':
        print('User is teacher.')
        data = crud.get(id=form_data.username)
    cipher = Fernet(SECRET.encode())
    decoded_pwd: str = cipher.decrypt(data['hashedPassword'].encode()).decode()
    if data is None or form_data.password != decoded_pwd:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                'message': 'User has not registered.'
            }
        )
    access_token_expires = datetime.utcnow() + timedelta(minutes=43200)
    access_token = Tool.create_token(
        data={"sub": form_data.username}, expires_delta=access_token_expires, secret=SECRET, algorithm='HS256'
    )
    print(f'| System notification | : User {form_data.username} has logged in @ {datetime.utcnow()}.')
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
@router.get("/user/get_user_detail", tags=['user'])
def get_current_user_detail(current_user: UserKey = Depends(get_current_user)) -> Response:
    cipher = Fernet(SECRET.encode())
    try:
        response = crud.get(id=current_user)
        data = response['Item']
        for k, v in data.items():
            if k not in ['id', 'hashedPassword', 'affiliation', 'role', 'points', 'netPoints']:
                data[k] = cipher.decrypt(v.encode()).decode()
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=data
        )
    except Exception as e:
        return str(e)
# ------------------

# ------ Edit ------
@router.put("/user/edit_user_detail", tags=['user'])
def edit_detail(current_user: any = Depends(get_current_user), edit_form: RegisterForm = None) -> Response:
    if current_user != edit_form.email:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                'message': 'Unauthorized.'
            }
        )
    cipher = Fernet(SECRET.encode())
    try:
        crud.updateUserDetail({
            "id": current_user,
            "firstName": cipher.encrypt(edit_form.fname.encode()).decode(),
            'lastName': cipher.encrypt(edit_form.surname.encode()).decode(),
            'hashedPassword': cipher.encrypt(edit_form.pwd.encode()).decode(),
            'phone': cipher.encrypt(edit_form.phone.encode()).decode(),
            'affiliation': edit_form.affiliation
        })
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                'message': 'successfully editted.',
                'user': current_user,
                'updated_data': edit_form.__dict__
            }
        )
    except Exception as e:
        return str(e)
# -----------------

@router.get("/teacher/get_assigned_classes", tags=['teacher'])
def get_current_user_detail(current_user: UserKey = Depends(get_current_user)) -> Response:
    if crud.getRole(current_user) == 'student':
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                'message': 'Only teacher can proceed this route.'
            }
        )
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            'classes': crud.getAssignedClasses(current_user)
        }
    )
    


    