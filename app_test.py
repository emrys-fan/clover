#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
import json
import app

class AppTest(unittest.TestCase):

    def setUp(self):
        self.app = app.app.test_client()
        app.app.redis.flushdb()

    def signup(self, username, password, confirm=None, email=None):
        if confirm is None:
            confirm = password
        if email is None:
            email = username + '@muxucao.com'
        return self.app.post('/signup', data={
            #'csrf_token': '20130108023135##279022d3750abd8e59110916a610fa122a10a0c1',
            'username': username,
            'password': password,
            'confirm': confirm,
            'email': email
            }, follow_redirects=True)

    def signin(self, username, password):
        return self.app.post('/signin', data={
            'username': username,
            'password': password
            }, follow_redirects=True)

    def signout(self):
        return self.app.get('/signout', follow_redirects=True)

    def signup_and_signin(self, username, password):
        self.signup(username, password)
        return self.signin(username, password)

    def signin_and_signout(self, username, password):
        self.signup(username, password)
        self.signin(username, password)
        return self.signout()

    def test_signup(self):
        rv = self.signup('emrys', 'hello')
        assert '注册成功' in rv.data
        rv = self.signup('emrys', 'hello')
        assert '该用户名已注册' in rv.data
        rv = self.signup('', 'hello')
        assert '缺少用户名' in rv.data

    def test_signin(self):
        rv = self.signup('emrys', 'hello')
        assert '注册成功' in rv.data
        rv = self.signout()
        assert '已退出' in rv.data
        rv = self.signin('emrys', 'hello')
        assert '成功登录' in rv.data

    def test_signin_signout(self):
        rv = self.signin_and_signout('emrys', 'hello')
        assert '已退出' in rv.data

    # item test helper
    def create_item(self):
        post = {'title': 'How to dress fluffy jumpers',
                'description': 'The difference between a fleece and a rich angora sweater is like',
                'original_price': 600.00,
                'current_price': 300.00,
                'brand': 'TakeIT',
                'size': 'Middle',
                'category': 'others',
                'photo': 'http://twitter.github.com/bootstrap/assets/img/bs-docs-twitter-github.png'
                }
        return self.app.post('/item/create', data=post)

    # item test functions
    def test_create_item(self):
        rv = self.signup('emrys', 'hello')
        assert '注册成功' in rv.data
        rv = self.create_item()
        assert 'success' in rv.data

    def test_show_item(self):
        self.signup('emrys', 'hello')
        # create item
        rv = self.create_item()
        assert 'success' in rv.data
        ret = json.loads(rv.data)
        postid = ret['postid']
        # show item
        rv = self.app.get('/item/show/%s' % postid, headers={'X-Requested-With': 'XMLHttpRequest'})
        ret = json.loads(rv.data)
        assert postid == int(ret['request_item']['postid'])

    def test_addcomment(self):
        # signup emrys
        rv = self.signup('emrys', 'hello')
        assert '注册成功' in rv.data

        # emrys create a item, then logout
        rv = self.create_item()
        assert 'success' in rv.data

        ret = json.loads(rv.data)
        postid = ret['postid']

        # signout emrys
        rv = self.app.get('/signout', follow_redirects=True)
        assert '已退出' in rv.data

        # signup google
        rv = self.signup('google', 'hello')
        assert '注册成功' in rv.data
        # google add a comment on emrys's post
        comment = {'text': 'So Amazing'}
        rv = self.app.post('/comment/item/%s' % postid, data=comment)
        ret = json.loads(rv.data)
        assert postid == int(ret['comment']['pid'])

    def test_show_item_comment(self):
        pass

if __name__ == '__main__':
    unittest.main()
