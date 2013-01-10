from flask import Blueprint, current_app, request, render_template, g, \
        jsonify
from account.utils import login_required
from helper import get_timeline, get_comment

bp_timeline = Blueprint('timeline', __name__)

PAGE_SIZE = 20

@bp_timeline.route('/public')
@login_required
def public():
    global_timeline_count = current_app.redis.zcard('global_timeline')
    since_id = int(request.args.get('since_id', global_timeline_count))
    page = int(request.args.get('page', 1))
    rev_since_id = global_timeline_count - since_id + (page-1)*PAGE_SIZE

    recent_postids = current_app.redis.zrevrange('global_timeline', rev_since_id, rev_since_id+PAGE_SIZE)
    page += 1
    public_timeline = get_timeline(recent_postids, g.user)

    if request.is_xhr:
        return jsonify(timeline=public_timeline, since_id=since_id, page=page)

    return render_template('timeline/public.html', timeline=public_timeline, since_id=since_id, page=page)


@bp_timeline.route('/feed')
@login_required
def feed():
    user_feed_count = current_app.redis.zcard('user:%s:feed'%g.user['id'])
    since_id = int(request.args.get('since_id', user_feed_count))
    page = int(request.args.get('page', 1))
    rev_since_id = user_feed_count - since_id + (page-1)*PAGE_SIZE

    recent_postids = current_app.redis.zrevrange('user:%s:feed'%g.user['id'], rev_since_id, rev_since_id+PAGE_SIZE)
    page += 1
    feed_timeline = get_timeline(recent_postids, g.user)

    if request.is_xhr:
        return jsonify(timeline=feed_timeline, since_id=since_id, page=page)

    return render_template('timeline/feed.html', timeline=feed_timeline, since_id=since_id, page=page)


@bp_timeline.route('/comments')
@login_required
def comments():
    user_comment_count = current_app.redis.zcard('user:%s:comment'%g.user['id'])
    since_id = int(request.args.get('since_id', user_comment_count))
    page = int(request.args.get('page', 1))
    rev_since_id = user_comment_count - since_id + (page-1)*PAGE_SIZE

    recent_comment_ids = current_app.redis.zrevrange('user:%s:comment'%g.user['id'], rev_since_id, rev_since_id+PAGE_SIZE)
    page += 1
    comment_timeline = get_comment(recent_comment_ids)

    if request.is_xhr:
        return jsonify(timeline=comment_timeline)

    return render_template('timeline/comments.html', timeline=comment_timeline, since_id=since_id, page=page)


@bp_timeline.route('/closet/<int:uid>')
@login_required
def closet(uid):
    user_timeline_count = current_app.redis.zcard('user:%s:timeline'%uid)
    since_id = int(request.args.get('since_id', user_timeline_count))
    page = int(request.args.get('page', 1))
    rev_since_id = user_timeline_count - since_id + (page-1)*PAGE_SIZE

    recent_postids = current_app.redis.zrevrange('user:%s:timeline'%uid, rev_since_id, rev_since_id+PAGE_SIZE)
    page += 1
    user_timeline = get_timeline(recent_postids)

    fields = ['id', 'username', 'photo']
    user = current_app.redis.hmget('user:%s'%uid, fields)
    user = dict(zip(fields, user))

    if current_app.redis.zscore('user:%s:following'%g.user['id'], uid):
        user['followed'] = True

    user['listing_count'] = current_app.redis.zcard('user:%s:timeline'%uid) or 0
    user['following_count'] = current_app.redis.zcard('user:%s:following'%uid) or 0
    user['followed_count'] = current_app.redis.zcard('user:%s:follower'%uid) or 0

    if request.is_xhr:
        return jsonify(user=user, timeline=user_timeline, since_id=since_id, page=page)

    return render_template('timeline/closet.html', user=user, timeline=user_timeline, since_id=since_id, page=page)


@bp_timeline.route('/likes')
@login_required
def likes():
    likes_count = current_app.redis.zcard('user:%s:like'%g.user['id'])
    since_id = int(request.args.get('since_id', likes_count))
    page = int(request.args.get('page', 1))
    rev_since_id = likes_count - since_id + (page-1)*PAGE_SIZE

    user_like_id_list = current_app.redis.zrevrange('user:%s:like'%g.user['id'], rev_since_id, rev_since_id+PAGE_SIZE)
    page += 1
    user_likes = get_timeline(user_like_id_list)

    if request.is_xhr:
        return jsonify(timeline=user_likes, since_id=since_id, page=page)

    return render_template('timeline/likes.html', timeline=user_likes, since_id=since_id, page=page)


@bp_timeline.route('/explore/category/<filter>')
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

    page += 1
    filtered_timeline = get_timeline(postid_list, g.user)

    if request.is_xhr:
        return jsonify(timeline=filtered_timeline, since_id=since_id, page=page)

    return render_template('timeline/explore.html', timeline=filtered_timeline, since_id=since_id, page=page)


@bp_timeline.route('/explore/brand/<filter>')
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

    page += 1
    filtered_timeline = get_timeline(postid_list, g.user)

    if request.is_xhr:
        return jsonify(timeline=filtered_timeline, since_id=since_id, page=page)

    return render_template('timeline/explore.html', timeline=filtered_timeline, since_id=since_id, page=page)
