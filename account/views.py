#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
from flask import Blueprint, current_app, render_template, request, g, \
        redirect, url_for, flash
from .forms import SigninForm, SignupForm, ProfileForm, \
        API_SigninForm, API_SignupForm, API_RecommemderForm, \
        API_ProfileForm, API_PasswordFrom
from .helpers import login, logout
from .decorators import login_required
from snippets import jsonify

bp_account = Blueprint('account', __name__)

PAGE_SIZE = 20


@bp_account.route('/signup', methods=['GET', 'POST'])
def signup():
    form = SignupForm()

    if form.validate_on_submit():
        user = form.save()
        login(user)
        flash('注册成功')
        return redirect(url_for('timeline.feed'))

    return render_template('account/signup.html', form=form)


@bp_account.route('/api/signup', methods=['POST'])
def api_signup():
    form = API_SignupForm()

    if form.validate_on_submit():
        user = form.save()
        login(user)
        return jsonify(user=user)

    return jsonify(message=form.errors, status_code=400)


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

@bp_account.route('/api/signin', methods=['POST'])
def api_signin():
    next_url = request.args.get('next', '/')

    form = API_SigninForm()
    if form.validate_on_submit():
        login(form.user)
        return jsonify(user=form.user)

    return jsonify(next_url=next_url, message="error", status_code=400)


@bp_account.route('/api/following/<int:uid>')
@bp_account.route('/following/<int:uid>')
@login_required
def following(uid):
    following_count = current_app.redis.zcard('user:%s:following'%uid)
    since_id = int(request.args.get('since_id', following_count))
    page = int(request.args.get('page', 1))
    rev_since_id = following_count - since_id + (page-1)*PAGE_SIZE

    fields = ['id', 'username', 'photo', 'about']
    user = current_app.redis.hmget('user:%s'%uid, fields)
    user = dict(zip(fields, user))

    user['listing_count'] = current_app.redis.zcard('user:%s:timeline'%uid) or 0
    user['following_count'] = current_app.redis.zcard('user:%s:following'%uid) or 0
    user['follower_count'] = current_app.redis.zcard('user:%s:follower'%uid) or 0

    followingid_list = current_app.redis.zrevrange('user:%s:following'%uid,
            rev_since_id,
            rev_since_id+PAGE_SIZE)
    page += 1

    followings = []
    for id in followingid_list:
        following = current_app.redis.hmget('user:%s'%id, fields)
        following = dict(zip(fields, following))
        followings.append(following)

    if current_app.redis.zscore('user:%s:following'%g.user['id'], uid):
        user['followed'] = True

    if request.is_xhr or request.headers.get('X-Clover-Access', None):
        return jsonify(user=user,
                followings=followings,
                since_id=since_id,
                page=page)

    return render_template('account/following.html',
            user=user,
            followings=followings,
            since_id=since_id, page=page)


@bp_account.route('/api/follower/<int:uid>')
@bp_account.route('/follower/<int:uid>')
@login_required
def follower(uid):
    follower_count = current_app.redis.zcard('user:%s:follower'%uid)
    since_id = int(request.args.get('since_id', follower_count))
    page = int(request.args.get('page', 1))
    rev_since_id = follower_count - since_id + (page-1)*PAGE_SIZE

    fields = ['id', 'username', 'photo', 'about']
    user = current_app.redis.hmget('user:%s'%uid, fields)
    user = dict(zip(fields, user))

    user['listing_count'] = current_app.redis.zcard('user:%s:timeline'%uid) or 0
    user['following_count'] = current_app.redis.zcard('user:%s:following'%uid) or 0
    user['followed_count'] = current_app.redis.zcard('user:%s:follower'%uid) or 0

    if current_app.redis.zscore('user:%s:follower'%g.user['id'], uid):
        user['followed'] = True

    followedid_list = current_app.redis.zrevrange('user:%s:follower'%uid,
            rev_since_id,
            rev_since_id+PAGE_SIZE)
    page += 1

    followers = []
    for id in followedid_list:
        f = current_app.redis.hmget('user:%s'%id, fields)
        f = dict(zip(fields, f))
        followers.append(f)

    if request.is_xhr or request.headers.get('X-Clover-Access', None):
        return jsonify(user=user,
                followers=followers,
                since_id=since_id,
                page=page)

    return render_template('account/follower.html',
            user=user,
            followers=followers,
            since_id=since_id,
            page=page)


@bp_account.route('/follow/<int:uid>')
@login_required
def follow(uid):
    if not current_app.redis.exists('user:%s'%uid)or g.user['id'] == str(uid):
        return jsonify(messge="用户不存在", status_code=400)

    # check if had followed
    if current_app.redis.zscore('user:%s:following'%g.user['id'], uid):
        return jsonify(followed=True, message="已关注")

    current_app.redis.zadd('user:%s:following'%g.user['id'], uid, time.time())
    current_app.redis.zadd('user:%s:follower'%uid, g.user['id'], time.time())
    postid_list = current_app.redis.zrevrange('user:%s:timeline'%uid, 0, -1)
    for pid in postid_list:
        current_app.redis.zadd('user:%s:feed'%g.user['id'], pid, time.time())

    return jsonify(followed=True, message="关注成功")


@bp_account.route('/unfollow/<int:uid>')
@login_required
def unfollow(uid):
    if not current_app.redis.exists('user:%s'%uid) or g.user['id'] == str(uid):
        return jsonify(messge="用户不存在", status_code=400)

    if not current_app.redis.zscore('user:%s:following'%g.user['id'], uid):
        return jsonify(followed=False, message='尚未关注', status_code=400)

    current_app.redis.zrem('user:%s:following'%g.user['id'], uid)
    current_app.redis.zrem('user:%s:follower'%uid, g.user['id'])
    postid_list = current_app.redis.zrange('user:%s:timeline'%uid, 0, -1)
    for pid in postid_list:
        current_app.redis.zrem('user:%s:feed'%g.user['id'], pid)

    return jsonify(followed=False, message="取消关注成功")


@bp_account.route('/profile/update', methods=['GET', 'POST'])
@login_required
def setting():
    form = ProfileForm()

    if form.validate_on_submit():
        form.save()
        flash("修改配置成功")
        return redirect(url_for('timeline.closet', uid=g.user['id']))

    # no way to prepopulate textarea, so do it manully
    form.about.data=g.user.get('about','')
    return render_template('account/setting.html', form=form)


@bp_account.route('/api/profile/update', methods=['GET', 'POST'])
@login_required
def update_profile():
    if request.method == 'GET':
        return jsonify(g.user)

    form = API_ProfileForm()
    if form.validate_on_submit():
        form.save()
        return jsonify(message="update profile successfully")
    return jsonify(message=form.errors, status_code=400)


@bp_account.route('/api/change/password', methods=['POST'])
@login_required
def change_password():
    form = API_PasswordFrom()

    if form.validate_on_submit():
        form.save()
        return jsonify(message="success")

    return jsonify(message=form.errors, status_code=400)


@bp_account.route('/api/signout')
@bp_account.route('/signout')
def signout():
    next_url = request.args.get('next', '/')
    logout()

    if request.headers.get('X-Clover-Access', None):
        return jsonify(message='success')

    flash('已退出')
    return redirect(next_url)


@bp_account.route('/api/check/recommender', methods=['POST'])
def check_recommemder():
    form = API_RecommemderForm()

    if form.validate_on_submit():
        return jsonify(recommender=form.recommender)

    return jsonify(message=form.errors)


@bp_account.route('/api/recommended')
@bp_account.route('/recommended')
@login_required
def recommended():
    invitation_count = current_app.redis.zcard('user:%s:recommended'%g.user['id'])
    since_id = int(request.args.get('since_id', invitation_count))
    page = int(request.args.get('page', 1))
    rev_since_id = invitation_count -since_id + (page-1)*PAGE_SIZE

    recent_invitation_ids = current_app.redis.zrevrange('user:%s:recommended'%g.user['id'],
            rev_since_id,
            rev_since_id+PAGE_SIZE)
    page += 1

    recommended = []
    fields = ['id', 'username', 'photo', 'about']
    for uid in recent_invitation_ids:
        user = current_app.redis.hmget('user:%s'%uid, fields)
        user = dict(zip(fields, user))
        recommended.append(user)

    if request.is_xhr or request.headers.get('X-Clover-Access', None):
        return jsonify(recommended=recommended, since_id=since_id, page=page)

    return render_template('account/recommended.html',
            recommended=recommended,
            since_id=since_id,
            page=page)
