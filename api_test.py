#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
import uuid
import json
import unittest
from app import app
from werkzeug.security import generate_password_hash

ajax_headers = {'X-Requested-With': 'XMLHttpRequest'}

class APITest(unittest.TestCase):
    """docstring for APIText"""

    def setUp(self):
        """docstring for setUp"""
        pass

    def signup(self, username, password, confirm=None, email=None, recommender=None):
        if confirm is None:
            confirm = password
        if email is None:
            email = username + '@muxucao.com'
        if recommender == None:
            recommender = username

        return self.client.post('/api/signup', data={
            'recommender': recommender,
            'username': username,
            'password': password,
            'confirm': confirm,
            'email': email
            }, follow_redirects=True)

    def signin(self, username, password):
        return self.client.post('/api/signin', data={
            'username': username,
            'password': password
            })

    def signout(self):
        return self.client.get('/signout', follow_redirects=True)

    def initialize_recommemder(self, username, password):
        # setup recommemder
        uid = app.redis.hincrby('system', 'next_uid', 1)
        recommender = {'id': uid,
                'username': username,
                'password': generate_password_hash(password),
                'email': username+'@gmail.com',
                'photo': app.config['DEFAULT_PROFILE_IMAGE'],
                'token': uuid.uuid4().get_hex(),
                'created_at': time.time(),
                'invite_quota_left': 2}
        app.redis.set('uname:%s:uid'%username, uid)
        app.redis.hmset('user:%s'%uid, recommender)

    def test_signup_disable_invite_mode(self):
        # disable INVITE_MODE
        app.config['INVITE_MODE'] = False
        app.redis.flushdb()
        self.client = app.test_client()

        # signup
        rv = self.signup('emrys', 'hello')
        assert rv.mimetype == 'application/json'
        jsondata = json.loads(rv.data)
        assert 'emrys' == jsondata['user']['username']
        self.signout()



        # signup with a exist name
        rv = self.signup('emrys', 'hello')
        assert rv.mimetype == 'application/json'
        jsondata = json.loads(rv.data)
        assert 'username' in jsondata['message']

        # signup with a name which is less than 5 chars
        rv = self.signup('me', 'hello')
        assert rv.mimetype == 'application/json'
        jsondata = json.loads(rv.data)
        assert 'Field must be between 5 and 30 characters long.' in jsondata['message']['username'][0]
        # signup with a name  which is more than 30 chars
        rv = self.signup('abcdefghijjihgfedcbaabcdefghijk', 'hello')
        jsondata = json.loads(rv.data)
        assert 'Field must be between 5 and 30 characters long.' in jsondata['message']['username'][0]

    def test_signup_enable_invite_mode(self):
        # enable INVITE_MODE
        app.config['INVITE_MODE'] = True
        app.redis.flushdb()
        self.client = app.test_client()

        rv = self.signup('emrys', 'hello')
        assert rv.mimetype == 'application/json'
        jsondata = json.loads(rv.data)
        assert 'recommender' in jsondata['message']

        self.initialize_recommemder('google', 'hello')
        rv = self.signup('emrys', 'hello', recommender="google")
        assert rv.mimetype == 'application/json'
        jsondata = json.loads(rv.data)
        assert 'emrys' == jsondata['user']['username']
        # check google's followings and followers
        rv = self.client.get('/following/1', headers=ajax_headers)
        jsondata = json.loads(rv.data)
        exist = [user for user in jsondata['followings'] if user['username'] == 'emrys']
        assert exist !=  []
        rv = self.client.get('/follower/1', headers=ajax_headers)
        jsondata = json.loads(rv.data)
        exist = [user for user in jsondata['followers'] if user['username'] == 'emrys']
        assert exist !=  []
        self.signout()
        # check emrys's followings and followers
        self.signin('emrys', 'hello')
        rv = self.client.get('/following/2', headers=ajax_headers)
        jsondata = json.loads(rv.data)
        exist = [user for user in jsondata['followings'] if user['username'] == 'google']
        assert exist !=  []
        rv = self.client.get('/follower/2', headers=ajax_headers)
        jsondata = json.loads(rv.data)
        exist = [user for user in jsondata['followers'] if user['username'] == 'google']
        assert exist !=  []

    def test_signin(self):
        """docstring for test_signin"""
        # disable INVITE_MODE
        app.config['INVITE_MODE'] = False
        app.redis.flushdb()
        self.client = app.test_client()

        # signup
        rv = self.signup('emrys', 'hello')
        assert rv.mimetype == 'application/json'
        jsondata = json.loads(rv.data)
        assert 'emrys' == jsondata['user']['username']
        rv = self.signout()

        # signin
        rv = self.signin('emrys', 'hello')
        jsondata = json.loads(rv.data)
        assert 'emrys' == jsondata['user']['username']

    def test_follow_action(self):
        """docstring for test_follow_action"""
        # enable INVITE_MODE
        app.config['INVITE_MODE'] = True
        app.redis.flushdb()
        self.client = app.test_client()

        # set up 2 users
        self.initialize_recommemder('somebody1', 'hello')
        self.initialize_recommemder('somebody2', 'hello')

        # signup 2 users with recommender
        self.signup('emrys', 'hello', recommender='somebody1')
        self.signout()
        self.signup('apple', 'hello', recommender='somebody1')
        self.signout()
        self.signup('google', 'hello', recommender='somebody2')
        self.signout()
        self.signup('facebook', 'hello', recommender='somebody2')
        self.signout()

        # check
        self.signin('somebody1', 'hello')
        rv = self.client.get('/following/1', headers=ajax_headers)
        jsondata = json.loads(rv.data)
        assert len(jsondata['followings']) == 2
        rv = self.client.get('/follower/1', headers=ajax_headers)
        jsondata = json.loads(rv.data)
        assert len(jsondata['followers']) == 2
        # follow someone that I already followed makes no change
        rv = self.client.get('/follow/3')
        assert rv.status_code == 200
        rv = self.client.get('/following/1', headers=ajax_headers)
        jsondata = json.loads(rv.data)
        assert len(jsondata['followings']) == 2
        # follow someone new
        rv = self.client.get('/follow/5')
        jsondata = json.loads(rv.data)
        assert rv.status_code == 200
        rv = self.client.get('/following/1', headers=ajax_headers)
        jsondata = json.loads(rv.data)
        assert len(jsondata['followings']) == 3
        # unfollow someone that I don't followed yet makes no change
        rv = self.client.get('/unfollow/6')
        assert rv.status_code == 400
        rv = self.client.get('/following/1', headers=ajax_headers)
        jsondata = json.loads(rv.data)
        assert len(jsondata['followings']) == 3
        # unfollow someone that I already followed
        rv = self.client.get('/unfollow/3')
        rv = self.client.get('/following/1', headers=ajax_headers)
        jsondata = json.loads(rv.data)
        assert len(jsondata['followings']) == 2

    def test_profile(self):
        """docstring for test_self"""
        # enable INVITE_MODE
        app.config['INVITE_MODE'] = True
        app.redis.flushdb()
        self.client = app.test_client()

        self.initialize_recommemder('emrys', 'hello')
        self.signin('emrys', 'hello')
        # get user profile
        rv = self.client.get('/api/profile/update')
        jsondata = json.loads(rv.data)
        assert jsondata['username'] == 'emrys'
        # update user profile
        profile = {'username': jsondata['username'],
                'email': jsondata['email']}
        rv = self.client.post('/api/profile/update', data=profile)
        assert rv.status_code == 200
        # update username conflict with another user
        self.signout()
        self.signup('google', 'hello', recommender='emrys')
        rv = self.client.post('/api/profile/update', data=profile)
        assert rv.status_code == 400

    def test_change_password(self):
        """docstring for test_change_password"""
        # disable INVITE_MODE
        app.config['INVITE_MODE'] = False
        app.redis.flushdb()
        self.client = app.test_client()

        self.signup('emrys', 'hello')
        # with correct password
        data = {'password': 'hello',
                'new_password': 'default',
                'confirm': 'default'}
        rv = self.client.post('/api/change/password', data=data)
        assert rv.status_code == 200
        # wrong password
        rv = self.client.post('/api/change/password', data=data)
        assert rv.status_code == 400


if __name__ == '__main__':
    unittest.main()
