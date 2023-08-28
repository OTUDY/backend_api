from .crud import SQLiteManager
from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer
from .body.classes import ClassCreationForm
import jwt
import os

router = APIRouter(prefix='/class')
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
def class_root() -> Response:
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            'message': 'accessing class root.'
        }
    )

@router.post('/create_class', tags=['class'])
def create_class(current_user: any = Depends(get_current_user), data: ClassCreationForm = None) -> Response:
    level_id = crud.get(f'SELECT clv_id FROM ClassLevels WHERE clv_name = "{data.level}"')[0][0]
    query: str = f'''
                        INSERT INTO Classes (class_id, class_name, clv_id, class_desc) 
                        VALUES ("{data.class_name}", "{data.class_name}", {level_id}, "{data.class_desc}")
                  '''
    crud.add(query)
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            'message': 'successfully created class.',
            'class': data.dict()
        }
    )

@router.post('/update_class_detail', tags=['class'])
def update_class_detail(current_user: any = Depends(get_current_user), data: ClassCreationForm = None) -> Response:
    level_id = crud.get(f'SELECT clv_id FROM ClassLevels WHERE clv_name = "{data.level}"')[0][0]
    query: str = f'''
                        UPDATE Classes SET clv_id = {level_id}, class_desc = "{data.class_desc}"
                        WHERE class_id = "{data.class_name}"
                  '''
    crud.edit(query)
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            'message': 'successfully updated class.',
            'class': data.dict()
        }
    )

@router.get('/assign_mission', tags=['class'])
def assign_mission(_class: str, mission_name: str, current_user: any = Depends(get_current_user)) -> Response:
    crud.add(f'INSERT INTO ClassMissionRelationship (class_id, mission_name) VALUES ("{_class}", "{mission_name}")')
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            'message': 'successfully assigned.',
            'class': _class,
            'mission': mission_name
        }
    )

@router.get('/all_classes', tags=['class'])
def get_all_classes(current_user: any = Depends(get_current_user)) -> Response:
    _result = crud.get('SELECT * FROM Classes')
    rewards = []
    for result in _result:
        rewards.append({
                'class_name': result[0],
                'class_desc': result[3],
                'class_level': crud.get(f'SELECT clv_name FROM ClassLevels WHERE clv_id = "{result[2]}"')[0][0]
            })
    return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={'classes': rewards}
        )