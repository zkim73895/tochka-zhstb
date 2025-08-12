import sqlite3 as sql

conn = sql.connect('database.db')
cursor = conn.cursor()

def create_user(id, name, role, api_key):
    # Parameterized query
    # print('creating user...')
    # print(id, name, role, api_key)
    query = '''
    INSERT INTO Users (id, name, role, api_key)
    VALUES (?, ?, ?, ?);
    '''
    # Execute the query with parameters
    try:
        cursor.execute(query, (str(id), name, int(role), api_key))
    except Exception as e:
        print(e)
    print(f'User {name} created successfully')
    conn.commit()

def lookup(table, key, val):
    query = f'''
    SELECT * FROM {table} WHERE {key} = ?
    '''
    cursor.execute(query, (val,))
    cursor.fetchone()