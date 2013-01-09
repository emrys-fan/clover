#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
from flask import current_app, g
from flask.ext.wtf import Form
from flask.ext.wtf import TextField, TextAreaField, DecimalField
from flask.ext.wtf import Required, Optional, Length
from flask.ext.wtf.html5 import URLField

class PostForm(Form):
    title = TextField('标题', validators=[Required(), Length(max=70)])
    description = TextAreaField('简介', validators=[Required(), Length(max=500)])
    category = TextField('分类', validators=[Length(max=30)])
    brand = TextField('品牌', validators=[Optional()])
    size = TextField('尺码', validators=[Optional()])
    original_price = DecimalField('原价', validators=[Required()])
    current_price = DecimalField('现价', validators=[Required()])
    photo = URLField('贴图', validators=[Required()])

    def validate_csrf_token(self, field):
        pass

    def save(self):
        current_app.logger.info('into save')
        postid = current_app.redis.hincrby('system', 'nextPostId', 1)
        post = {'postid': postid,
                'uid': g.user['id'],
                'publish_time': time.strftime('%Y-%m-%dT%H:%M:%S%z'),
                'title': self.title.data,
                'description': self.description.data,
                'photo': self.photo.data,
                'category': self.data.get('category', 'others'),
                'brand': self.data.get('brand', 'others'),
                'size': self.data.get('size', 'unknown'),
                'original_price': self.original_price.data,
                'current_price': self.current_price.data}
        current_app.redis.hmset('post:%s'%postid, post)
        current_app.redis.zadd('global_timeline', postid, time.time())
        current_app.redis.zadd('user:%s:timeline'%g.user['id'], postid, time.time())
        current_app.redis.zadd('category:%s'%post['category'], postid, time.time())
        current_app.redis.zadd('category:%s:size:%s'%(post['category'], post['size']), postid, time.time())
        current_app.redis.zadd('brand:%s'%post['brand'], postid, time.time())

        followings = current_app.redis.zrevrange('user:%s:following'%g.user['id'], 0, -1)
        for fid in followings:
            current_app.redis.zadd('user:%s:feed'%fid, postid, time.time())

        current_app.redis.hincrby('user:%s'%g.user['id'], 'invite_quota_left',
                current_app.config['PUBLISH_TO_INVITE_COEFFICIENT'])

        return post
