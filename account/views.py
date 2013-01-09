#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
import uuid
from flask import Blueprint, current_app, render_template, request, g, \
        redirect, url_for, flash, jsonify, abort, session
from forms import SigninForm, SignupForm, ProfileForm, InvitationForm
from helpers import login, logout, get_weibo_client
from utils import login_required, invitation_required

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


@bp_account.route('/signin/auth/weibo', methods=['GET'])
def weibo_signin():
    access_token = request.cookies.get('access_token', None)
    client = get_weibo_client(request.url)

    if access_token:
        return redirect(url_for('index'))

    if request.args.get("code", ''):
        code = request.args.get('code')
        client.set_code(code)
        user = client.get("users/show", uid=client.uid)
        fields = ["id", "screen_name", "profile_image_url"]
        weibo = {}

        for field in fields:
            weibo[field] = user.get(field)

        weibo.update({"access_token": client.access_token,
            "session_expires": client.expires_in})

        if weibo.get('id', None):
            exist_weibo = current_app.redis.hgetall('weibo:%s'%weibo['id'])
        else:
            abort(403)

        if exist_weibo:
            uid = exist_weibo['uid']
            g.user = current_app.redis.hgetall('user:%s'%uid)

            # refresh weibo information
            current_app.redis.hmset('weibo:%s'%weibo['id'], weibo)
            login(g.user)
            flash('成功登录')
            return redirect(url_for('index'))
        else:
            flash('请先行注册')
            return redirect('account.signup')

    return redirect(client.authorize_url)


@bp_account.route('/signup', methods=['GET', 'POST'])
@invitation_required
def signup():
    form = SignupForm()
    current_app.logger.info('sign info: %s', form.data)

    if form.validate_on_submit():
        current_app.logger.info('sign successfully')
        user = form.save()

        if hasattr(g, 'recommender'):
            current_app.redis.zadd('user:%s:invited'%g.recommender['id'], user['id'], time.time())
            current_app.redis.hset('user:%s'%user['id'], 'rid', g.recommender['id'])
            current_app.redis.hincrby('user:%s'%g.recommender['id'], 'invite_quota_left', -1)
            session.pop('rid', None)

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


@bp_account.route('/join/invitation', methods=['GET', 'POST'])
def confirm_invitation():
    form = InvitationForm()
    next = request.args.get('next', url_for('.signup'))

    if form.validate_on_submit():
        session['rid'] = g.recommender['id']
        return redirect(next)

    return render_template('account/confirm_invitation.html', form=form)


@bp_account.route('/invitations')
@login_required
def invitations():
    return render_template('account/invitations.html')


@bp_account.route('/auth/weibo',methods=['GET'])
@invitation_required
def auth_weibo():
    access_token = request.cookies.get('access_token', None)
    client = get_weibo_client(request.url)

    if access_token:
        return redirect('/')

    if request.args.get("code", ''):
        code = request.args.get('code')
        client.set_code(code)
        user = client.get("users/show", uid=client.uid)
        fields = ["id", "screen_name", "profile_image_url"]
        weibo = {}

        for field in fields:
            weibo[field] = user.get(field)

        weibo.update({"access_token": client.access_token,
            "session_expires": client.expires_in})

        if weibo.get('id', None):
            exist_weibo = current_app.redis.hgetall('weibo:%s'%weibo['id'])
        else:
            abort(403)

        if exist_weibo:
            uid = exist_weibo['uid']
            g.user = current_app.redis.hgetall('user:%s'%uid)

            # refresh weibo information
            current_app.redis.hmset('weibo:%s'%weibo['id'], weibo)
            login(g.user)
        else:
            uid = current_app.redis.hincrby('system', 'next_uid', 1)
            weibo.update({'uid': uid})

            g.user = {'id': uid,
                    'username': weibo['screen_name'],
                    'active': True,
                    'photo': weibo['profile_image_url'],
                    'weibo': weibo['id'],
                    'token': uuid.uuid4().get_hex()}

            current_app.redis.hmset('weibo:%s'%weibo['id'], weibo)
            current_app.redis.hmset('user:%s'%uid, g.user)
            login(g.user)

        if hasattr(g, 'recommender'):
            current_app.redis.zadd('user:%s:invited'%g.recommender['id'], g.user['id'], time.time())
            current_app.redis.hset('user:%s'%g.user['id'], 'rid', g.recommender['id'])
            current_app.redis.hincrby('user:%s'%g.recommender['id'], 'invite_quota_left', -1)
            session.pop('rid', None)

        return redirect(url_for('index'))

    return redirect(client.authorize_url)


@bp_account.route('/following/<int:uid>')
@login_required
def following(uid):
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
def follower(uid):
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


@bp_account.route('/follow/<int:uid>')
@login_required
def follow(uid):
    if not current_app.redis.exists('user:%s'%uid)or g.user['id'] == str(uid):
        abort(404)

    # check if had followed
    if current_app.redis.zscore('user:%s:following'%g.user['id'], uid):
        jsonify(followed=True, message="已关注")

    current_app.redis.zadd('user:%s:following'%g.user['id'], uid, time.time())
    current_app.redis.zadd('user:%s:followed'%uid, g.user['id'], time.time())
    postid_list = current_app.redis.zrevrange('user:%s:timeline'%uid, 0, -1)
    for pid in postid_list:
        current_app.redis.zadd('user:%s:feed'%g.user['id'], pid, time.time())

    return jsonify(followed=True, message="关注成功")


@bp_account.route('/unfollow/<int:uid>')
@login_required
def unfollow(uid):
    if not current_app.redis.exists('user:%s'%uid) or g.user['id'] == str(uid):
        abort(404)

    if not current_app.redis.zscore('user:%s:following'%g.user['id'], uid):
        return jsonify(followed=False, message='尚未关注')

    current_app.redis.zrem('user:%s:following'%g.user['id'], uid)
    current_app.redis.zrem('user:%s:followed'%uid, g.user['id'])
    postid_list = current_app.redis.zrange('user:%s:timeline'%uid, 0, -1)
    for pid in postid_list:
        current_app.redis.zrem('user:%s:feed'%g.user['id'], pid)
    return jsonify(followed=False, message="取消关注成功")
