from datetime import datetime
from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer
from .body.token import UserKey
from .body.mission import CreateMission
from .crud import DynamoManager
import jwt
import os
from cryptography.fernet import Fernet
from dotenv import load_dotenv

load_dotenv()

router = APIRouter(prefix='/mission')
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/user/login")
SECRET_KEY = os.environ.get('key')
ALGORITHM = 'HS256'
crud = DynamoManager('Classes')

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
    tags: str = '[' + ', '.join(data.tags) + ']'
    is_success = crud.createMission(data.mission_class_id, data.mission_name, data.mission_points, data.mission_desc, data.mission_expired_date, data.tags, data.slot_amount)
    if is_success:
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
    else :
        return "Unable to proceed."
 

@router.delete('/delete_mission', tags=['missions'])
async def delete_mission(mission_name: str, _class: str, current_user: any = Depends(get_current_user)) -> Response:
    is_success = crud.deleteMission(_class, mission_name)
    if is_success:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                'message': f"successfully deleted mission {mission_name} "
            }
        )
    else:
        return 'Unable to proceed, please check your parameters or try again later.'


@router.put('/update_mission_detail', tags=['missions'])
async def update_mission(current_user: any = Depends(get_current_user), data: CreateMission = None) -> Response:
    is_success = crud.updateMissionsDetail(data.mission_class_id, data.mission_id, data.mission_name, data.mission_points, data.mission_desc, data.mission_expired_date, data.tags, data.slot_amount)
    if is_success:
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                'message': 'successfully editted.',
                'mission': data.__dict__
            }
        )
    else:
        return "Unable to proceed, please try again later or check your parameters."

@router.get('/change_mission_status', tags=['mission', 'student'])
async def change_mission_status(_class: str, student_id: str, mission_id: str, _status: str, current_user = Depends(get_current_user)) -> Response:
    is_sucess = crud.changeMissionStatus(_class, mission_id, student_id, _status)
    if is_sucess:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                'message': f'Change status of {mission_id} of {student_id}'
            }
        )
    else:
        return 'Unable to proceed.'