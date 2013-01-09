import functools
from flask import redirect, url_for, request, g, current_app, session
from helpers import logout

def login_required(method):
    @functools.wraps(method)
    def wrapper(*args, **kwargs):
        if g.user:
            return method(*args, **kwargs)
        else:
            url = url_for('account.signin')
            if '?' not in url:
                url += '?next=' + request.url
            return redirect(url)
    return wrapper


def invitation_required(method):
    @functools.wraps(method)
    def wrapper(*args, **kwargs):
        if current_app.config['INVITE_MODE']:
            g.recommender = None
            logout()
            rid = session.get('rid', None)
            if rid:
                g.recommender = current_app.redis.hgetall('user:%s'%rid)
            if g.recommender:
                return method(*args, **kwargs)
            return redirect(url_for('account.confirm_invitation', next=request.url))
        else:
            return method(*args, **kwargs)
    return wrapper
