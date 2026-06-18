from database.connection import engine, Base

def init_db():
    print("Создаем таблицы в базе данных...")
    Base.metadata.create_all(bind=engine)
    print("Таблицы успешно созданы!")

if __name__ == "__main__":
    init_db()