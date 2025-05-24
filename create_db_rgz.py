import psycopg2

DB_CONFIG = {
    'user': 'postgres',
    'password': 'postgres',
    'host': '127.0.0.1',
    'port': '5432',
    'dbname': 'finance_db'
}

def create_tables():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    # Таблица пользователей
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            chat_id BIGINT UNIQUE NOT NULL
        );
    """)

    # Таблица категорий
    cur.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            chat_id BIGINT NOT NULL,
            FOREIGN KEY (chat_id) REFERENCES users(chat_id) ON DELETE CASCADE
        );
    """)

    # Таблица операций
    cur.execute("""
        CREATE TABLE IF NOT EXISTS operations (
            id SERIAL PRIMARY KEY,
            date DATE NOT NULL,
            sum NUMERIC NOT NULL,
            chat_id BIGINT NOT NULL,
            type_operation TEXT NOT NULL CHECK (type_operation IN ('РАСХОД', 'ДОХОД')),
            category_id INTEGER,
            FOREIGN KEY (chat_id) REFERENCES users(chat_id) ON DELETE CASCADE,
            FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL
        );
    """)

    conn.commit()
    cur.close()
    conn.close()
    print("Все таблицы успешно созданы.")

if __name__ == "__main__":
    create_tables()
