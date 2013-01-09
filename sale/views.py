from flask import Blueprint, render_template

bp_sale = Blueprint('sale', __name__)

@bp_sale.route('/orders')
def orders():
    return render_template('sale/orders.html')


@bp_sale.route('/purchases')
def purchases():
    return render_template('sale/purchases.html')


@bp_sale.route('/sales')
def sales():
    return render_template('sale/sales.html')

@bp_sale.route('/buy')
def buy():
    return render_template('buy.html')
