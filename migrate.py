"""
Запусти этот файл ОДИН РАЗ после обновления models.py,
чтобы добавить новые колонки avatar и bio в существующую таблицу users.

    python migrate.py
"""
from database.connection import engine
from sqlalchemy import text

def run_migration():
    with engine.connect() as conn:
        result = conn.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name='users' AND column_name='avatar'"
        ))
        if result.fetchone() is None:
            conn.execute(text("ALTER TABLE users ADD COLUMN avatar TEXT"))
            print("[+] Колонка 'avatar' добавлена")
        else:
            print("[=] Колонка 'avatar' уже существует")

        result = conn.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name='users' AND column_name='bio'"
        ))
        if result.fetchone() is None:
            conn.execute(text("ALTER TABLE users ADD COLUMN bio VARCHAR(300)"))
            print("[+] Колонка 'bio' добавлена")
        else:
            print("[=] Колонка 'bio' уже существует")

        conn.commit()
        print("Миграция завершена!")

if __name__ == "__main__":
    run_migration()