from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func
from werkzeug.security import generate_password_hash, check_password_hash
from database.models import User, Message


# ─────────────────────────────────────────────
#  АВТОРИЗАЦИЯ
# ─────────────────────────────────────────────

def register_user(db: Session, username: str, password: str):
    username = username.strip()
    if len(username) < 3:
        return {"success": False, "message": "Имя пользователя должно быть не менее 3 символов"}
    if len(username) > 50:
        return {"success": False, "message": "Имя пользователя слишком длинное"}
    if len(password) < 6:
        return {"success": False, "message": "Пароль должен быть не менее 6 символов"}
    existing = db.query(User).filter(func.lower(User.username) == username.lower()).first()
    if existing:
        return {"success": False, "message": "Пользователь с таким именем уже существует"}
    new_user = User(username=username, password_hash=generate_password_hash(password))
    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return {"success": True, "message": "Регистрация успешна", "user": new_user}
    except Exception as e:
        db.rollback()
        return {"success": False, "message": f"Ошибка при сохранении: {str(e)}"}


def authenticate_user(db: Session, username: str, password: str):
    username = username.strip()
    user = db.query(User).filter(func.lower(User.username) == username.lower()).first()
    if not user or not check_password_hash(user.password_hash, password):
        return {"success": False, "message": "Неверное имя пользователя или пароль"}
    return {"success": True, "message": "Вход выполнен успешно", "user": user}


def change_password(db: Session, user_id: int, old_password: str, new_password: str):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return {"success": False, "message": "Пользователь не найден"}
    if not check_password_hash(user.password_hash, old_password):
        return {"success": False, "message": "Неверный текущий пароль"}
    if len(new_password) < 6:
        return {"success": False, "message": "Новый пароль должен быть не менее 6 символов"}
    user.password_hash = generate_password_hash(new_password)
    try:
        db.commit()
        return {"success": True, "message": "Пароль успешно изменён!"}
    except Exception as e:
        db.rollback()
        return {"success": False, "message": f"Ошибка: {str(e)}"}


# ─────────────────────────────────────────────
#  ПРОФИЛЬ
# ─────────────────────────────────────────────

def get_profile(db: Session, user_id: int):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return None
    return {"id": user.id, "username": user.username, "bio": user.bio or "", "avatar": user.avatar or ""}


def update_profile(db: Session, user_id: int, new_username: str = None, bio: str = None, avatar: str = None):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return {"success": False, "message": "Пользователь не найден"}

    if new_username is not None:
        new_username = new_username.strip()
        if len(new_username) < 3:
            return {"success": False, "message": "Никнейм должен быть не менее 3 символов"}
        if len(new_username) > 50:
            return {"success": False, "message": "Никнейм слишком длинный"}
        conflict = db.query(User).filter(
            func.lower(User.username) == new_username.lower(),
            User.id != user_id
        ).first()
        if conflict:
            return {"success": False, "message": "Этот никнейм уже занят"}
        user.username = new_username

    if bio is not None:
        bio = bio.strip()
        if len(bio) > 300:
            return {"success": False, "message": "О себе — не более 300 символов"}
        user.bio = bio

    if avatar is not None:
        if avatar and not avatar.startswith("data:image/"):
            return {"success": False, "message": "Неверный формат изображения"}
        if len(avatar) > 2_800_000:
            return {"success": False, "message": "Изображение слишком большое (максимум ~2 МБ)"}
        user.avatar = avatar if avatar else None

    try:
        db.commit()
        db.refresh(user)
        return {
            "success": True, "message": "Профиль обновлён!",
            "username": user.username, "bio": user.bio or "", "avatar": user.avatar or ""
        }
    except Exception as e:
        db.rollback()
        return {"success": False, "message": f"Ошибка: {str(e)}"}


# ─────────────────────────────────────────────
#  СООБЩЕНИЯ
# ─────────────────────────────────────────────

def send_message(db: Session, sender_id: int, text: str, recipient_id: int = None, chat_type: str = "global"):
    text = text.strip()
    if not text:
        return {"success": False, "message": "Сообщение не может быть пустым"}
    if len(text) > 2000:
        return {"success": False, "message": "Сообщение слишком длинное"}
    if chat_type == "private":
        if not recipient_id:
            return {"success": False, "message": "Для приватного сообщения нужен получатель"}
        if not db.query(User).filter(User.id == recipient_id).first():
            return {"success": False, "message": "Получатель не найден"}

    new_msg = Message(
        sender_id=sender_id,
        recipient_id=recipient_id if chat_type == "private" else None,
        chat_type=chat_type,
        text=text
    )
    try:
        db.add(new_msg)
        db.commit()
        db.refresh(new_msg)
        return {"success": True, "message": "Сообщение отправлено", "data": new_msg}
    except Exception as e:
        db.rollback()
        return {"success": False, "message": f"Ошибка: {str(e)}"}


def delete_message(db: Session, message_id: int, user_id: int):
    """Удалить своё сообщение."""
    msg = db.query(Message).filter(Message.id == message_id).first()
    if not msg:
        return {"success": False, "message": "Сообщение не найдено"}
    if msg.sender_id != user_id:
        return {"success": False, "message": "Можно удалять только свои сообщения"}
    try:
        db.delete(msg)
        db.commit()
        return {"success": True, "message": "Сообщение удалено"}
    except Exception as e:
        db.rollback()
        return {"success": False, "message": f"Ошибка: {str(e)}"}


def get_global_messages(db: Session, limit: int = 50):
    msgs = db.query(Message)\
        .filter(Message.chat_type == "global")\
        .order_by(Message.timestamp.desc())\
        .limit(limit).all()
    return list(reversed(msgs))  # старые сверху, новые снизу


def get_private_messages(db: Session, user_one_id: int, user_two_id: int, limit: int = 50):
    msgs = db.query(Message).filter(
        Message.chat_type == "private",
        or_(
            and_(Message.sender_id == user_one_id, Message.recipient_id == user_two_id),
            and_(Message.sender_id == user_two_id, Message.recipient_id == user_one_id)
        )
    ).order_by(Message.timestamp.desc()).limit(limit).all()
    return list(reversed(msgs))


def get_dialogs(db: Session, user_id: int):
    """
    Возвращает список пользователей, с которыми у текущего юзера есть личная переписка.
    Нужно для восстановления списка диалогов после перезагрузки страницы.
    """
    # Все приватные сообщения, где участвует юзер
    msgs = db.query(Message).filter(
        Message.chat_type == "private",
        or_(Message.sender_id == user_id, Message.recipient_id == user_id)
    ).order_by(Message.timestamp.desc()).all()

    seen = {}
    for m in msgs:
        other_id = m.recipient_id if m.sender_id == user_id else m.sender_id
        if other_id is None or other_id in seen:
            continue
        other = db.query(User).filter(User.id == other_id).first()
        if other:
            seen[other_id] = {
                "id": other.id,
                "username": other.username,
                "avatar": other.avatar or "",
                "last_text": m.text[:40],
                "last_time": m.timestamp.strftime('%H:%M')
            }
    return list(seen.values())