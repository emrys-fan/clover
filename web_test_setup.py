#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
from app import app

ajax_headers = {'X-Requested-With': 'XMLHttpRequest'}

class AppTest(unittest.TestCase):

    def setUp(self):
        # disable invite mode for initial signup
        app.config['INVITE_MODE'] = False
        self.app = app.test_client()
        app.redis.flushdb()

        # register 6 users
        self.signup('someone1', 'default')
        self.signout()
        self.signup('someone2', 'default')
        self.signout()
        self.signup('someone3', 'default')
        self.signout()
        self.signup('someone4', 'default')
        self.signout()
        self.signup('someone5', 'default')
        self.signout()
        self.signup('someone6', 'default')
        self.signout()

        # create 60 items
        self.signin('someone1', 'default')
        self.create_multiple_items()
        self.create_multiple_items()
        self.create_multiple_items()
        self.create_multiple_items()
        self.create_multiple_items()
        self.create_multiple_items()
        self.create_multiple_items()
        self.create_multiple_items()
        self.create_multiple_items()
        self.create_multiple_items()
        self.signout()

        # add 60 comments on item1
        self.signin('someone2', 'default')
        comment = {'comment':'So Amazing'}
        for i in range(60):
            self.app.post('/comment/item/1', data=comment)

    # test helpers
    def signup(self, username, password, confirm=None, email=None, recommender=None):
        if confirm is None:
            confirm = password
        if email is None:
            email = username + '@muxucao.com'
        if recommender is None:
            recommender = username
        return self.app.post('/api/signup', data={
            'recommender': recommender,
            'username': username,
            'password': password,
            'confirm': confirm,
            'email': email
            }, follow_redirects=True)

    def signin(self, username, password):
        return self.app.post('/api/signin', data={
            'username': username,
            'password': password
            }, follow_redirects=True)

    def signout(self):
        return self.app.get('/signout', follow_redirects=True)

    def create_single_item(self):
        post = {'title': 'How to dress fluffy jumpers',
                'description': 'The difference between a fleece and a rich angora sweater is like',
                'original_price': 600.00,
                'current_price': 300.00,
                'brand': 'TakeIT',
                'size': 'Middle',
                'category': 'others',
                'photo': 'http://twitter.github.com/bootstrap/assets/img/bs-docs-twitter-github.png'
                }
        return self.app.post('/item/create', data=post)

    def create_multiple_items(self):
        post = {'title': 'Fashion Digital Daily',
                'description': '2012年由Fashion Digital Daily于Projective Space举办的Future of Fashion会议上，Merocrat, Bib+Tuck, Go Try It On, Stylitics, Little Black Bag这5家公司出席并且为我们带来了时尚界的新技术',
                'original_price': 500.00,
                'current_price': 400.00,
                'brand': 'Merocrat',
                'size': 'Small',
                'category': 'Suit',
                'photo': 'http://pic.fashiontrenddigest.com/digestPics/2013/1/6/159_11954_16_01S.jpg'
                }
        rv = self.app.post('/item/create', data=post)

        post = {'title': 'Merocrat',
                'description': 'Merocrat：作为全球时尚的一个专业部落，Merocrat旨在为雇佣时尚管理人才创造完全的透明度，创立者Viktoria Ruubel当初决定创立这样一个品牌就是为业界打造信任度和透明度。她希望能够时尚界的人士包括摄影师，设计师，模特，化妆师，发型师能和客户有直接的接触，通过这种直接的接触以建立信任并且创造更多的工作机会。为了全面杜绝自吹自擂，Merocrat会提供一个评分平台，让客户为和其工作过的业内专业人士打分，客户也可直接创建支付计划，无需经过经纪人这个第三方。',
                'original_price': 400.00,
                'current_price': 300.00,
                'brand': 'Merocrat',
                'size': 'Middle',
                'category': 'dress',
                'photo': 'http://pic.fashiontrenddigest.com/digestPics/2013/1/6/159_11954_16_02S.jpg'
                }
        rv = self.app.post('/item/create', data=post)

        post = {'title': 'Bit+Tuck',
                'description': 'Bib+Tuck：创立者Sari Azout和Sari Bibliowicz用“Wear your best bib and tucker”这句宣传语来表达每个人都应该穿着自己最棒的服装。这个平台只向女性开放，通过邀请的方式加入会员，会员可以在这个平台上交换服装，且不在平台上涉及金钱交易。会员可以上传自己想要出售的服装，并且给出一个能够接受的交易价格，然后通过Bib+Tuck币在平台上进行交易，如果Bib+Tuck币不足的话，会员可直接向Bib+Tuck进行购买。Bib+Tuck上每周会有指定衣柜，潮流走向等活动，展出的全部都是会员上传的单品，鼓励其他会员进行交换或者购买以达到再次使用的目的',
                'original_price': 700.00,
                'current_price': 570.00,
                'brand': 'Bit+Tuck',
                'size': 'Middle',
                'category': 'Suit',
                'photo': 'http://pic.fashiontrenddigest.com/digestPics/2013/1/6/159_11954_16_03S.jpg'
                }
        rv = self.app.post('/item/create', data=post)

        post = {'title': 'Go Try It On',
                'description': '创立者Amanda Hunter表示推出这个平台的目的是想要使用者和其朋友能够分享衣橱的服饰信息，并且互相探讨未来想要购买的单品，让这些使用者能够相互影响并且制定出属于自己的潮流走向。这个应用程序让使用者可以随时快速拍摄三张照片，通过上传服饰照片并在Facebook和Twitter上进行分享的方式找寻时尚意见',
                'original_price': 500.00,
                'current_price': 400.00,
                'brand': 'GoTryItOn',
                'size': 'Small',
                'category': 'dress',
                'photo': 'http://pic.fashiontrenddigest.com/digestPics/2013/1/6/159_11954_16_04S.jpg'
                }
        rv = self.app.post('/item/create', data=post)

        post = {'title': 'Stylitics',
                'description': '目前Stylitics向大众免费开放，让使用者可以上传服饰配饰的照片，并且将其摆放在一个虚拟的衣橱里。通过这个虚拟衣橱，使用者可以随意的搭配服装，定位想买的服饰，并且共享其他使用者的穿衣灵感。除此之外，使用者还可自己创建剪切本，邀请朋友进行评价或者反馈，以寻得更多的时尚建议。很多公司也开始使用这个平台来管理库存，分析消费者的消费行为等',
                'original_price': 500.00,
                'current_price': 400.00,
                'brand': 'Stylitics',
                'size': 'Large',
                'category': 'Shirt',
                'photo': 'http://pic.fashiontrenddigest.com/digestPics/2013/1/6/159_11954_16_05S.jpg'
                }
        rv = self.app.post('/item/create', data=post)

        post = {'title': 'Little Black Bag',
                'description': '创立者David Weissman表示已经有200多个品牌和Little Black Bag合作，宣传自己的产品。Little Black Bag是一个品牌宣传的很好途径，众多新兴品牌也通过这个平台吸引消费者的注意，Little Black Bag通过社交平台，电子商务，网络游戏等形式宣传品牌，以神秘产品出现在Black Bag的形式充分吸引消费者的兴趣。',
                'original_price': 500.00,
                'current_price': 400.00,
                'brand': 'LittleBlackBag',
                'size': 'Large',
                'category': 'bag',
                'photo': 'http://pic.fashiontrenddigest.com/digestPics/2013/1/6/159_11954_16_06S.jpg'
                }
        rv = self.app.post('/item/create', data=post)

    def test_web_setup(self):
        pass

if __name__ == '__main__':
    unittest.main()
