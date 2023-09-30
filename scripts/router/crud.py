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
        try:
            result = []
            response = self._class_table.scan()
            if response.get('Items') is None:
                return False
            for _class in response['Items']:
                if id in _class['teachers']:
                    result.append(_class['id'])

            return result
        except Exception as e:
            return str(e)
        
    def updateClassDetail(self, data): 
        try:
            expression_attribute_names = {
                '#reserved_keyword': 'level',
                '#reserved_keyword2': 'description'  # Replace 'reserved_keyword' with your actual attribute name
            }
            response = self.table.update_item(
                Key={'id': data['id']},
                UpdateExpression=f'set #reserved_keyword=:l, #reserved_keyword2=:d',
                ExpressionAttributeNames=expression_attribute_names,
                ExpressionAttributeValues={
                    ':l': data['level'],
                    ':d': data['description']
                },
                ReturnValues="UPDATED_NEW"
            )
        except Exception as e:
            return str(e)
        else:
            return response['Attributes']
        
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
            new_status_item = {'studentId': {'S': student_id}, 'status': {'S': 'Doing'}, 'startedDate': {'S': str(datetime.now())}}
            
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
        response = self.table.get_item(
        Key={'id': class_id}
    )

        # Check if the item was found
        if 'Item' in response:
            item = response['Item']
            
            # Modify the list in the item to remove a value
            if 'students' in item:
                value_to_remove = id
                if value_to_remove in item['students']:
                    item['students'].remove(value_to_remove)
                    
                # Update the item in the DynamoDB table with the modified data
                self.table.update_item(
                    Key={
                        'id': class_id
                    },
                    UpdateExpression='SET students = :val',
                    ExpressionAttributeValues={
                        ':val': item['students']
                    }
                )
                return True
            else:
                return False
        else:
            return False
        
    def insertNonExistedStudent(self, data):
        self._user_table.put_item(Item=data)
    def addStudent(self, student, class_id, no):
        # Specify the value you want to insert into the list

        # Retrieve the item from the DynamoDB table
        response = self._class_table.get_item(
            Key={
                'id': class_id
            }
        )

        # Check if the item was found
        if 'Item' in response:
            item = response['Item']
            
            # Modify the list in the item to insert a value
            if 'students' not in item:
                item['students'] = []
            if 'studentsNo' not in item:
                item['studentsNo'] = {}

            item['students'].append(student)
            item['studentsNo'].update({
                student: no
            })
                
            # Update the item in the DynamoDB table with the modified data
            try:
                self._class_table.update_item(
                    Key={'id': class_id},
                    UpdateExpression='SET students = :val, studentsNo = :val2',
                    ExpressionAttributeValues={
                        ':val': item['students'],
                        ':val2': item['studentsNo']
                    }
                )
                return True
            except:
                return False
        else:
            return False
        
    def createMission(self, class_id, name, points, desc, expired_date, tags, amt):
        alphabets = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
        class_response = self._class_table.get_item(Key={'id': class_id})
        if 'Item' in class_response:
            data = class_response['Item']
            if 'missions' in data:
                data['missions'].append({
                    'id': ''.join(random.choice(alphabets) for i in range(5)),
                    'name': name,
                    'receivedPoints': points,
                    'description': desc,
                    'expiredDate': expired_date,
                    'tags': tags,
                    'slotsAmount': amt,
                    'onGoingStatus': []
                })
            else :
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
                else :
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
                        ExpressionAttributeValues = {
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
        
    def assignMission(self, class_id, mission_id, student_id):
        response = self._class_table.get_item(
            Key={
                'id': class_id
            }
        )
        if 'Item' in response:
            item = response['Item']
            if 'missions' in item:
                index = None
                for idx in item['missions']:
                    if item['missions'][idx]['id'] == mission_id:
                        index = idx
                if 'onGoingStatus' not in item['missions'][index]:
                    item['missions']['onGoingStatus'] = []
                else:
                    item['missions']['onGoingStatus'].append({
                        'studentId': student_id,
                        'startedDate': str(datetime.now()),
                        'status': 'Doing'
                    })
                try: 
                    self._class_table.update_item(
                        Key={'id': class_id},
                        UpdateExpression='SET missions = :val',
                        ExpressionAttributeValues = {
                            ':val': item['missions']
                        }
                    )
                    return True
                except:
                    return False
            else:
                return False
            
    def editStudentData(self, original_id, firstname, lastname, inclass_no, class_id):
        if original_id != f'{firstname}.{lastname}':
            print('Current key and Original are not matched.')
            response = self._user_table.get_item(
                Key={'id': original_id}
            )
            if 'Item' in response:
                item = response['Item']
                self._user_table.delete_item(
                    Key={
                        'id': original_id
                    }
                )
                item['id'] = f'{firstname}.{lastname}'
                self._user_table.put_item(
                    Item=item
                )
                response_class = self._class_table.get_item(Key={
                    'id': class_id
                })
        response_class = self._class_table.get_item(
            Key={
                'id': class_id
            }
        )
        if 'Item' in response_class:
            class_item = response_class['Item']
            for idx, x in enumerate(class_item['students']):
                if x == original_id:
                    class_item['students'][idx] = f'{firstname}.{lastname}'
                    break
            class_item['studentsNo'].pop(original_id)
            new_id = f'{firstname}.{lastname}'
            class_item['studentsNo'][new_id] = inclass_no
            if 'onGoingStatus' in class_item['missions']:
                for idx, x in enumerate(class_item['onGoingStatus']):
                    if x['studentId'] == original_id:
                        class_item['missions']['onGoingStatus'][idx]['studentId'] = f'{firstname}.{lastname}'
            try:
                self._class_table.update_item(
                    Key={
                        'id': class_id
                    },
                    UpdateExpression='SET students = :val1, missions = :val2, studentsNo = :val3',
                    ExpressionAttributeValues = {
                        ':val1': class_item['students'],
                        ':val2': class_item['missions'],
                        ':val3': class_item['studentsNo']
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
            reward_data = {
                'id': ''.join(random.choice(alphabets) for i in range(5)),
                'name': name,
                'description': desc,
                'spentPoints': spent_points,
                'expiredDate': expired_date,
                'slotsAmount': amt,
                'onGoingRedemption': []
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

