from flask import Blueprint, current_app, request, render_template, g, \
        jsonify
from account.decorators import login_required
from helpler import get_timeline, get_comment

bp_timeline = Blueprint('timeline', __name__, template_folder='templates',
        static_folder='static')

page_size = current_app.config['PAGE_SIZE']

@bp_timeline.route('/public')
@login_required
def public():
    global_timeline_count = current_app.redis.zcard('global_timeline')
    since_id = int(request.args.get('since_id', global_timeline_count))
    page = int(request.args.get('page', 1))
    rev_since_id = global_timeline_count - since_id + (page-1)*page_size

    recent_postids = current_app.redis.zrevrange('global_timeline', rev_since_id, rev_since_id+page_size)
    page = page + 1
    public_timeline = get_timeline(recent_postids, g.user)

    if request.is_xhr:
        return jsonify(timeline=public_timeline, since_id=since_id, page=page)

    return render_template('public.html', timeline=public_timeline, since_id=since_id, page=page)


@bp_timeline.route('/feed')
@login_required
def feed():
    user_feed_count = current_app.redis.zcard('user:%s:feed'%g.user['id'])
    since_id = int(request.args.get('since_id', user_feed_count))
    page = int(request.args.get('page', 1))
    rev_since_id = user_feed_count - since_id + (page-1)*page_size

    recent_postids = current_app.redis.zrevrange('user:%s:feed'%g.user['id'], rev_since_id, rev_since_id+page_size)
    page = page + 1
    feed_timeline = get_timeline(recent_postids, g.user)

    if request.is_xhr:
        return jsonify(timeline=feed_timeline, since_id=since_id, page=page)

    return render_template('feed.html', timeline=feed_timeline, since_id=since_id, page=page)


@bp_timeline.route('/comments')
@login_required
def comments():
    user_comment_count = current_app.redis.zcard('user:%s:comment'%g.user['id'])
    since_id = int(request.args.get('since_id', user_comment_count))
    page = int(request.args.get('page', 1))
    rev_since_id = user_comment_count - since_id + (page-1)*page_size

    recent_comment_ids = current_app.redis.zrevrange('user:%s:comment'%g.user['id'], rev_since_id, rev_since_id+page_size)
    page = page + 1
    comment_timeline = get_comment(recent_comment_ids)

    if request.is_xhr:
        return jsonify(timeline=comment_timeline)

    return render_template('comments.html', timeline=comment_timeline, since_id=since_id, page=page)


@bp_timeline.route('/closet/<int:uid>')
@login_required
def closet(uid):
    user_timeline_count = current_app.redis.zcard('user:%s:timeline'%uid)
    since_id = int(request.args.get('since_id', user_timeline_count))
    page = int(request.args.get('page', 1))
    rev_since_id = user_timeline_count - since_id + (page-1)*page_size

    recent_postids = current_app.redis.zrevrange('user:%s:timeline'%uid, rev_since_id, rev_since_id+page_size)
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


@bp_timeline.route('/likes')
@login_required
def likes():
    likes_count = current_app.redis.zcard('user:%s:like'%g.user['id'])
    since_id = int(request.args.get('since_id', likes_count))
    page = int(request.args.get('page', 1))
    rev_since_id = likes_count - since_id + (page-1)*page_size

    user_like_id_list = current_app.redis.zrevrange('user_likes:%s'%g.user['id'], rev_since_id, rev_since_id+page_size)
    page = page + 1
    user_likes = get_timeline(user_like_id_list)

    if request.is_xhr:
        return jsonify(likes=user_likes, since_id=since_id, page=page)

    return render_template('likes.html', likes=user_likes, since_id=since_id, page=page)
