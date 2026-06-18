from flask_socketio import SocketIO, send, emit, join_room
from flask import Flask, session
from controllers.routes import auth_bp
from database.connection import engine, Base, get_db
from services.business_logic import send_message
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'f1farka_vksuperkrutoi_dev')
app.register_blueprint(auth_bp)

# Конфигурация которая стабильно работает (без manage_session)
socketio = SocketIO(app, cors_allowed_origins="*")

Base.metadata.create_all(bind=engine)

# Онлайн-пользователи { user_id: количество открытых вкладок }
online_users = {}


def broadcast_online_status():
    socketio.emit('online_users', {'users': list(online_users.keys())})


@socketio.on('connect')
def handle_connect():
    user_id = session.get('user_id')
    # ВАЖНО: НЕ отклоняем подключение (никаких return False),
    # иначе при пустой сессии сокет молча отваливается и страница ломается.
    if user_id:
        join_room(f'user_{user_id}')
        online_users[user_id] = online_users.get(user_id, 0) + 1
        print(f"[+] {session.get('username')} (id={user_id}) онлайн")
        broadcast_online_status()


@socketio.on('disconnect')
def handle_disconnect():
    user_id = session.get('user_id')
    if not user_id:
        return
    if user_id in online_users:
        online_users[user_id] -= 1
        if online_users[user_id] <= 0:
            del online_users[user_id]
    print(f"[-] {session.get('username')} (id={user_id}) оффлайн")
    broadcast_online_status()


@socketio.on('get_online')
def handle_get_online():
    emit('online_users', {'users': list(online_users.keys())})


@socketio.on('typing')
def handle_typing(data):
    user_id = session.get('user_id')
    username = session.get('username')
    if not user_id:
        return
    recipient_id = data.get('recipient_id')
    chat_type = data.get('chat_type', 'global')
    payload = {'sender_id': user_id, 'sender': username, 'chat_type': chat_type}
    if chat_type == 'global':
        emit('typing', payload, broadcast=True, include_self=False)
    elif recipient_id:
        emit('typing', payload, room=f'user_{recipient_id}')


@socketio.on('message')
def handle_message(data):
    user_id = session.get('user_id')
    username = session.get('username')
    if not user_id:
        return

    text = data.get('text', '').strip()
    chat_type = data.get('chat_type', 'global')
    recipient_id = data.get('recipient_id')

    if not text or len(text) > 2000:
        return

    db = next(get_db())
    result = send_message(db, user_id, text, recipient_id, chat_type)
    if not result['success']:
        print(f"[!] Ошибка: {result['message']}")
        return

    msg = result['data']
    sender_avatar = msg.sender.avatar if msg.sender else ''

    payload = {
        'sender_id': user_id,
        'sender': username,
        'sender_avatar': sender_avatar or '',
        'text': text,
        'chat_type': chat_type,
        'recipient_id': recipient_id,
        'timestamp': msg.timestamp.strftime('%H:%M'),
        'msg_id': msg.id
    }

    if chat_type == 'global':
        send(payload, broadcast=True)
    else:
        emit('message', payload, room=f'user_{user_id}')
        if recipient_id and recipient_id != user_id:
            emit('message', payload, room=f'user_{recipient_id}')


if __name__ == '__main__':
    socketio.run(app, debug=True, allow_unsafe_werkzeug=True)