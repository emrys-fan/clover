#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
from flask import Blueprint, request, current_app, g, jsonify, \
        render_template, abort, flash
from account.utils import login_required
from forms import PostForm

bp_item = Blueprint('item', __name__)

PAGE_SIZE = 20

@bp_item.route('/item/create', methods=['GET', 'POST'])
@login_required
def create_item():
    form  = PostForm()

    if form.validate_on_submit():
        post = form.save()
        flash('发布成功')
        return jsonify(postid=post['postid'], message='success')

    return render_template('item/create.html', form=form)


@bp_item.route('/item/show/<int:pid>')
@login_required
def show_item(pid):
    item_comment_count = current_app.redis.zcard('post:%s:comment'%pid)
    since_id = int(request.args.get('since_id', item_comment_count))
    page = int(request.args.get('page', 1))
    rev_since_id = item_comment_count - since_id + (page-1)*PAGE_SIZE

    request_item = current_app.redis.hgetall('post:%s'%pid)
    if not request_item:
        abort(404)
    fields = ['id', 'username', 'photo']
    user = current_app.redis.hmget('user:%s'%request_item['uid'], fields)
    user = dict(zip(fields, user))

    if current_app.redis.zscore('user:%s:like'%g.user['id'], pid):
        request_item['liked'] = True

    post_commentid_list = current_app.redis.zrevrange('post:%s:comment'%pid, rev_since_id, rev_since_id+PAGE_SIZE)
    page = page + 1
    comments = []
    fields = ['id', 'username', 'photo']
    for commentid in post_commentid_list:
        comment = current_app.redis.hgetall('comment:%s'%commentid)
        comment_user = current_app.redis.hmget('user:%s'%comment['uid'], fields)
        comment['user'] = dict(zip(fields, comment_user))
        comments.append(comment)

    if request.is_xhr:
        return jsonify(request_item=request_item,
                user=user,
                comments=comments,
                since_id=since_id,
                page=page)

    return render_template('item/item.html',
            request_item=request_item,
            user=user,
            comments=comments,
            since_id=since_id,
            page=page)


@bp_item.route('/comment/item/<int:pid>', methods=['POST'])
@login_required
def add_comment(pid):
    comment_text = request.form.get('comment', None)

    if not comment_text:
        return jsonify()

    commentid = current_app.redis.hincrby('system', 'comment_id', 1)

    comment = {'text': comment_text,
            'uid':g.user['id'],
            'cid': commentid,
            'pid': pid,
            'publish_time':time.strftime('%Y-%m-%dT%H:%M:%S%z')}

    current_app.redis.hmset('comment:%s'%commentid, comment)
    current_app.redis.zadd('post:%s:comment'%pid, commentid, time.time())
    current_app.redis.zadd('user:%s:comment'%g.user['id'], commentid, time.time())

    return jsonify(comment=comment)


@bp_item.route('/item/comment/<int:pid>')
@login_required
def show_comment(pid):
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
        comment = current_app.redis.hgetall('comment:%s' % commentid)
        fields = ['id', 'username', 'photo']
        user = current_app.redis.hmget('user:%s'%comment['uid'], fields)
        comment['user'] = dict(zip(fields, user))
        comments.append(comment)

    return jsonify(comments=comments, since_id=since_id, page=page)


@bp_item.route('/like/<int:pid>')
@login_required
def like(pid):
    exist = current_app.redis.exists('post:%s'%pid)
    if exist:
        current_app.redis.zadd('post:%s:like'%pid, g.user['id'], time.time())
        current_app.redis.zadd('user:%s:like'%g.user['id'], pid, time.time())
        return jsonify(liked=True)
    else:
        abort(404)


@bp_item.route('/unlike/<int:pid>')
@login_required
def unlike(pid):
    exist = current_app.redis.exists('post:%s'%pid)

    if exist:
        current_app.redis.zrem('post:%s:like'%pid, g.user['id'])
        current_app.redis.zrem('user:%s:like'%g.user['id'], pid)
        return jsonify(liked=False)
    else:
        abort(404)
