# import sqlite3
# import json
# import pyodbc as odbc
# from datetime import datetime

# class SQLiteManager:
#     def __init__(self : object, db_name : str) -> None:
#         self.connection = sqlite3.connect(db_name, check_same_thread=False)
#         self.cursor = self.connection.cursor()

#     def get(self : object, query : str) -> list:
#         return self.cursor.execute(query).fetchall()
    
#     def add(self : object, query : str) -> dict:
#         self.cursor.execute(query)
#         self.connection.commit()
#         return True
    
#     def edit(self : object, query : str) -> dict:
#         self.cursor.execute(query)
#         self.connection.commit()
#         return {
#             'status': 0,
#             'detail': {
#                 'message': 'Successfully editted item(s) in database.',
#                 'query' : query 
#             }
#         }
    
#     def delete(self : object, query : str) -> dict:
#         try :
#             self.cursor.execute(query)
#             self.connection.commit()
#         except:
#             raise Exception('Error: SQL Query or Syntax is not in the right format, please look forward to check.')
#         return {
#             'status': 0,
#             'detail': {
#                 'message': 'Successfully added item(s) to database.',
#                 'query' : query 
#             }
#         }
    
#     def close(self : object) -> dict:
#         try : 
#             self.connection.close()
#         except:
#             raise Exception('Error: Could not proceed to close the connection of the database, try again later.')
#         return {
#             'status': 0,
#             'detail': {
#                 'message': 'Database connection has been closed.',
#             }
#         }
    
# class SQLManager:
#     def __init__(self, connection_string: str) -> None:
#         self.conn: any = odbc.connect(connection_string)
#         self.cursor: any = self.conn.cursor()

#     def get(self, query: str) -> list:
#         result: list = self.cursor.execute(query)
#         return result.fetchall()
    
#     def operate(self, query: str, operation: str) -> any:
#         try: 
#             self.cursor.execute(query)
#             self.conn.commit()
#             with ('log.json', 'a') as f:
#                 data: dict = {
#                     'operation': operation,
#                     'query': query,
#                     'created_at': datetime.now()
#                 }
#                 f.write(json.dumps(data))
#             return True
#         except Exception as e:
#             return e
        
# if __name__ == '__main__':
#     manager: SQLManager = SQLManager('Driver={ODBC Driver 17 for SQL Server};Server=tcp:otudy-team.database.windows.net,1433;Database=main-db;Uid=aketdOTUDY012023;Pwd=oT-,872%54Asdwzzsq>*90;Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;')
#     print(manager.get('SELECT * FROM dbo.Users;'))
        
    
        
            
    

