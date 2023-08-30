from .crud import SQLManager
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
crud = SQLManager('Driver={ODBC Driver 17 for SQL Server};Server=tcp:%s,1433;Database=%s;Uid=%s;Pwd=%s;Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;'%(os.environ.get('SQL_SERVER'), os.environ.get('SQL_DB'), os.environ.get('SQL_USERNAME'), os.environ.get('SQL_PASSWORD')))

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
    query: str = f'''
                        INSERT INTO Classes (class_id, class_name, clv_id, class_desc) 
                        VALUES ('{data.class_name}', '{data.class_name}', {data.level}, '{data.class_desc}')
                  '''
    crud.operate(query, 'add')
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            'message': 'successfully created class.',
            'class': data.__dict__
        }
    )

@router.put('/update_class_detail', tags=['class'])
def update_class_detail(current_user: any = Depends(get_current_user), data: ClassCreationForm = None) -> Response:
    query: str = f'''
                        UPDATE Classes SET clv_id = {data.level}, class_desc = '{data.class_desc}'
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

@router.get('/all_classes', tags=['class'])
def get_all_classes(current_user: any = Depends(get_current_user)) -> Response:
    _result = crud.get('''SELECT class_name, class_desc, clv_name 
                          FROM dbo.Classes 
                          INNER JOIN dbo.ClassLevels
                          ON dbo.Classes.clv_id = dbo.ClassLevels.clv_id
                          ''')
    classes = []
    for result in _result:
        classes.append({
                'class_name': result[0],
                'class_desc': result[1],
                'class_level': result[2]
            })
    return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={'classes': classes}
        )