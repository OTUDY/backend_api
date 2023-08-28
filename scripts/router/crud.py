import sqlite3

class SQLiteManager:
    def __init__(self : object, db_name : str) -> None:
        self.connection = sqlite3.connect(db_name, check_same_thread=False)
        self.cursor = self.connection.cursor()

    def get(self : object, query : str) -> list:
        return self.cursor.execute(query).fetchall()
    
    def add(self : object, query : str) -> dict:
        self.cursor.execute(query)
        self.connection.commit()
        return True
    
    def edit(self : object, query : str) -> dict:
        self.cursor.execute(query)
        self.connection.commit()
        return {
            'status': 0,
            'detail': {
                'message': 'Successfully editted item(s) in database.',
                'query' : query 
            }
        }
    
    def delete(self : object, query : str) -> dict:
        try :
            self.cursor.execute(query)
            self.connection.commit()
        except:
            raise Exception('Error: SQL Query or Syntax is not in the right format, please look forward to check.')
        return {
            'status': 0,
            'detail': {
                'message': 'Successfully added item(s) to database.',
                'query' : query 
            }
        }
    
    def close(self : object) -> dict:
        try : 
            self.connection.close()
        except:
            raise Exception('Error: Could not proceed to close the connection of the database, try again later.')
        return {
            'status': 0,
            'detail': {
                'message': 'Database connection has been closed.',
            }
        }
    

if __name__ == '__main__':
    crud = SQLiteManager('/Users/magicbook/Desktop/OTUDY/EF-App-Backend/scripts/router/default.sqlite')
    print(crud.get('SELECT * FROM ClassLevels'))
    

