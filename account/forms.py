# -*- coding: utf-8 -*-
import uuid
import time
from werkzeug.security import generate_password_hash, check_password_hash
from flask import current_app
from flask import g
from flask.ext.wtf import Form
from flask.ext.wtf import TextField, PasswordField, TextAreaField
from flask.ext.wtf import Required, Email, URL, Optional, Length
from flask.ext.wtf import EqualTo
from flask.ext.wtf.html5 import EmailField, URLField


class SignupForm(Form):
    recommender = TextField('推荐人', validators=[Required()])
    username = TextField('用户名', validators=[Required('缺少用户名'), Length(min=5, max=30)])
    email = EmailField('电子邮箱', validators=[Required('缺少电子邮箱'), Email()])
    password = PasswordField('密码', validators=[Required()])
    confirm = PasswordField('确认密码', validators=[Required(), EqualTo('password', message="密码不匹配")])
    photo = URLField('profie image', validators=[Optional(), URL()])

    def validate_recommender(self, field):
        # if INVITE_MODE is disabled, recommender is also required but was not used.
        if current_app.config['INVITE_MODE']:
            if not field.data:
                raise ValueError('必须填写邀请人')
            rid = current_app.redis.get('uname:%s:uid'%field.data)
            g.recommender = current_app.redis.hgetall('user:%s'%rid)
            if not g.recommender:
                raise ValueError('查无此人')

            if int(g.recommender.get('invite_quota_left', 0)) < 1:
                raise ValueError('无推荐名额')


    def validate_username(self, field):
        uid = current_app.redis.get('uname:%s:uid'%field.data)
        if uid:
            raise ValueError("该用户名已注册")

    def save(self):
        uid = current_app.redis.hincrby('system', 'next_uid', 1)
        token = uuid.uuid4().get_hex()

        if hasattr(g, 'recommender'):
            user = {'id': uid,
                    'rid': g.recommender['id'],
                    'username': self.username.data,
                    'password': generate_password_hash(self.password.data),
                    'email': self.email.data,
                    'photo': self.photo.data or current_app.config['DEFAULT_PROFILE_IMAGE'],
                    'token': token,
                    'created_at': time.time()}

            current_app.redis.set('uname:%s:uid'%self.username.data, uid)
            current_app.redis.hmset('user:%s'%uid, user)
            current_app.redis.hincrby('user:%s'%g.recommender['id'], 'invite_quota_left', -1)
            current_app.redis.hincrby('user:%s'%g.recommender['id'], 'invite_count', 1)
            current_app.redis.zadd('user:%s:recommended'%g.recommender['id'], uid, time.time())
            # following each other
            current_app.redis.zadd('user:%s:following'%uid, g.recommender['id'], time.time())
            current_app.redis.zadd('user:%s:follower'%uid, g.recommender['id'], time.time())
            current_app.redis.hincrby('user:%s'%uid, 'following_count', 1)
            current_app.redis.hincrby('user:%s'%uid, 'follower_count', 1)
            current_app.redis.zadd('user:%s:following'%g.recommender['id'], uid, time.time())
            current_app.redis.zadd('user:%s:follower'%g.recommender['id'], uid, time.time())
            current_app.redis.hincrby('user:%s'%g.recommender['id'], 'following_count', 1)
            current_app.redis.hincrby('user:%s'%g.recommender['id'], 'follower_count', 1)
        else:
            user = {'id': uid,
                    'username': self.username.data,
                    'password': generate_password_hash(self.password.data),
                    'email': self.email.data,
                    'photo': self.photo.data or current_app.config['DEFAULT_PROFILE_IMAGE'],
                    'token': token,
                    'created_at': time.time()}
            current_app.redis.set('uname:%s:uid'%self.username.data, uid)
            current_app.redis.hmset('user:%s'%uid, user)

        filter_keys = ['id', 'username', 'photo', 'token']
        return { key: user[key] for key in filter_keys}

class API_SignupForm(SignupForm):

    def validate_csrf_token(self, field):
        """
        disable csrf protection
        """
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

        update_info = {'token': uuid.uuid4().get_hex(), 'updated_at': time.time()}
        # update token
        current_app.redis.hmset('user:%s'%uid, update_info)
        user.update(update_info)
        filter_keys = ['id', 'username', 'photo', 'token']
        self.user = { key: user[key] for key in filter_keys}


class API_SigninForm(SigninForm):

    def validate_csrf_token(self, field):
        """
        disable csrf protection
        """
        pass


class ProfileForm(Form):
    username = TextField('username', validators=[Required()])
    email = TextField('email', validators=[Required(), Email()])
    about = TextAreaField('about')
    city = TextField('city')
    photo = URLField('profie image', validators=[Optional(), URL()])
    website = URLField('Website', validators=[Optional(), URL()])

    def validate_username(self, field):
        if g.user['username'] == field.data:
            return None

        uid = current_app.redis.get('uname:%s:uid'%field.data)
        if uid:
            raise ValueError("该用户名已注册")

    def save(self):
        user = g.user
        user.update(self.data)
        current_app.redis.hmset('user:%s'%g.user['id'], user)

        if g.user['username'] != user['username']:
            current_app.redis.set('uname:%s:uid'%user['username'], user['id'])
            current_app.redis.delete('uname:%s:uid'%g.user['username'])

        return user

class API_ProfileForm(ProfileForm):

    def validate_csrf_token(self, field):
        """
        disable csrf protection
        """
        pass


class RecommemderForm(Form):
    username = TextField('邀请人', validators=[Required()])

    def validate_username(self, field):
        rid = current_app.redis.get('uname:%s:uid' % field.data)
        if not rid:
            raise ValueError("查无此人")

        recommender = current_app.redis.hgetall('user:%s' % rid)
        if int(recommender.get('invite_quota_left', 0)) < 1:
            raise ValueError("邀请名额已用完")
        filter_keys = ['id', 'username', 'photo', 'token']
        self.recommender = dict(zip(filter_keys, recommender))

class API_RecommemderForm(RecommemderForm):

    def validate_csrf_token(self, field):
        """
        disable csrf protection
        """
        pass

class API_PasswordFrom(Form):
    password = PasswordField('当前密码', validators=[Required()])
    new_password = PasswordField('新密码', validators=[Required()])
    confirm = PasswordField('确认新密码', validators=[Required(), EqualTo('new_password', message="密码不匹配")])

    def validate_csrf_token(self, field):
        """
        disable csrf protection
        """
        pass

    def validate_password(self, field):
        if not check_password_hash(g.user['password'], self.password.data):
            raise ValueError("当前密码输入有误")

    def save(self):
        g.user.update({'password': generate_password_hash(self.new_password.data)})
        current_app.redis.hset('user:%s'%g.user['id'], 'password', g.user['password'])


