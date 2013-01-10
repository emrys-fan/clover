#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
import json
import app

ajax_headers = {'X-Requested-With': 'XMLHttpRequest'}

class AppTest(unittest.TestCase):

    def setUp(self):
        self.app = app.app.test_client()
        app.app.redis.flushdb()

    def signup(self, username, password, confirm=None, email=None):
        if confirm is None:
            confirm = password
        if email is None:
            email = username + '@muxucao.com'
        return self.app.post('/signup', data={
            #'csrf_token': '20130108023135##279022d3750abd8e59110916a610fa122a10a0c1',
            'username': username,
            'password': password,
            'confirm': confirm,
            'email': email
            }, follow_redirects=True)

    def signin(self, username, password):
        return self.app.post('/signin', data={
            'username': username,
            'password': password
            }, follow_redirects=True)

    def signout(self):
        return self.app.get('/signout', follow_redirects=True)

    def signup_and_signin(self, username, password):
        self.signup(username, password)
        return self.signin(username, password)

    def signin_and_signout(self, username, password):
        self.signup(username, password)
        self.signin(username, password)
        return self.signout()

    def test_signup(self):
        rv = self.signup('emrys', 'hello')
        assert '注册成功' in rv.data
        rv = self.signup('emrys', 'hello')
        assert '该用户名已注册' in rv.data
        rv = self.signup('', 'hello')
        assert '缺少用户名' in rv.data
        rv = self.signup('me', 'hello')
        assert 'Field must be between 3 and 20 characters long' in rv.data

    def test_signin(self):
        rv = self.signup('emrys', 'hello')
        assert '注册成功' in rv.data
        rv = self.signout()
        assert '已退出' in rv.data
        rv = self.signin('emrys', 'hello')
        assert '成功登录' in rv.data
        rv = self.signout()

        rv = self.signin('emrys', '')
        assert 'This field is required' in rv.data
        rv = self.signin('', 'hello')
        assert 'This field is required' in rv.data
        rv = self.signin('emrys', 'default')
        assert '用户名或密码错误' in rv.data
        rv = self.signin('emily', 'hello')
        assert '用户名或密码错误' in rv.data

    def test_signin_signout(self):
        rv = self.signin_and_signout('emrys', 'hello')
        assert '已退出' in rv.data

    def test_follow_action(self):
        self.signup('emrys', 'hello')
        self.signout()
        self.signup('google', 'hello')
        self.signout()
        self.signup('facebook', 'hello')
        self.signout()
        self.signup('someone1', 'hello')
        self.signout()
        self.signup('someone2', 'hello')
        self.signout()
        self.signup('someone3', 'hello')
        self.signout()

        rv = self.signup('myself', 'hello')
        # follow emrys
        rv = self.app.get('/follow/1')
        ret = json.loads(rv.data)
        assert ret['message'] == '关注成功'
        # try follow the same person again
        rv = self.app.get('/follow/1')
        ret = json.loads(rv.data)
        assert ret['message'] == '已关注'
        # unfollow emrys
        rv = self.app.get('/unfollow/1')
        ret = json.loads(rv.data)
        assert '取消关注成功' == ret['message']
        rv = self.app.get('/unfollow/1')
        ret = json.loads(rv.data)
        assert '尚未关注' == ret['message']
        # follow or unfollow somebody does not exist will get a error
        rv = self.app.get('/follow/100')
        assert rv.status_code == 404
        rv = self.app.get('/unfollow/100')
        assert rv.status_code == 404

        # following 6 buddies
        rv = self.app.get('/follow/1')
        rv = self.app.get('/follow/2')
        rv = self.app.get('/follow/3')
        rv = self.app.get('/follow/4')
        rv = self.app.get('/follow/5')
        rv = self.app.get('/follow/6')
        # check following lists
        rv = self.app.get('/following/7', headers=ajax_headers)
        ret = json.loads(rv.data)
        assert len(ret['followings']) == 6
        # logout myself
        self.signout()

        #
        self.signin('google', 'hello')
        # now google is following emrys
        rv = self.app.get('/follow/1')
        self.signout()

        self.signin('facebook', 'hello')
        # now facebook is following emrys
        rv = self.app.get('/follow/1')
        self.signout()

        # check emrys's followers
        self.signin('emrys', 'hello')
        rv = self.app.get('/follower/1', headers=ajax_headers)
        ret = json.loads(rv.data)
        assert len(ret['followers']) == 3

        # listing followers of nonexist user get empty data instead of error
        rv = self.app.get('/follower/100', headers=ajax_headers)
        assert rv.status_code == 200
        ret = json.loads(rv.data)
        assert len(ret['followers']) == 0


    # item test helper
    def create_item(self):
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

    def create_several_items(self):
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
        assert 'success' in rv.data

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
        assert 'success' in rv.data

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
        assert 'success' in rv.data

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
        assert 'success' in rv.data

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
        assert 'success' in rv.data

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
        assert 'success' in rv.data

    # item test functions
    def test_create_item(self):
        rv = self.signup('emrys', 'hello')
        assert '注册成功' in rv.data
        rv = self.create_item()
        ret = json.loads(rv.data)
        assert ret['message'] == 'success'

    def test_show_item(self):
        self.signup('emrys', 'hello')
        # create item
        rv = self.create_item()
        assert 'success' in rv.data
        ret = json.loads(rv.data)
        postid = ret['postid']
        # show item
        rv = self.app.get('/item/show/%s' % postid, headers=ajax_headers)
        ret = json.loads(rv.data)
        assert postid == int(ret['request_item']['postid'])

    def test_addcomment(self):
        # signup emrys
        rv = self.signup('emrys', 'hello')
        assert '注册成功' in rv.data

        # emrys create a item, then logout
        rv = self.create_item()
        assert 'success' in rv.data

        ret = json.loads(rv.data)
        postid = ret['postid']

        # signout emrys
        rv = self.app.get('/signout', follow_redirects=True)
        assert '已退出' in rv.data

        # signup google
        rv = self.signup('google', 'hello')
        assert '注册成功' in rv.data
        # google add a comment on emrys's post
        comment = {'comment':'So Amazing'}
        rv = self.app.post('/comment/item/%s' % postid, data=comment)
        ret = json.loads(rv.data)
        assert postid == int(ret['comment']['pid'])

    def test_show_item_comment(self):
        # signup emrys
        rv = self.signup('emrys', 'hello')
        assert '注册成功' in rv.data

        # emrys create a item, then logout
        rv = self.create_item()
        assert 'success' in rv.data

        ret = json.loads(rv.data)
        postid = ret['postid']

        # signout emrys
        rv = self.app.get('/signout', follow_redirects=True)
        assert '已退出' in rv.data

        # signup google
        rv = self.signup('google', 'hello')
        assert '注册成功' in rv.data
        # google add several comments on emrys's post
        # first comment
        comment = {'comment': 'So Amazing'}
        rv = self.app.post('/comment/item/%s' % postid, data=comment)
        ret = json.loads(rv.data)
        assert postid == int(ret['comment']['pid'])
        # second comment
        rv = self.app.post('/comment/item/%s' % postid, data=comment)
        ret = json.loads(rv.data)
        assert postid == int(ret['comment']['pid'])

        # show all item comment
        rv = self.app.get('/item/comment/%s' % postid)
        ret = json.loads(rv.data)
        assert len(ret['comments']) == 2

    def test_like_action(self):
        # create several items
        self.signup('emrys', 'hello')
        self.create_several_items()
        self.signout()

        self.signup('google', 'hello')
        rv = self.app.get('/like/1')
        ret = json.loads(rv.data)
        assert ret['liked'] == True
        # like a nonexists item will get a error
        rv = self.app.get('/like/100')
        assert rv.status_code == 404

        rv = self.app.get('/like/1')
        rv = self.app.get('/like/2')
        rv = self.app.get('/like/3')
        rv = self.app.get('/like/4')
        rv = self.app.get('/like/5')
        rv = self.app.get('/likes', headers=ajax_headers)
        ret = json.loads(rv.data)
        assert len(ret['likes']) == 5

        rv = self.app.get('/unlike/4')
        ret = json.loads(rv.data)
        assert ret['liked'] == False
        rv = self.app.get('/likes', headers=ajax_headers)
        ret = json.loads(rv.data)
        assert len(ret['likes']) == 4

    # timeline test stuff
    def test_timeline(self):
        self.signup('emrys', 'hello')
        self.create_several_items()
        self.create_several_items()
        self.create_several_items()
        self.create_several_items()
        self.create_several_items()
        self.create_several_items()
        self.signout()

        #get public timeline
        self.signup('google', 'hello')
        rv = self.app.get('/public', headers=ajax_headers)
        ret = json.loads(rv.data)
        assert len(ret['timeline']) == 21
        # show closet
        rv = self.app.get('/closet/1', headers=ajax_headers)
        ret = json.loads(rv.data)
        assert len(ret['timeline']) == 21
        rv = self.app.get('/closet/1?since_id=%s&page=%s'%(ret['since_id'], ret['page']), headers=ajax_headers)
        ret_pre = json.loads(rv.data)
        # create more items
        self.create_several_items()

        rv = self.app.get('/closet/1?since_id=%s&page=%s'%(ret['since_id'], ret['page']), headers=ajax_headers)
        ret_now = json.loads(rv.data)
        assert ret_pre == ret_now

    def test_feed(self):
        self.signup('emrys', 'hello')
        self.create_several_items()
        self.signout()
        self.signup('google', 'hello')
        self.create_several_items()
        self.create_several_items()
        self.signout()
        self.signup('facebook', 'hello')

        # follow emrys
        rv = self.app.get('/follow/1')
        assert 'followed' in rv.data
        # check feed count
        rv = self.app.get('/feed', headers=ajax_headers)
        ret = json.loads(rv.data)
        assert len(ret['timeline']) == 6
        # now following google
        rv = self.app.get('/follow/2')
        assert 'followed' in rv.data
        # check feed count
        rv = self.app.get('/feed', headers=ajax_headers)
        ret = json.loads(rv.data)
        assert len(ret['timeline']) == 18
        # unfollow emrys
        rv = self.app.get('/unfollow/1')
        assert 'false' in rv.data
        # check feed count
        rv = self.app.get('/feed', headers=ajax_headers)
        ret = json.loads(rv.data)
        assert len(ret['timeline']) == 12
        # unfollow google
        rv = self.app.get('/unfollow/2')
        assert 'false' in rv.data
        # check feed count
        rv = self.app.get('/feed', headers=ajax_headers)
        ret = json.loads(rv.data)
        assert len(ret['timeline']) == 0

        # try to follow yourself will get a 404 error
        rv = self.app.get('/follow/3')
        assert rv.status_code == 404

    def test_show_user_comment(self):
        self.signup('emrys', 'hello')
        self.create_several_items()
        self.signout()

        self.signup('google', 'hello')
        comment = {'comment':'So Amazing'}
        rv = self.app.post('/comment/item/1', data=comment)
        ret = json.loads(rv.data)
        assert 1 == int(ret['comment']['pid'])
        rv = self.app.post('/comment/item/2', data=comment)
        ret = json.loads(rv.data)
        assert 2 == int(ret['comment']['pid'])
        rv = self.app.post('/comment/item/3', data=comment)
        ret = json.loads(rv.data)
        assert 3 == int(ret['comment']['pid'])

        # listing user comments
        rv = self.app.get('/comments', headers=ajax_headers)
        ret = json.loads(rv.data)
        assert len(ret['timeline']) == 3

    def test_explore(self):
        self.signup('emrys', 'hello')
        self.create_several_items()
        self.signout()
        self.signup('google', 'hello')
        self.create_several_items()
        self.signout()

        self.signup('myself', 'hello')
        # explore category
        rv = self.app.get('/explore/category/Suit', headers=ajax_headers)
        ret = json.loads(rv.data)
        assert len(ret['timeline']) == 4
        rv = self.app.get('/explore/category/Suit?size=Middle', headers=ajax_headers)
        ret = json.loads(rv.data)
        assert len(ret['timeline']) == 2

        # explore brand
        rv = self.app.get('/explore/brand/Merocrat', headers=ajax_headers)
        ret = json.loads(rv.data)
        assert len(ret['timeline']) == 4
        rv = self.app.get('/explore/brand/Merocrat?category=Suit', headers=ajax_headers)
        ret = json.loads(rv.data)
        assert len(ret['timeline']) == 2


if __name__ == '__main__':
    unittest.main()
