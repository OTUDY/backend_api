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
            response = self.table.update_item(
                Key={'id': data['id']},
                UpdateExpression=f'set level=:l, description=:d',
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
        response = self.table.get_item(Key={
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
                if value_to_remove in item['students']['L']:
                    item['students']['L'].remove({'S': value_to_remove})
                    
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
    def addStudent(self, student, class_id):
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
            if 'students' in item:
                if 'L' not in item['students']:
                    item['students']['L'] = []
                item['students']['L'].append({'S': student})
                
                # Update the item in the DynamoDB table with the modified data
                self._class_table.update_item(
                    Key={'id': class_id},
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
