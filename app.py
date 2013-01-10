#!/usr/bin/env python
# -*- coding: utf-8 -*-

import redis
from flask import Flask, g, render_template, redirect, url_for
from account.helpers import get_current_user
from account.views import bp_account
from item.views import bp_item
from timeline.views import bp_timeline
from we.views import bp_we
from sale.views import bp_sale

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
app.register_blueprint(bp_timeline)
app.register_blueprint(bp_we)
app.register_blueprint(bp_sale)

@app.route('/')
def index():
    if g.user:
        return redirect(url_for('timeline.public'))
    return render_template('index.html')


if __name__ == '__main__':
    app.run('0.0.0.0', debug=True)
