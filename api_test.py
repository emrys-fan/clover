#!/usr/bin/env python
# -*- coding: utf-8 -*-

import requests
import json
from urlparse import urljoin

session_token_1 = '79204bdf336f4a118dec775be255bdb7'
session_token_2 = '7ee87fd1a93b471a91b0d865cbe7cb18'
user = {'id': 1}

def test_login(session):
    r = session.post(urljoin(session.base_url, '/signup'),
            data={'username': 'emrys',
                'password': 'hello',
                'email': 'emrys@muxucao.com',
                'confirm': 'hello'})
    assert "注册成功" in r.text
    r = session.post(urljoin(session.base_url, '/signin'),
            data={'username':'emrys', 'password':'hello'})
    assert "成功登录" in r.text

def test_items(session):
    # create item
    data = {'title': 'How to dress: fluffy jumpers',
            'description': 'The difference between a fleece and a rich angora sweater is like the difference between an electric radiator and an open fire',
            'original_price': 600.00,
            'current_price': 300.00,
            'brand': 'TakeIT',
            'size': 'Middle',
            'category': 'others',
            'photo': 'http://custoshopsandbox.develoop.net/row/es/skin/frontend/enterprise/custobarcelona/images/men.jpg'
            }
    r = session.post(urljoin(session.base_url, '/item/create'), data=data)
    print r.text

    # show item
    item = json.loads(r.text)
    r = session.get(urljoin(session.base_url, '/item/show/%s'%item['postid']))
    print r.text

    # comment item
    comment = {'text': 'comment from request test.'}
    r = session.post(urljoin(session.base_url, '/comment/item/%s'%item['postid']), data=comment)
    r = session.post(urljoin(session.base_url, '/comment/item/%s'%item['postid']), data=comment)
    r = session.post(urljoin(session.base_url, '/comment/item/%s'%item['postid']), data=comment)
    r = session.post(urljoin(session.base_url, '/comment/item/%s'%item['postid']), data=comment)
    print r.text

    # show comments list
    comment_ret = json.loads(r.text)
    r = session.get(urljoin(session.base_url, '/item/comment/%s'%comment_ret['cid']))
    print r.text

    # show public
    r = session.get(urljoin(session.base_url, '/public'))
    print r.text
    # show user feed
    r = session.get(urljoin(session.base_url, '/feed'))
    print r.text
    # show user comments
    r = session.get(urljoin(session.base_url, '/comments'))
    # show user closet
    r = session.get(urljoin(session.base_url, '/closet'))
    print r.text
    # show user likes
    r = session.get(urljoin(session.base_url, '/likes'))
    print r.text
    # listing user following
    r = session.get(urljoin(session.base_url, '/following'))
    print r.text
    r = session.get(urljoin(session.base_url, '/user/following/%s'%user['id']))
    print r.text
    # listing user followed
    r = session.get(urljoin(session.base_url, '/followed'))
    print r.text
    r = session.get(urljoin(session.base_url, '/user/followed/%s'%user['id']))
    print r.text

    # like action
    ## listing item likes
    r = session.get(urljoin(session.base_url, '/item/likes/%s'%item['postid']))
    print r.text
    ## like it
    r = session.post(urljoin(session.base_url, '/like/%s'%item['postid']))
    print r.text
    ## listing item likes
    r = session.get(urljoin(session.base_url, '/item/likes/%s'%item['postid']))
    print r.text
    ## listing user likes
    r = session.get(urljoin(session.base_url, '/likes'))
    print r.text
    ## unlike it
    r = session.post(urljoin(session.base_url, '/unlike/%s'%item['postid']))
    print r.text
    ## listing item likes
    r = session.get(urljoin(session.base_url, '/item/likes/%s'%item['postid']))
    print r.text
    ## listing user likes
    r = session.get(urljoin(session.base_url, '/likes'))
    print r.text

    # follow action
    r = session.get(urljoin(session.base_url, '/follow/%s'%user['id']))
    print r.text
    r = session.get(urljoin(session.base_url, '/unfollow/%s'%user['id']))
    print r.text

if __name__ == '__main__':
    headers = {'X-Requested-With': 'XMLHttpRequest'}
    session = requests.session(headers=headers)
    session.base_url = 'http://ld.youpinapp.com:5000/'
    test_login(session)
    #test_items(session)
