from flask import session, current_app
from weibo import Client

def get_weibo_client(redirect_url):
    return Client(current_app.config['WEIBO_CONSUMER_KEY'],
            current_app.config['WEIBO_CONSUMER_SECRET'],
            redirect_url)


def get_current_user():
    if 'id' not in session or 'token' not in session:
        return None

    user = current_app.redis.hgetall('user:%s'%session['id'])
    if not user:
        return None
    if user['token'] != session['token']:
        logout()
        return None
    return user


def login(user):
    if not user:
        return None
    session['id'] = user['id']
    session['token'] = user['token']
    return user


def logout():
    if 'id' not in session:
        return
    session.pop('id')
    session.pop('token')
