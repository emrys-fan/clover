# -*- coding: utf-8 -*-
import time
import uuid
from werkzeug.security import generate_password_hash, check_password_hash
from flask import current_app
from flask import g
from flask import session
from flask.ext.wtf import Form
from flask.ext.wtf import TextField, PasswordField, TextAreaField
from flask.ext.wtf import Required, Email, URL, Optional, Length
from flask.ext.wtf import EqualTo
from flask.ext.wtf.html5 import EmailField, URLField


class SignupForm(Form):
    username = TextField('用户名', validators=[Required('缺少用户名'), Length(min=3, max=20)])
    email = EmailField('电子邮箱', validators=[Required('缺少电子邮箱'), Email()])
    password = PasswordField('密码', validators=[Required()])
    confirm = PasswordField('确认密码', validators=[Required(), EqualTo('password', message="密码不匹配")])

    def validate_username(self, field):
        uid = current_app.redis.get('uname:%s:uid'%field.data)
        if uid:
            raise ValueError("该用户名已注册")

    def save(self):
        uid = current_app.redis.hincrby('system', 'next_uid', 1)
        token = uuid.uuid4().get_hex()

        user = {'id': uid,
                'username': self.username.data,
                'password': generate_password_hash(self.password.data),
                'email': self.email.data,
                'token': token}

        current_app.redis.set('uname:%s:uid'%self.username.data, uid)
        current_app.redis.hmset('user:%s'%uid, user)

        if hasattr(g, 'recommender'):
            current_app.redis.zadd('user:%s:invited'%g.recommender['id'], user['id'], time.time())
            current_app.redis.hset('user:%s'%user['id'], 'rid', g.recommender['id'])
            current_app.redis.hincrby('user:%s'%g.recommender['id'], 'invite_quota_left', -1)
            session.pop('uid', None)

        return user

    def validate_csrf_token(self, field):
        pass


class SigninForm(Form):
    username = TextField('用户名', validators=[Required()])
    password = PasswordField('密码', validators=[Required()])

    def validate_password(self, field):
        username = self.username.data
        uid = current_app.redis.get('uname:%s:uid'%username)

        if not uid:
            raise ValueError('用户名或密码错误')

        user = current_app.redis.hgetall('user:%s'%uid)

        if not check_password_hash(user['password'], self.password.data):
            raise ValueError('用户名或密码错误')

        self.user = user
        return user

    def validate_csrf_token(self, field):
        pass


class ProfileForm(Form):
    username = TextField('username', validators=[Required()])
    email = TextField('email', validators=[Required(), Email()])
    about = TextAreaField('about')
    city = TextField('city')
    photo = URLField('profie image', validators=[Optional(), URL()])
    website = URLField('Website', validators=[Optional(), URL()])

    def save(self):
        user = g.user
        user.update(self.data)
        current_app.redis.hmset('user:%s'%g.user['id'], user)
        return user

    def validate_csrf_token(self, field):
        pass
