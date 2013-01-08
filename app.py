#!/usr/bin/env python
# -*- coding: utf-8 -*-

import redis
from flask import Flask, g, render_template
from account.helpers import get_current_user
from account.views import bp_account
from item.views import bp_item
# from comment.views import bp_comment

app = Flask(__name__)
app.config.from_object('settings')

@app.before_request
def before_request():
    g.user = get_current_user()

app.redis = redis.Redis(
        host=app.config['REDIS_HOST'],
        port=app.config['REDIS_PORT'], db=2)

app.register_blueprint(bp_account)
app.register_blueprint(bp_item)
# app.register_blueprint(bp_comment)

@app.route('/')
def index():
    return render_template('index.html')


if __name__ == '__main__':
    app.run('0.0.0.0', debug=True)
