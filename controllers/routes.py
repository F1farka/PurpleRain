from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from database.connection import get_db
from database.models import User
from services.business_logic import (
    register_user, authenticate_user,
    get_global_messages, get_private_messages,
    change_password, get_profile, update_profile,
    delete_message, get_dialogs
)

auth_bp = Blueprint('auth', __name__)


def _msg_json(m, chat_type):
    return {
        'sender_id':     m.sender_id,
        'sender':        m.sender.username if m.sender else 'Удалён',
        'sender_avatar': (m.sender.avatar if m.sender else '') or '',
        'text':          m.text,
        'chat_type':     chat_type,
        'recipient_id':  m.recipient_id,
        'timestamp':     m.timestamp.strftime('%H:%M'),
        'msg_id':        m.id
    }


# ─────────────────────────────────────────────
#  СТРАНИЦЫ
# ─────────────────────────────────────────────

@auth_bp.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    return render_template('chat.html',
                           username=session.get('username'),
                           user_id=session.get('user_id'))


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        db = next(get_db())
        result = register_user(db, username, password)
        if result['success']:
            flash('Регистрация прошла успешно! Теперь войдите.', 'success')
            return redirect(url_for('auth.login'))
        flash(result['message'], 'danger')
    return render_template('register.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        db = next(get_db())
        result = authenticate_user(db, username, password)
        if result['success']:
            session['user_id']  = result['user'].id
            session['username'] = result['user'].username
            return redirect(url_for('auth.index'))
        flash(result['message'], 'danger')
    return render_template('login.html')


@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))


# ─────────────────────────────────────────────
#  API — ПРОФИЛЬ
# ─────────────────────────────────────────────

@auth_bp.route('/api/profile', methods=['GET'])
def api_get_profile():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    db = next(get_db())
    profile = get_profile(db, session['user_id'])
    if not profile:
        return jsonify({'error': 'Not found'}), 404
    return jsonify(profile)


@auth_bp.route('/api/profile', methods=['POST'])
def api_update_profile():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'Нет данных'}), 400
    db = next(get_db())
    result = update_profile(db, user_id=session['user_id'],
                            new_username=data.get('username'),
                            bio=data.get('bio'),
                            avatar=data.get('avatar'))
    if result.get('success') and data.get('username'):
        session['username'] = result['username']
    return jsonify(result)


# ─────────────────────────────────────────────
#  API — ПАРОЛЬ
# ─────────────────────────────────────────────

@auth_bp.route('/api/change-password', methods=['POST'])
def api_change_password():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'Нет данных'}), 400
    db = next(get_db())
    result = change_password(db, session['user_id'],
                             data.get('old_password', ''),
                             data.get('new_password', ''))
    return jsonify(result)


# ─────────────────────────────────────────────
#  API — СООБЩЕНИЯ
# ─────────────────────────────────────────────

@auth_bp.route('/api/messages/global')
def api_global_messages():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    db = next(get_db())
    return jsonify([_msg_json(m, 'global') for m in get_global_messages(db)])


@auth_bp.route('/api/messages/private/<int:other_user_id>')
def api_private_messages(other_user_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    db = next(get_db())
    msgs = get_private_messages(db, session['user_id'], other_user_id)
    return jsonify([_msg_json(m, 'private') for m in msgs])


@auth_bp.route('/api/messages/<int:message_id>', methods=['DELETE'])
def api_delete_message(message_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    db = next(get_db())
    result = delete_message(db, message_id, session['user_id'])
    return jsonify(result)


# ─────────────────────────────────────────────
#  API — ДИАЛОГИ (список переписок)
# ─────────────────────────────────────────────

@auth_bp.route('/api/dialogs')
def api_dialogs():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    db = next(get_db())
    return jsonify(get_dialogs(db, session['user_id']))


# ─────────────────────────────────────────────
#  API — ПОИСК
# ─────────────────────────────────────────────

@auth_bp.route('/api/users/search')
def api_search_users():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    q = request.args.get('q', '').strip()
    if len(q) < 1:
        return jsonify([])
    db = next(get_db())
    users = db.query(User).filter(
        User.username.ilike(f'%{q}%'),
        User.id != session['user_id']
    ).limit(10).all()
    return jsonify([{'id': u.id, 'username': u.username,
                     'avatar': u.avatar or '', 'bio': u.bio or ''} for u in users])