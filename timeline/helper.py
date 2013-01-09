from flask import current_app

def get_timeline(postid_list, user=None):
    timeline = []
    if user:
        for pid in postid_list:
            post = current_app.redis.hgetall('post:%s'%pid)
            post['user'] = current_app.redis.hgetall('user:%s'%post['uid'])
            post['like_count'] = current_app.redis.zcard('post:%s:like'%pid)
            post['comment_count'] = current_app.redis.zcard('post:%s:comment'%pid)
            post_like_ids = current_app.redis.zrange('post:%s:like'%pid, 0, -1)
            if user['id'] in post_like_ids:
                post['liked'] = True
            timeline.append(post)
    else:
        for pid in postid_list:
            post = current_app.redis.hgetall('post:%s'%pid)
            post['user'] = current_app.redis.hgetall('user:%s'%post['uid'])
            post['like_count'] = current_app.redis.zcard('post:%s:like'%pid)
            post['comment_count'] = current_app.redis.zcard('post:%s:comment'%pid)
            timeline.append(post)
    return timeline


def get_comment(pid, since_id, count):
    comment_ids = current_app.redis.zrange('post:%s:comment'%pid, since_id, count)
    comments = []
    fields = ['id', 'username', 'photo']
    for commentid in comment_ids:
        comment = current_app.redis.hgetall('comment:%s'%commentid)
        user = current_app.redis.hmget('user:%s'%comment['uid'], fields)
        comment['user'] = dict(zip(fields, user))
        comments.append(comment)
    return comments
