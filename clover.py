#!/usr/bin/env python
# -*- coding: utf-8 -*-

import gevent.monkey
gevent.monkey.patch_all()

import time
import json
import uuid
from werkzeug.security import generate_password_hash, check_password_hash
from flask import request, render_template, abort, current_app, \
        session, url_for, g, flash, jsonify, redirect, Blueprint
from forms import LoginForm, RegisterForm, ProfileForm, PostForm, \
        InvitationForm
from utils import login_check, login_required, invitation_required, \
        get_timeline


clover = Blueprint('clover', __name__, template_folder='templates',
        static_folder='static')

PAGE_SIZE = 20

@clover.route('/')
@login_check
def index():
    recent_postids = current_app.redis.zrevrange('global_timeline', 0, PAGE_SIZE)
    public_timeline = get_timeline(recent_postids, g.user)
    return render_template('index.html', timeline=public_timeline)


@clover.route('/public')
@login_required
def public():
    global_timeline_count = current_app.redis.zcard('global_timeline')
    since_id = int(request.args.get('since_id', global_timeline_count))
    page = int(request.args.get('page', 1))
    rev_since_id = global_timeline_count - since_id + (page-1)*PAGE_SIZE

    recent_postids = current_app.redis.zrevrange('global_timeline', rev_since_id, rev_since_id+PAGE_SIZE)
    page = page + 1
    public_timeline = get_timeline(recent_postids, g.user)

    if request.is_xhr:
        return jsonify(timeline=public_timeline, since_id=since_id, page=page)

    return render_template('public.html', timeline=public_timeline, since_id=since_id, page=page)


@clover.route('/feed')
@login_required
def feed():
    user_feed_count = current_app.redis.zcard('user:%s:feed'%g.user['id'])
    since_id = int(request.args.get('since_id', user_feed_count))
    page = int(request.args.get('page', 1))
    rev_since_id = user_feed_count - since_id + (page-1)*PAGE_SIZE

    recent_postids = current_app.redis.zrevrange('user:%s:feed'%g.user['id'], rev_since_id, rev_since_id+PAGE_SIZE)
    page = page + 1
    feed_timeline = get_timeline(recent_postids, g.user)

    if request.is_xhr:
        return jsonify(timeline=feed_timeline, since_id=since_id, page=page)

    return render_template('feed.html', timeline=feed_timeline, since_id=since_id, page=page)


@clover.route('/closet/<int:uid>')
@login_required
def closet(uid):
    user_timeline_count = current_app.redis.zcard('user:%s:timeline'%uid)
    since_id = int(request.args.get('since_id', user_timeline_count))
    page = int(request.args.get('page', 1))
    rev_since_id = user_timeline_count - since_id + (page-1)*PAGE_SIZE

    recent_postids = current_app.redis.zrevrange('user:%s:timeline'%uid, rev_since_id, rev_since_id+PAGE_SIZE)
    page = page + 1
    user_timeline = get_timeline(recent_postids)

    fields = ['id', 'username', 'photo']
    user = current_app.redis.hmget('user:%d'%uid, fields)
    user = dict(zip(fields, user))

    if current_app.redis.zscore('user:%s:followed'%g.user['id'], uid):
        user['followed'] = True

    user['listing_count'] = current_app.redis.zcard('user:%s:timeline'%uid) or 0
    user['following_count'] = current_app.redis.zcard('user:%s:following'%uid) or 0
    user['followed_count'] = current_app.redis.zcard('user:%s:followed'%uid) or 0

    if request.is_xhr:
        return jsonify(user=user, timeline=user_timeline, since_id=since_id, page=page)

    return render_template('closet.html', user=user, timeline=user_timeline, since_id=since_id, page=page)


@clover.route('/publish', methods=['GET', 'POST'])
@login_required
def publish():
    form = PostForm()

    if form.validate_on_submit():
        photos = request.files.getlist('photo')

        photo_url_list = []
        for photo in photos:
            photo_name = current_app.uploaded_photos.save(photo)
            photo_url_list.append(current_app.uploaded_photos.url(photo_name))

        postid = current_app.redis.hincrby('system', 'nextPostId', 1)
        post = {'postid': postid,
                'publish_time': time.strftime('%Y-%m-%dT%H:%M:%S%z'),
                'title': form.title.data,
                'description': form.description.data,
                'original_price': form.original_price.data,
                'brand': form.brand.data,
                'current_price': form.current_price.data,
                'photos': json.dumps(photo_url_list),
                'size': form.size.data,
                'category': form.category.data,
                'uid': g.user['id']}

        current_app.redis.hmset('post:%s'%postid, post)
        current_app.redis.zadd('global_timeline', postid, time.time())
        current_app.redis.zadd('user:%s:timeline'%g.user['id'], postid, time.time())
        current_app.redis.zadd('category:%s'%form.category.data, postid, time.time())
        current_app.redis.zadd('category:%s:size:%s'%(form.category.data, form.size.data), postid, time.time())
        current_app.redis.zadd('brand:%s'%form.brand.data, postid, time.time())

        followings = current_app.redis.zrevrange('user:%s:following'%g.user['id'], 0, -1)
        for fid in followings:
            current_app.redis.zadd('user:%s:feed'%fid, postid, time.time())

        current_app.redis.hincrby('user:%s'%g.user['id'], 'invite_quota_left',
                current_app.config['PUBLISH_TO_INVITE_COEFFICIENT'])

        flash("Post successful!")

        return redirect(url_for('.closet', id=g.user['id']))

    return render_template("publish.html", form=form)


@clover.route('/item/create', methods=['POST'])
@login_required
def create_item():
    postid = current_app.redis.hincrby('system', 'nextPostId', 1)
    form = request.form
    post = {'postid': postid,
            'publish_time': time.strftime('%Y-%m-%dT%H:%M:%S%z'),
            'title': form.get('title',''),
            'description': form.get('description', ''),
            'original_price': form.get('original_price', ''),
            'brand': form.get('brand', ''),
            'current_price': form.get('current_price', ''),
            'photos': json.dumps(form.get('photos').split(';')),
            'size': form.get('size', ''),
            'category': form.get('category', 'others'),
            'uid': g.user['id']}
    current_app.redis.hmset('post:%s'%postid, post)
    current_app.redis.zadd('global_timeline', postid, time.time())
    current_app.redis.zadd('user:%s:timeline'%g.user['id'], postid, time.time())
    current_app.redis.zadd('category:%s'%form.get('category'), postid, time.time())
    current_app.redis.zadd('category:%s:size:%s'%(form.get('category'), form.get('size')), postid, time.time())
    current_app.redis.zadd('brand:%s'%form.get('brand'), postid, time.time())

    followings = current_app.redis.zrevrange('user:%s:following'%g.user['id'], 0, -1)
    for fid in followings:
        current_app.redis.zadd('user:%s:feed'%fid, postid, time.time())

    current_app.redis.hincrby('user:%s'%g.user['id'], 'invite_quota_left',
            current_app.config['PUBLISH_TO_INVITE_COEFFICIENT'])

    return jsonify(postid=postid, message='success')

@clover.route('/item/show/<int:pid>')
@login_required
def item(pid):
    item_comment_count = current_app.redis.zcard('post:%s:comment'%pid)
    since_id = int(request.args.get('since_id', item_comment_count))
    page = int(request.args.get('page', 1))
    rev_since_id = item_comment_count - since_id + (page-1)*PAGE_SIZE

    request_item = current_app.redis.hgetall('post:%s'%pid)
    if not request_item:
        abort(404)
    request_item['photos'] = json.loads(request_item['photos'])
    fields = ['id', 'username', 'photo']
    user = current_app.redis.hmget('user:%s'%request_item['uid'], fields)
    user = dict(zip(fields, user))
    request_item['user'] = user

    if current_app.redis.zscore('user:%s:like'%g.user['id'], pid):
        request_item['liked'] = True

    post_commentid_list = current_app.redis.zrevrange('post:%s:comment'%pid, rev_since_id, rev_since_id+PAGE_SIZE)
    page = page + 1
    comments = []
    for commentid in post_commentid_list:
        comments.append(json.loads(current_app.redis.hget('comment', commentid)))

    if request.is_xhr:
        return jsonify(request_item=request_item,
                user=user,
                comments=comments,
                since_id=since_id,
                page=page)

    user_postid_list = current_app.redis.zrange('user:%s:timeline'%user['id'], 0, 7)
    user_timeline = get_timeline(user_postid_list)

    return render_template('item.html',
            request_item=request_item,
            user=user,
            timeline=user_timeline,
            comments=comments,
            since_id=since_id,
            page=page)

@clover.route('/item/comment/<int:pid>')
@login_required
def item_comment(pid):
    item_comment_count = current_app.redis.zcard('post:%s:comment'%pid)
    since_id = int(request.args.get('since_id', item_comment_count))
    page = int(request.args.get('page', 1))
    rev_since_id = item_comment_count - since_id + (page-1)*PAGE_SIZE

    request_item = current_app.redis.hgetall('post:%s'%pid)

    if not request_item:
        abort(404)

    post_commentid_list = current_app.redis.zrevrange('post:%s:comment'%pid, rev_since_id, rev_since_id+PAGE_SIZE)
    page = page + 1

    comments = []
    for commentid in post_commentid_list:
        comments.append(json.loads(current_app.redis.hget('comment', commentid)))

    return jsonify(comments=comments, since_id=since_id, page=page)


@clover.route('/party')
@login_required
def party():
    """docstring for party"""
    parties = []
    return render_template('party.html', parties=parties)

@clover.route('/explore/category/<filter>')
@login_required
def explore_category(filter):
    size = request.args.get('size', None)
    page = int(request.args.get('page', 1))
    since_id = 0
    postid_list = []

    if size:
        category_count = current_app.redis.zcard('category:%s:size:%s'%(filter,size))
        since_id = int(request.args.get('since_id', category_count))
        rev_since_id = category_count - since_id + (page-1)*PAGE_SIZE
        postid_list = current_app.redis.zrevrange('category:%s:size:%s'%(filter,size), rev_since_id, rev_since_id+PAGE_SIZE)
    else:
        category_count = current_app.redis.zcard('category:%s'%filter)
        since_id = int(request.args.get('since_id', category_count))
        rev_since_id = category_count - since_id + (page-1)*PAGE_SIZE
        postid_list = current_app.redis.zrevrange('category:%s'%filter, rev_since_id, rev_since_id+PAGE_SIZE)

    page = page + 1
    filtered_timeline = get_timeline(postid_list, g.user)

    if request.is_xhr:
        return jsonify(timeline=filtered_timeline, since_id=since_id, page=page)

    return render_template('explore.html', timeline=filtered_timeline, since_id=since_id, page=page)


@clover.route('/explore/brand/<filter>')
@login_required
def explore_brand(filter):
    page = int(request.args.get('page', 1))
    category = request.args.get('category', None)
    since_id = 0
    postid_list = []

    if category:
        brand_count = current_app.redis.zcard('brand:%s:category:%s'%(filter, category))
        since_id = request.args.get('since_id', brand_count)
        rev_since_id = brand_count - since_id + (page-1)*PAGE_SIZE
        postid_list = current_app.redis.zrevrange('brand:%s:category:%s'%(filter, category), rev_since_id, rev_since_id+PAGE_SIZE)
    else:
        brand_count = current_app.redis.zcard('brand:%s'%filter)
        since_id = request.args.get('since_id', brand_count)
        rev_since_id = brand_count - since_id + (page-1)*PAGE_SIZE
        postid_list = current_app.redis.zrevrange('brand:%s'%filter, rev_since_id, rev_since_id+PAGE_SIZE)

    page = page + 1
    filtered_timeline = get_timeline(postid_list, g.user)

    if request.is_xhr:
        return jsonify(timeline=filtered_timeline, since_id=since_id, page=page)

    return render_template('explore.html', timeline=filtered_timeline, since_id=since_id, page=page)


@clover.route('/buy/<int:pid>')
@login_required
def buy(pid):
    return render_template('buy.html')


@clover.route('/user/following/<int:uid>')
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
    user['followed_count'] = current_app.redis.zcard('user:%s:followed'%uid) or 0

    followingid_list = current_app.redis.zrevrange('user:%s:following'%uid, rev_since_id, rev_since_id+PAGE_SIZE)
    page = page + 1

    followings = []
    for id in followingid_list:
        following = current_app.redis.hmget('user:%s'%id, fields)
        following = dict(zip(fields, following))
        followings.append(following)

    if current_app.redis.zscore('user:%s:followed'%g.user['id'], uid):
        user['followed'] = True

    if request.is_xhr:
        return jsonify(user=user, followings=followings, since_id=since_id, page=page)

    return render_template('following.html', user=user, followings=followings, since_id=since_id, page=page)


@clover.route('/user/followed/<int:uid>')
@login_required
def followed(uid):
    followed_count = current_app.redis.zcard('user:%s:followed'%uid)
    since_id = int(request.args.get('since_id', followed_count))
    page = int(request.args.get('page', 1))
    rev_since_id = followed_count - since_id + (page-1)*PAGE_SIZE

    fields = ['id', 'username', 'photo']
    user = current_app.redis.hmget('user:%s'%uid, fields)
    user = dict(zip(fields, user))

    user['listing_count'] = current_app.redis.zcard('user:%s:timeline'%uid) or 0
    user['following_count'] = current_app.redis.zcard('user:%s:following'%uid) or 0
    user['followed_count'] = current_app.redis.zcard('user:%s:followed'%uid) or 0

    if current_app.redis.zscore('user:%s:followed'%g.user['id'], uid):
        user['followed'] = True

    followedid_list = current_app.redis.zrevrange('user:%s:followed'%uid, rev_since_id, rev_since_id+PAGE_SIZE)
    page = page + 1

    followed = []
    for id in followedid_list:
        f = current_app.redis.hmget('user:%s'%id, fields)
        f = dict(zip(fields, f))
        followed.append(f)

    if request.is_xhr:
        return jsonify(user=user, followed=followed, since_id=since_id, page=page)

    return render_template('followed.html', user=user, followed=followed, since_id=since_id, page=page)


@clover.route('/invitations')
@login_required
def invitations():
    return render_template('invitations.html')


@clover.route('/orders')
@login_required
def orders():
    orders = []
    return render_template('orders.html', orders=orders)


@clover.route('/purchases')
@login_required
def purchases():
    purchases = []
    return render_template('purchases.html', purchases=purchases)


@clover.route('/sales')
@login_required
def sales():
    sales = []
    return render_template('sales.html', sales=sales)


@clover.route('/search')
def search():
    return render_template('search.html')


@clover.route('/likes')
@login_required
def likes():
    likes_count = current_app.redis.zcard('user:%s:like'%g.user['id'])
    since_id = int(request.args.get('since_id', likes_count))
    page = int(request.args.get('page', 1))
    rev_since_id = likes_count - since_id + (page-1)*PAGE_SIZE

    user_like_id_list = current_app.redis.zrevrange('user_likes:%s'%g.user['id'], rev_since_id, rev_since_id+PAGE_SIZE)
    page = page + 1
    user_likes = get_timeline(user_like_id_list)

    if request.is_xhr:
        return jsonify(likes=user_likes, since_id=since_id, page=page)

    return render_template('likes.html', likes=user_likes, since_id=since_id, page=page)


@clover.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    form = ProfileForm()

    if form.validate_on_submit():

        g.user.update({
            'username': form.username.data,
            'email': form.email.data,
            'about': form.about.data,
            'city': form.city.data,
            'website': form.website.data})

        current_app.logger.info('user: %s'%g.user)

        if g.user['email']:
            current_app.redis.set('email:%s:uid'%g.user['email'], g.user['id'])

        current_app.redis.hmset('user:%s'%g.user['id'], g.user)
        return redirect(url_for('.feed'))

    return render_template('settings.html', form=form)


@clover.route('/join/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    g.user = None
    current_app.logger.info('data: %s'%form.data)

    if form.validate_on_submit():
        uid = current_app.redis.get('uname:%s:uid'%form.username.data)
        current_app.logger.info('uid:%s' % uid)

        if not uid:
            flash("用户名或密码错误")
            return render_template('login.html', form=form)

        g.user = current_app.redis.hgetall('user:%s'%uid)

        if g.user['active'] == "False":
            flash("用户未激活")
            return redirect(url_for('.index'))

        if not check_password_hash(g.user['password'], form.password.data):
            flash("用户名或密码错误")
            return render_template('login.html', form=form)

        session['session_token'] = uuid.uuid4().get_hex()

        user_session = {'session_token': session['session_token'],
                'id': uid,
                'username': g.user['username'],
                'create_time': time.time()}

        current_app.redis.hmset('session:%s'%session['session_token'], user_session)
        flash("成功登录")

        return redirect(url_for('.feed'))

    return  render_template('login.html', form=form)


@clover.route('/join/register', methods=['GET', 'POST'])
@invitation_required
def register():
    g.user = None
    form = RegisterForm()

    if form.validate_on_submit():
        username = form.username.data
        uid = current_app.redis.get('uname:%s:uid'%username)

        if uid:
            flash('该用户名已经被注册!')
            return render_template('register.html', form=form)

        uid = current_app.redis.hincrby('system', 'next_uid', 1)
        photo_url = None

        if form.photo.data:
            photo = current_app.uploaded_photos.save(request.files.get('photo'))
            photo_url = current_app.uploaded_photos.url(photo)

        new_user = {'id': uid,
                'username': username,
                'password': generate_password_hash(form.password.data),
                'email': form.email.data,
                'active': True,
                'photo': photo_url}

        current_app.redis.set('uname:%s:uid'%username, uid)
        current_app.redis.hmset('user:%s'%uid, new_user)

        if hasattr(g, 'recommender'):
            current_app.redis.zadd('user:%s:invited'%g.recommender['id'], new_user['id'], time.time())
            current_app.redis.hset('user:%s'%new_user['id'], 'rid', g.recommender['id'])
            current_app.redis.hincrby('user:%s'%g.recommender['id'], 'invite_quota_left', -1)
            session.pop('uid', None)

        flash('注册成功')

        return redirect(url_for('.login'))

    return render_template('register.html', form=form)


@clover.route('/logout')
@login_required
def logout():
    session.pop('session_token', None)
    return redirect(url_for('.index'))


@clover.route('/join/invitation', methods=['GET', 'POST'])
def join_with_invitation():
    form = InvitationForm()
    next = request.args.get('next') or url_for('.register')

    if form.validate_on_submit():
        username = form.username.data
        recommender_id = current_app.redis.get('uname:%s:uid'%username)

        current_app.logger.info('recommender_id:%s' % recommender_id)

        if not recommender_id:
            flash("查无此人")
            return render_template('join_with_invitation.html', form=form, next=next)

        fields = ['id', 'username', 'photo']
        recommender = current_app.redis.hmget('user:%s'%recommender_id, fields)
        recommender = dict(zip(fields, recommender))
        current_app.logger.info('recommender: %s' % recommender)
        if int(recommender.get('invite_quota_left', 0)) < 1:
            flash("邀请名额已用完")
            return render_template('join_with_invitation.html', form=form, next=next)

        session['uid'] = recommender_id

        return redirect(next)

    return render_template('join_with_invitation.html', form=form, next=next)


@clover.route('/auth/weibo',methods=['GET'])
@invitation_required
def auth_weibo():
    g.user = None
    access_token = request.cookies.get('access_token', None)
    client = current_app.client()

    if access_token  :
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

        session['session_token'] = uuid.uuid4().get_hex()

        if exist_weibo:
            uid = exist_weibo['uid']
            fields = ['id', 'username', 'photo']
            g.user = current_app.redis.hmget('user:%s'%uid, fields)
            g.user = dict(zip(fields, user))

            user_session = {'session_token': session['session_token'],
                    'id': uid,
                    'username': g.user['username'],
                    'create_time': time.time()}

            # refresh weibo information
            current_app.redis.hmset('weibo:%s'%weibo['id'], weibo)
            current_app.redis.hmset('session:%s'%session['session_token'], user_session)
        else:
            uid = current_app.redis.hincrby('system', 'next_uid', 1)
            weibo.update({'uid': uid})

            user_session = {'session_token': session['session_token'],
                    'id': uid,
                    'username': weibo['screen_name'],
                    'create_time': time.time()}

            g.user = {'id': uid,
                    'username': weibo['screen_name'],
                    'active': True,
                    'photo': weibo['profile_image_url'],
                    'weibo': weibo['id']}

            current_app.redis.hmset('weibo:%s'%weibo['id'], weibo)
            current_app.redis.hmset('session:%s'%session['session_token'], user_session)
            current_app.redis.hmset('user:%s'%uid, g.user)

        if hasattr(g, 'recommender'):
            current_app.redis.zadd('user:%s:invited'%g.recommender['id'], g.user['id'], time.time())
            current_app.redis.hset('user:%s'%g.user['id'], 'rid', g.recommender['id'])
            current_app.redis.hincrby('user:%s'%g.recommender['id'], 'invite_quota_left', -1)
            session.pop('uid', None)

        return redirect(url_for('.index'))

    return redirect(client.authorize_url)


@clover.route('/comment/item/<int:pid>', methods=['POST'])
@login_required
def addcomment(pid):
    comment_text = request.form.get('comment', None)

    if comment_text:
        return jsonify()

    commentid = current_app.redis.hincrby('system', 'comment_id', 1)

    comment = {'text': comment_text,
            'user':g.user,
            'cid': commentid,
            'publish_time':time.strftime('%Y-%m-%dT%H:%M:%S%z')}

    current_app.redis.hset('comment', commentid, json.dumps(comment))
    current_app.redis.zadd('post:%s:comment'%pid, commentid, time.time())
    current_app.redis.zadd('user:%s:comment'%g.user['id'], commentid, time.time())

    return jsonify(comment=comment)


@clover.route('/like/<int:pid>', methods=['POST'])
@login_required
def like(pid):
    exist = current_app.redis.exists('post:%s'%pid)
    current_app.logger.info('exist:%s'%exist)
    if exist:
        current_app.redis.zadd('post:%s:like'%pid, g.user['id'], time.time())
        current_app.redis.zadd('user:%s:like'%g.user['id'], pid, time.time())
        return jsonify(liked=True)
    else:
        abort(404)


@clover.route('/unlike/<int:pid>', methods=['POST'])
@login_required
def unlike(pid):
    exist = current_app.redis.exists('post:%s'%pid)

    if exist:
        current_app.redis.zrem('post:%s:like'%pid, g.user['id'])
        current_app.redis.zrem('user:%s:like'%g.user['id'], pid)
        return jsonify(liked=False)
    else:
        abort(404)


@clover.route('/share/<int:pid>', methods=['POST'])
@login_required
def share(pid):
    exist = current_app.redis.exists('post:%s'%pid)

    if exist:
        current_app.redis.zrem('post:%s:share'%pid, g.user['id'])
        current_app.redis.zrem('user:%s:share'%g.user['id'], pid)
        return jsonify()
    else:
        abort(404)


@clover.route('/unfollow/<int:uid>', methods=['POST'])
@login_required
def unfollow_user(uid):
    if not current_app.redis.exists('user:%s'%uid):
        abort(404)

    current_app.redis.zrem('user:%s:followed'%g.user['id'], uid)
    current_app.redis.zrem('user:%s:following'%uid, g.user['id'])
    postid_list = current_app.redis.zrange('user:%s:timeline'%uid, 0, -1)
    for pid in postid_list:
        current_app.redis.zrem('user:%s:feed'%g.user['id'], pid)
    return jsonify(followed=False)


@clover.route('/follow/<int:uid>', methods=['POST'])
@login_required
def follow_user(uid):
    if not current_app.redis.exists('user:%s'%uid):
        abort(404)

    current_app.redis.zadd('user:%s:followed'%g.user['id'], uid, time.time())
    current_app.redis.zadd('user:%s:following'%uid, g.user['id'], time.time())
    postid_list = current_app.redis.zrevrange('user:%s:timeline'%uid, 0, -1)
    for pid in postid_list:
        current_app.redis.zadd('user:%s:feed'%g.user['id'], pid, time.time())
    return jsonify(followed=True)


@clover.route('/about')
def about():
    return  render_template('about.html')


@clover.route('/contact')
def contact():
    return  render_template('contact.html')


@clover.route('/faq')
def faq():
    return  render_template('faq.html')


@clover.route('/jobs')
def jobs():
    return  render_template('jobs.html')


@clover.route('/blog')
def blog():
    return  render_template('blog.html')
