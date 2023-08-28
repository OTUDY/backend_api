from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer
from .body.token import UserKey
from .body.mission import CreateMission
from .crud import SQLiteManager
import jwt
import os

router = APIRouter(prefix='/mission')
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
def mission_root() -> Response:
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            'message': 'accessing mission root route.'
        }
    )

@router.post('/create', tags=['missions'])
def create_mission(current_user: UserKey = Depends(get_current_user), data: CreateMission = None) -> Response:
    query: str = f'''
        INSERT INTO Missions
        (mission_name, mission_desc, mission_points, mission_pic, mission_active_status)
        VALUES
        ("{data.mission_name}", "{data.mission_desc}", "{data.mission_points}", "{data.mission_pic}", {int(data.mission_active_status)})
    '''
    if crud.add(query):
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                'message': 'Successfully created the mission.',
                'mission_name': data.mission_name
            }
        )
    else:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                'message': 'Unable to proceed.',
            }
        )
    
@router.get('/get_mission_detail/{mission_name}', tags=['missions'])
def get_mission_detail(mission_name: str, current_user: UserKey = Depends(get_current_user)) -> Response:
    query: str = f'SELECT * FROM Missions WHERE mission_name = "{mission_name}"'
    result = crud.get(query)
    if not result:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                'message': 'Unable to proceed.'
            }
        )
    response_body = {
        'mission_name': result[0][0],
        'mission_desc': result[0][1],
        'mission_redeem_points': result[0][2],
        'mission_pic': result[0][3],
        'mission_active_status': result[0][4]
    }
    return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                'message': 'Successfully fetched',
                'data': response_body
            }
        )

@router.get('/get_all_missions', tags=['missions'])
def get_all_mission(current_user: any = Depends(get_current_user)) -> Response:
    _result = crud.get('SELECT * FROM Missions')
    missions = []
    for result in _result:
        missions.append({
                'mission_name': result[0],
                'mission_desc': result[1],
                'mission_redeem_points': result[2],
                'mission_pic': result[3],
                'mission_active_status': result[4]
            })
    return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={'missions': missions}
        )

@router.post('/update_mission_detail', tags=['missions'])
def update_mission(current_user: any = Depends(get_current_user), data: CreateMission = None) -> Response:
    query: str = f'''UPDATE Missions SET mission_desc = "{data.mission_desc}", 
                                         mission_points = {data.mission_points}, 
                                         mission_pic = "{data.mission_pic}", 
                                         mission_active_status = {int(data.mission_active_status)}
                     WHERE mission_name = "{data.mission_name}"'''
    crud.edit(query)
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            'message': 'successfully editted.',
            'mission': data.dict()
        }
    )