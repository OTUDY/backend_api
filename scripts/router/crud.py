import boto3
from boto3.dynamodb.conditions import Key

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


                        
            