import psycopg2

DB_CONFIG = {
    'user': 'postgres',
    'password': 'postgres',
    'dbname': 'lab6',
    'host': '127.0.0.1'
}

def create_database():
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = True
    cur = conn.cursor()
    
    try:
        cur.execute("CREATE DATABASE lab6db")
        print("База данных lab6db успешно создана")
    except psycopg2.Error as e:
        print(f"Ошибка при создании базы данных: {e}")
    
    conn.close()

def create_table():
    conn = psycopg2.connect(
        user='postgres',
        password='postgres',
        dbname='lab6db',
        host='127.0.0.1'
    )
    cur = conn.cursor()
    
    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS currencies (
                id SERIAL PRIMARY KEY,
                currency_name VARCHAR(50) UNIQUE NOT NULL,
                rate NUMERIC(10, 2) NOT NULL
            )
        """)
        conn.commit()
        print("Таблица currencies успешно создана")
    except psycopg2.Error as e:
        print(f"Ошибка при создании таблицы: {e}")
    
    conn.close()

if __name__ == '__main__':
    create_database()
    create_table()