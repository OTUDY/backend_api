from .crud import DynamoManager
from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer
from .body.classes import ClassCreationForm, EditStudentForm
from .body.user import AddStudentObject
import jwt
import os
from .body.user import AddStudent
from cryptography.fernet import Fernet
from typing import List
from dotenv import load_dotenv
import random

load_dotenv()

router = APIRouter(prefix='/class')
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/user/login")
SECRET_KEY = os.environ.get('key')
ALGORITHM = 'HS256'
crud = DynamoManager('Classes')
alphabets = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'

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
    alphabets = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
    _data = [{
        'id': ''.join(random.choice(alphabets) for i in range(8)),
        'name': data.class_name,
        'level': data.level,
        'description': data.class_desc,
        'students': [],
        'studentsNo': {},
        'missions': [],
        'rewards': [],
        'activities': [],
        'items': [],
        'teachers': [current_user]
    }]
    try:
        crud.insert(_data)
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                'message': 'successfully created class.',
                'class': _data,
                'assigned_teacher': current_user
            }
        )
    except Exception as e:
        return str(e)


@router.put('/update_class_detail', tags=['class'])
def update_class_detail(current_user: any = Depends(get_current_user), data: ClassCreationForm = None) -> Response:
    try: 
        _data = {   
            'id': data.class_name,
            'level': data.level,
            'description': data.class_desc
        }
        response = crud.updateClassDetail(_data)
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                'message': 'successfully updated class.',
                'class': response
            }
        )
    except Exception as e:
        return str(e)


@router.put('/assign_mission', tags=['class'])
def assign_mission(_class: str, mission_name: str, student_id: str, current_user: any = Depends(get_current_user)) -> Response:
    success = crud.assignMission(_class, student_id, mission_name)
    if success:
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                'message': 'successfully assigned.',
                'class': _class,
                'mission': mission_name
            }
        )
    else :
        return "Unable to assign, mission is not found."


@router.delete('/delete_class', tags=['class'])
async def delete_class(_class: str, current_user: any = Depends(get_current_user)) -> Response:
    try:
        crud.deleteClass(_class)
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                'message': 'successfully deleted',
                'class': _class,
            }
        )
    except Exception as e:
        return str(e)


@router.get('/get_class_meta_data', tags=['class'])
def get_meta_data(_class: str, current_user: any = Depends(get_current_user)) -> Response:
    cipher = Fernet(SECRET_KEY.encode())
    try:
        data = crud.getClassDetail(_class)
        if 'Item' in data:
            _d = data['Item']
            response = {
                'id': _d['id'],
                'name': _d['name'],
                'level': _d['level'],
                'students': _d['students'],
                'missions': _d['missions'],
                'rewards': _d['rewards'],
                'activities': _d['activities'],
                'items': _d['items'],
                'teachers': _d['teachers'],
                'description': _d['description']
            }
            for idx in range(len(response['missions'])):
                for x in range(len(response['missions'][idx]['onGoingStatus'])):
                    response['missions'][idx]['onGoingStatus'][x]['inClassId'] = int(response['missions'][idx]['onGoingStatus'][x]['inClassId'])
                    response['missions'][idx]['onGoingStatus'][x]['firstName'] = cipher.decrypt(response['missions'][idx]['onGoingStatus'][x]['firstName'].encode()).decode()
                    response['missions'][idx]['onGoingStatus'][x]['lastName'] = cipher.decrypt(response['missions'][idx]['onGoingStatus'][x]['lastName'].encode()).decode()
            for idx in range(len(response['students'])):
                response['students'][idx]['inClassId'] = int(response['students'][idx]['inClassId'])
                response['students'][idx]['points'] = int(response['students'][idx]['points'])
                response['students'][idx]['netPoints'] = int(response['students'][idx]['netPoints'])
                response['students'][idx]['firstName'] = cipher.decrypt(response['students'][idx]['firstName'].encode()).decode()
                response['students'][idx]['lastName'] = cipher.decrypt(response['students'][idx]['lastName'].encode()).decode()
            if len(_d['missions']) > 0:
                for idx, _ in enumerate(_d['missions']):
                    _d['missions'][idx]['receivedPoints'] = int(_d['missions'][idx]['receivedPoints'])
                    _d['missions'][idx]['slotsAmount'] = int(_d['missions'][idx]['slotsAmount'])
                    response['missions'] = _d['missions']
            if len(_d['rewards']) > 0:
                for idx, _ in enumerate(_d['rewards']):
                    _d['rewards'][idx]['spentPoints'] = int(_d['rewards'][idx]['spentPoints'])
                    _d['rewards'][idx]['slotsAmount'] = int(_d['rewards'][idx]['slotsAmount'])
                    for idx2, _ in enumerate(_d['rewards'][idx]['onGoingRedemption']):
                        _d['rewards'][idx]['onGoingRedemption'][idx2]['firstName'] = cipher.decrypt(_d['rewards'][idx]['onGoingRedemption'][idx2]['firstName'].encode()).decode()
                        _d['rewards'][idx]['onGoingRedemption'][idx2]['lastName'] = cipher.decrypt(_d['rewards'][idx]['onGoingRedemption'][idx2]['lastName'].encode()).decode()
                        _d['rewards'][idx]['onGoingRedemption'][idx2]['inClassId'] = int(_d['rewards'][idx]['onGoingRedemption'][idx2]['inClassId'])
                    response['rewards'] = _d['rewards']
            #print(response)
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content=response
            )
    except Exception as e:
        return str(e)


@router.put('/remove_students', tags=['class', 'student'])
async def remove_students(students: List[str], _class: str ,current_user: any = Depends(get_current_user)) -> Response:
    success_removed_list = []
    for j in students:
        is_success = crud.removeStudent(j, _class)
        if is_success:
            success_removed_list.append(j)
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            'removed_students': success_removed_list
        }
    )

@router.post('/add_student', tags=['class', 'student'])
async def add_student(current_user: any = Depends(get_current_user), data: AddStudentObject = None) -> Response:
    cipher = Fernet(SECRET_KEY.encode())
    is_success = crud.addStudent(''.join(random.choice(alphabets) for _ in range(6)),
                                 cipher.encrypt(data.fname.encode()).decode(),
                                 cipher.encrypt(data.surname.encode()).decode(),
                                 data.class_id,
                                 data.inclass_id)
    if is_success:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                    'message': 'successfully added student'
            }
        )
    else :
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                    'message': 'Unabled to add student'
                }
            )

@router.put('/edit_student_detail', tags=['student'])
async def edit_student_detail(current_user = Depends(get_current_user), data: EditStudentForm = None) -> Response:
    cipher = Fernet(SECRET_KEY.encode())
    firstname = cipher.encrypt(data.firstname.encode()).decode()
    lastname = cipher.encrypt(data.lastname.encode()).decode()
    if crud.editStudentData(data.original_id, firstname, firstname, data.inclass_no, data.class_id):
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                'message': 'successfully editted the data of the student.'
            }
        )
    else:
        return "Unable to proceed"
