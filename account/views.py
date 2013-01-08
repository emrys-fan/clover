#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
from flask import Blueprint, current_app, render_template, request, g, \
        redirect, url_for, flash, jsonify, abort
from forms import SigninForm, SignupForm, ProfileForm
from helpers import login, logout
from utils import login_required

bp_account = Blueprint('account', __name__)

PAGE_SIZE = 20

@bp_account.route('/signin', methods=['GET', 'POST'])
def signin():
    next_url = request.args.get('next', '/')
    if g.user:
        return redirect(next_url)
    form = SigninForm()
    if form.validate_on_submit():
        login(form.user)
        flash('成功登录')
        return redirect(next_url)
    return render_template('account/signin.html', form=form)


@bp_account.route('/signup', methods=['GET', 'POST'])
def signup():
    form = SignupForm()
    current_app.logger.info('sign info: %s', form.data)
    if form.validate_on_submit():
        current_app.logger.info('sign successfully')
        user = form.save()
        login(user)
        flash('注册成功')
        return redirect(url_for('.setting'))
    return render_template('account/signup.html', form=form)


@bp_account.route('/setting', methods=['GET', 'POST'])
@login_required
def setting():
    form = ProfileForm()
    if form.validate_on_submit():
        form.save()
        flash("修改配置成功")
        return redirect(url_for('.setting'))
    return render_template('account/setting.html', form=form)


@bp_account.route('/signout')
def signout():
    next_url = request.args.get('next', '/')
    logout()
    flash('已退出')
    return redirect(next_url)


@bp_account.route('/following/<int:uid>')
@login_required
def user_following(uid):
    following_count = current_app.redis.zcard('user:%s:following'%uid)
    since_id = int(request.args.get('since_id', following_count))
    page = int(request.args.get('page', 1))
    rev_since_id = following_count - since_id + (page-1)*PAGE_SIZE

    fields = ['id', 'username', 'photo']
    user = current_app.redis.hmget('user:%s'%uid, fields)
    user = dict(zip(fields, user))

    user['listing_count'] = current_app.redis.zcard('user:%s:timeline'%uid) or 0
    user['following_count'] = current_app.redis.zcard('user:%s:following'%uid) or 0
    user['follower_count'] = current_app.redis.zcard('user:%s:follower'%uid) or 0

    followingid_list = current_app.redis.zrevrange('user:%s:following'%uid, rev_since_id, rev_since_id+PAGE_SIZE)
    page = page + 1

    followings = []
    for id in followingid_list:
        following = current_app.redis.hmget('user:%s'%id, fields)
        following = dict(zip(fields, following))
        followings.append(following)

    if current_app.redis.zscore('user:%s:follower'%g.user['id'], uid):
        user['followed'] = True

    if request.is_xhr:
        return jsonify(user=user, followings=followings, since_id=since_id, page=page)

    return render_template('following.html', user=user, followings=followings, since_id=since_id, page=page)


@bp_account.route('/follower/<int:uid>')
@login_required
def user_follower(uid):
    follower_count = current_app.redis.zcard('user:%s:follower'%uid)
    since_id = int(request.args.get('since_id', follower_count))
    page = int(request.args.get('page', 1))
    rev_since_id = follower_count - since_id + (page-1)*PAGE_SIZE

    fields = ['id', 'username', 'photo']
    user = current_app.redis.hmget('user:%s'%uid, fields)
    user = dict(zip(fields, user))

    user['listing_count'] = current_app.redis.zcard('user:%s:timeline'%uid) or 0
    user['following_count'] = current_app.redis.zcard('user:%s:following'%uid) or 0
    user['followed_count'] = current_app.redis.zcard('user:%s:follower'%uid) or 0

    if current_app.redis.zscore('user:%s:follower'%g.user['id'], uid):
        user['followed'] = True

    followedid_list = current_app.redis.zrevrange('user:%s:follower'%uid, rev_since_id, rev_since_id+PAGE_SIZE)
    page = page + 1

    followers = []
    for id in followedid_list:
        f = current_app.redis.hmget('user:%s'%id, fields)
        f = dict(zip(fields, f))
        followers.append(f)

    if request.is_xhr:
        return jsonify(user=user, followers=followers, since_id=since_id, page=page)

    return render_template('follower.html', user=user, followers=followers, since_id=since_id, page=page)


@bp_account.route('/follow/<int:uid>', methods=['POST'])
@login_required
def follow(uid):
    if not current_app.redis.exists('user:%s'%uid):
        abort(404)

    current_app.redis.zadd('user:%s:follower'%g.user['id'], uid, time.time())
    current_app.redis.zadd('user:%s:following'%uid, g.user['id'], time.time())
    postid_list = current_app.redis.zrevrange('user:%s:timeline'%uid, 0, -1)
    for pid in postid_list:
        current_app.redis.zadd('user:%s:feed'%g.user['id'], pid, time.time())
    return jsonify(followed=True)


@bp_account.route('/unfollow/<int:uid>', methods=['POST'])
@login_required
def unfollow(uid):
    if not current_app.redis.exists('user:%s'%uid):
        abort(404)

    current_app.redis.zrem('user:%s:follower'%g.user['id'], uid)
    current_app.redis.zrem('user:%s:following'%uid, g.user['id'])
    postid_list = current_app.redis.zrange('user:%s:timeline'%uid, 0, -1)
    for pid in postid_list:
        current_app.redis.zrem('user:%s:feed'%g.user['id'], pid)
    return jsonify(followed=False)
