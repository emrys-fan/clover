import json
import requests
from urlparse import urljoin

if __name__ == '__main__':
    data = {'recommender': 'somebody',
            'username': 'somebody',
            'password': 'hello',
            'confirm': 'hello',
            'email': 'emrys@gmail.com'}
    base_url = 'http://ld.youpinapp.com:5000/'
    rv = requests.post(urljoin(base_url, '/api/signup'), data=data)
    jsondata = json.loads(rv.text)
    token = jsondata['user']['token']

    headers = {'X-Clover-Access': token}
    rv = requests.get(urljoin(base_url, '/api/profile/update'), headers=headers)
    jsondata = json.loads(rv.text)
    print jsondata
    assert jsondata['username'] == 'somebody'

