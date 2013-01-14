import time
from flask import session, current_app, request
from weibo import Client

def get_weibo_client(redirect_url):
    return Client(current_app.config['WEIBO_CONSUMER_KEY'],
            current_app.config['WEIBO_CONSUMER_SECRET'],
            redirect_url)


def get_current_user():
    token = request.headers.get('X-Clover-Access', request.args.get('token', session.get('token', None)))
    if not token:
        return None

    user_session = current_app.redis.hgetall('session:%s'%token)
    if not user_session or token!= user_session['token']:
        return None

    user = current_app.redis.hgetall('user:%s'%user_session['uid'])

    return user


def login(user):
    if not user:
        return None
    session['token'] = user['token']
    current_app.redis.hmset('session:%s'%user['token'],
            {'uid': user['id'], 'token': user['token'], 'created_at': time.time()})
    return user


def logout():
    session.pop('token', None)
