import random
import boto3
from boto3.dynamodb.conditions import Key
from datetime import datetime


class DynamoManager:
    def __init__(self, table: str) -> None:
        self.db = boto3.resource('dynamodb')
        self._table = table
        self.table = self.db.Table(table)
        self._user_table = self.db.Table('Users')
        self._class_table = self.db.Table('Classes')

    def get(self, all: bool = False, id: str = None) -> list:
        response_data = None
        if all:
            response: dict = self.table.scan()
            data_count: int = response['Count']
            data: list = response['Items']
            if data_count > 0:
                response_data = data.copy()
        else:
            response = self.table.get_item(Key={
                'id': id
            })
            if response.get('Item') is not None:
                response_data = response['Item']
        return response_data

    def getCurrentUserDetail(self, id):
        return self._user_table.get_item(Key={'id': id}).get('Item')

    def insert(self, items: list) -> any:
        returned_data = {
            'missingStudents': [],
            'missionTeachers': []
        }
        if self._table == "Users":
            for item in items:
                self.table.put_item(Item=item)
        elif self._table == 'Classes':
            for index, item in enumerate(items):
                for student in item['students']:
                    if self._user_table.get_item(Key={
                        'id': student
                    }).get('Item') is None:
                        returned_data['missingStudents'].append(student)
                        _idx = items[index]['students'].index(student)
                        items[index]['students'].pop(_idx)
                for teacher in item['teachers']:
                    if self._user_table.get_item(Key={
                        'id': teacher
                    }).get('Item') is None:
                        returned_data['missionTeachers'].append(teacher)
                        _idx = items[index]['teachers'].index(student)
                        items[index]['teachers'].pop(_idx)
                self.table.put_item(Item=item)

        return returned_data

    def updateUserDetail(self, item) -> any:
        try:
            response = self.table.update_item(
                Key={'id': item['id']},
                UpdateExpression=f'set firstName=:f, lastName=:s, hashedPassword=:p, phone=:ph, affiliation=:af',
                ExpressionAttributeValues={
                    ':f': item['firstName'],
                    ':s': item['lastName'],
                    ':p': item['hashedPassword'],
                    ':ph': item['phone'],
                    ':af': item['affiliation']
                },
                ReturnValues="UPDATED_NEW"
            )
        except Exception as e:
            return str(e)
        else:
            return response['Attributes']

    def updateStudentPoint(self, points: int) -> bool:
        pass

    def getRole(self, id: str):
        try:
            response = self.table.get_item(Key={
                'id': id
            })
            if response.get('Item') is None:
                return False
            return response['Item']['role']
        except Exception as e:
            return str(e)

    def getAssignedClasses(self, id):
        response = self._class_table.scan()
        assigned_classes = []
        if 'Items' in response:
            items = response['Items']
            for _c in items:
                if 'teachers' in _c:
                    if id in _c['teachers']:
                        data = {
                            'id': _c['id'],
                            'name': _c['name'],
                            'totalStudents': len(_c['students']),
                            'description': _c['description'],
                            'level': _c['level'],
                            'teachers': _c['teachers']
                        }
                        assigned_classes.append(data)
            return assigned_classes
        else:
            return None

    def updateClassDetail(self, data):
        response = self._class_table.get_item(
            Key={'id': data['id']}
        )
        expression_attribute_names = {
            '#reserved_keyword': 'name',
            '#reserved_keyword2': 'level',
            '#reserved_keyword3': 'description'    # Replace 'reserved_keyword' with your actual attribute name
        }
        if 'Item' in response:
            self._class_table.update_item(
                Key={
                    "id": data['id']
                },
                UpdateExpression='SET #reserved_keyword=:n, #reserved_keyword2=:l, #reserved_keyword3=:d',
                ExpressionAttributeNames=expression_attribute_names,
                ExpressionAttributeValues={
                    ':n': data['name'],
                    ':l': data['level'],
                    ":d": data['description']
                }
            )
            return True
        else:
            return False

    def assignMission(self, class_id, student_id, mission_id):
        # Retrieve the item from DynamoDB
        response = self.table.get_item(
            TableName='YourTableName',
            Key={
                'id': {'S': class_id}
            }
        )
        is_added = False
        # Check if the item exists
        if 'Item' in response:
            # Extract the item
            item = response['Item']

            # Modify the 'missions' list by appending the new item to 'onGoingStatus'
            new_status_item = {'studentId': {'S': student_id}, 'status': {
                'S': 'Doing'}, 'startedDate': {'S': str(datetime.now())}}

            # Check if 'missions' key exists and is a list
            if 'missions' in item and 'L' in item['missions']:
                missions_list = item['missions']['L']

                # Find the mission you want to update
                for mission in missions_list:
                    if 'M' in mission and 'id' in mission['M'] and mission['M']['id']['S'] == mission_id:
                        # Check if 'onGoingStatus' key exists and is a list
                        if 'onGoingStatus' in mission['M'] and 'L' in mission['M']['onGoingStatus']:
                            onGoingStatus_list = mission['M']['onGoingStatus']['L']

                            # Append the new status item to the 'onGoingStatus' list
                            onGoingStatus_list.append({'M': new_status_item})

                            # Update the DynamoDB item with the modified 'missions' list
                            self.table.update_item(
                                Key={
                                    'id': {'S': class_id}
                                },
                                UpdateExpression='SET missions = :m',
                                ExpressionAttributeValues={
                                    ':m': {'L': missions_list}
                                }
                            )
                            is_added = True
                            break
        return is_added

    def deleteClass(self, id):
        self.table.delete_item(Key={
            'id': id
        })

    def getClassDetail(self, id):
        response = self._class_table.get_item(Key={
            'id': id
        })
        return response

    def getStudentDetail(self, id):
        return self._user_table.get_item(Key={
            'id': id
        })

    def removeStudent(self, id, class_id):
        response = self._class_table.get_item(
            Key={'id': class_id}
        )
        if 'Item' in response:
            item = response['Item']
            index = None
            for x in range(len(item['students'])):
                if item['students'][x]['id'] == id:
                    index = x
                    break
            item['students'].pop(index)
            for i in range(len(item['missions'])):
                for j in range(len(item['missions'][i]['onGoingStatus'])):
                    if item['missions'][i]['onGoingStatus'][j]['id'] == id:
                        item['missions'][i]['onGoingStatus'].pop(j)
                        break
            for z in range(len(item['rewards'])):
                for y in range(len(item['rewards'][z]['onGoingRedemption'])):
                    if item['rewards'][z]['onGoingRedemption'][y]['id'] == id:
                        item['rewards'][z]['onGoingRedemption'].pop(y)
                        break
            try:
                self._class_table.update_item(
                    Key={'id': class_id},
                    UpdateExpression="SET students = :val, missions = :val2, rewards = :val3",
                    ExpressionAttributeValues={
                        ':val': item['students'],
                        ':val2': item['missions'],
                        ':val3': item['rewards']
                    }
                )
                return True
            except:
                return False
        else:
            return False
    def insertNonExistedStudent(self, data):
        self._user_table.put_item(Item=data)

    def addStudent(self, id, fname, lname, class_id, no):
        response = self._class_table.get_item(
            Key={'id': class_id}
        )
        if 'Item' in response:
            item = response['Item']
            if 'students' not in item:
                item['students'] = []
            item['students'].append({
                'id': id,
                'firstName': fname,
                'lastName': lname,
                'points': 0,
                'netPoints': 0,
                'inClassId': no 
            })
            if 'missions' in item:
                for idx, vlaue in enumerate(item['missions']):
                    item['missions'][idx]['onGoingStatus'].append({
                        'id': id,
                        'firstName': fname,
                        'lastName': lname,
                        'inClassId': no,
                        'status': 'ยังไม่ได้รับมอบหมาย'
                    }
                )
            if 'rewards' in item:
                for idx, vlaue in enumerate(item['rewards']):
                    item['rewards'][idx]['onGoingRedemption'].append({
                        'id': id,
                        'firstName': fname,
                        'lastName': lname,
                        'inClassId': no,
                        'status': 'ยังไม่ได้ทำการแลก'
                    }
                )
            try:
                self._class_table.update_item(
                    Key={'id': class_id},
                    UpdateExpression='SET students = :val, missions = :val2, rewards = :val3',
                    ExpressionAttributeValues={
                        ':val': item['students'],
                        ':val2': item['missions'],
                        ':val3': item['rewards']

                    }
                )
                return True
            except:
                return False
        else:
            return True

    def createMission(self, class_id, name, points, desc, expired_date, tags, amt):
        alphabets = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
        class_response = self._class_table.get_item(Key={'id': class_id})
        if 'Item' in class_response:
            data = class_response['Item']
            if 'missions' in data:
                on_going_status = []
                for j in data['students']:
                    to_append_data = {
                        'id': j['id'],
                        'firstName': j['firstName'],
                        'lastName': j['lastName'],
                        'inClassId': j['inClassId'],
                        'status': 'ยังไม่ได้รับมอบหมาย'
                    }
                    on_going_status.append(to_append_data)

                data['missions'].append({
                    'id': ''.join(random.choice(alphabets) for i in range(5)),
                    'name': name,
                    'receivedPoints': points,
                    'description': desc,
                    'expiredDate': expired_date,
                    'tags': tags,
                    'slotsAmount': amt,
                    'onGoingStatus': on_going_status
                })
            else:
                data['missions'] = []

            self._class_table.update_item(
                Key={'id': class_id},
                UpdateExpression='SET missions = :val',
                ExpressionAttributeValues={
                    ':val': data['missions']
                }
            )
            return True
        else:
            return False

    def deleteMission(self, class_id, id):
        response = self._class_table.get_item(
            Key={'id': class_id}
        )
        if 'Item' in response:
            item = response['Item']
            if 'missions' not in item:
                return False
            else:
                index = None
                for j in range(len(item['missions'])):
                    if item['missions'][j]['id'] == id:
                        index = j
                        break
                if index is None:
                    return False
                else:
                    try:
                        item['missions'].pop(index)
                        self._class_table.update_item(
                            Key={'id': class_id},
                            UpdateExpression='SET missions = :val',
                            ExpressionAttributeValues={
                                ':val': item['missions']
                            }
                        )
                        return True
                    except:
                        return False

    def updateMissionsDetail(self, class_id, id, name, points, desc, expired_date, tags, amt):
        response = self._class_table.get_item(
            Key={
                'id': class_id
            }
        )
        if 'Item' in response:
            item = response['Item']
            if 'missions' in item:
                index = None
                for idx in range(len(item['missions'])):
                    if item['missions'][idx]['id'] == id:
                        index = idx
                        break
                item['missions'][index]['name'] = name
                item['missions'][index]['receivedPoints'] = points
                item['missions'][index]['description'] = desc
                item['missions'][index]['expiredDate'] = expired_date
                item['missions'][index]['tags'] = tags
                item['missions'][index]['slotsAmount'] = amt

                try:
                    self._class_table.update_item(
                        Key={
                            "id": class_id
                        },
                        UpdateExpression='SET missions = :val',
                        ExpressionAttributeValues={
                            ':val': item['missions']
                        }
                    )
                    return True
                except:
                    return False
            else:
                return False
        else:
            return False

    def changeMissionStatus(self, class_id, mission_id, student_id, status):
        response = self._class_table.get_item(
            Key={
                'id': class_id
            }
        )
        if 'Item' in response:
            item = response['Item']
            received_points = None
            for x in range(len(item['missions'])):
                if item['missions'][x]['id'] == mission_id:
                    received_points = item['missions'][x]['receivedPoints']
                    if status == 'เสร็จสิ้นภารกิจ':
                        if item['missions'][x]['slotsAmount'] <= 0:
                            return False
                        item['missions'][x]['slotsAmount'] -= 1
                    for idx, j in enumerate(item['missions'][x]['onGoingStatus']):
                        if j['id'] == student_id:
                            item['missions'][x]['onGoingStatus'][idx]['status'] = status
                            break
            if status == 'เสร็จสิ้นภารกิจ':
                for x in range(len(item['students'])):
                    if item['students'][x]['id'] == student_id:
                        item['students'][x]['points'] += received_points
                        item['students'][x]['netPoints'] += received_points
            try:
                self._class_table.update_item(
                    Key={'id': class_id},
                    UpdateExpression='SET missions = :val, students = :val2',
                    ExpressionAttributeValues={
                        ':val': item['missions'],
                        ':val2': item['students']
                    }
                )
                return True
            except:
                return False
        else:
            return False
            
    def editStudentData(self, id, firstname, lastname, inclass_no, class_id):
        response = self._class_table.get_item(
            Key={
                'id': class_id
            }
        )
        if 'Item' in response:
            item = response['Item']
            for idx in range(len(item['students'])):
                if item['students'][idx]['id'] == id:
                    item['students'][idx]['firstName'] = firstname
                    item['students'][idx]['lastName'] = lastname
                    item['students'][idx]['inClassId'] = inclass_no
                    break
            try:
                self._class_table.update_item(
                    Key={'id': class_id},
                    UpdateExpression='SET students = :val',
                    ExpressionAttributeValues = {
                        ':val': item['students']
                    }
                )
                return True
            except:
                return False
        else:
            return False

    def createReward(self, class_id, name, desc, spent_points, expired_date, amt):
        alphabets = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
        response = self._class_table.get_item(
            Key={
                'id': class_id
            }
        )
        if 'Item' in response:
            item = response['Item']
            if 'rewards' not in item:
                item['rewards'] = []
            on_going_status = []
            for j in item['students']:
                to_append_data = {
                        'id': j['id'],
                        'firstName': j['firstName'],
                        'lastName': j['lastName'],
                        'inClassId': j['inClassId'],
                        'status': 'ยังไม่ได้ทำการแลก'
                    }
            on_going_status.append(to_append_data)

            reward_data = {
                'id': ''.join(random.choice(alphabets) for i in range(5)),
                'name': name,
                'description': desc,
                'spentPoints': spent_points,
                'expiredDate': expired_date,
                'slotsAmount': amt,
                'onGoingRedemption': on_going_status
            }
            item['rewards'].append(reward_data)

            try:
                self._class_table.update_item(
                    Key={
                        'id': class_id
                    },
                    UpdateExpression='SET rewards = :val',
                    ExpressionAttributeValues={
                        ':val': item['rewards']
                    }
                )
                return True
            except:
                return False
        return False

    def deleteReward(self, class_id, id):
        response = self._class_table.get_item(
            Key={
                'id': class_id
            }
        )
        if 'Item' in response:
            item = response['Item']
            if 'rewards' in item:
                index = None
                for idx, reward in enumerate(item['rewards']):
                    if reward['id'] == id:
                        index = idx
                        break
                item['rewards'].pop(index)
                try:
                    self._class_table.update_item(
                        Key={'id': class_id},
                        UpdateExpression='SET rewards = :val',
                        ExpressionAttributeValues={
                            ':val': item['rewards']
                        }
                    )
                    return True
                except:
                    return False
            else:
                return False
        else:
            return False

    def updateRewardDetail(self, class_id, id, name, desc, spent_points, expired_date, amt):
        response = self._class_table.get_item(
            Key={
                'id': class_id
            }
        )
        if 'Item' in response:
            item = response['Item']
            if 'rewards' in item:
                index = None
                for idx, reward in enumerate(item['rewards']):
                    if reward['id'] == id:
                        index = idx
                        break
                item['rewards'][index]['name'] = name
                item['rewards'][index]['description'] = desc
                item['rewards'][index]['spentPoints'] = spent_points
                item['rewards'][index]['expiredDate'] = expired_date
                item['rewards'][index]['slotsAmount'] = amt
                try:
                    self._class_table.update_item(
                        Key={
                            'id': class_id
                        },
                        UpdateExpression='SET rewards = :val',
                        ExpressionAttributeValues={
                            ':val': item['rewards']
                        }
                    )
                    return True
                except:
                    return False
            else:
                return False
        else:
            return False
        
    def changeRedeemStatus(self, id, class_id, student_id, status):
        response = self._class_table.get_item(
            Key={'id': class_id}
        )
        if 'Item' in response:
            item = response['Item']
            spent_points = None
            for idx, value in enumerate(item['rewards']):
                if value['id'] == id:
                    spent_points = value['spentPoints']
                    slot_count = value['slotsAmount']
                    if status == 'แลกเสร็จสิ้น':
                        if slot_count <= 0:
                            return False
                        item['rewards'][idx]['slotsAmount'] -= 1
                    for idx2, redeem in enumerate(item['rewards'][idx]['onGoingRedemption']):
                        if redeem['id'] == student_id:
                            item['rewards'][idx]['onGoingRedemption'][idx2]['status'] = status
            for i in range(len(item['students'])):
                if item['students'][i]['id'] == student_id:
                    item['students'][i]['points'] -= spent_points
            try:
                self._class_table.update_item(
                    Key={'id': class_id},
                    UpdateExpression='SET rewards = :val, students = :val2',
                    ExpressionAttributeValues={
                        ':val': item['rewards'],
                        ':val2': item['students']
                    }
                )
                return True
            except:
                return False
        else:
            return False
        
    def getStudentPoint(self, class_id, id):
        response = self._class_table.get_item(
            Key={'id': class_id}
        )
        if 'Item' in response:
            item = response['Item']
            for j in item['students']:
                if j['id'] == id:
                    return j['points']
        return None
