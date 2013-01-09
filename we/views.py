from flask import Blueprint, render_template

bp_we = Blueprint('we', __name__)

@bp_we.route('/about')
def about():
    return render_template('we/about.html')


@bp_we.route('/contact')
def contact():
    return render_template('we/contact.html')


@bp_we.route('/faq')
def faq():
    return render_template('we/faq.html')


@bp_we.route('/jobs')
def jobs():
    return render_template('we/jobs.html')


@bp_we.route('/blog')
def blog():
    return render_template('we/blog.html')
