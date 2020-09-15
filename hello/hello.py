#!/usr/bin/env python
from flask import Flask
app = Flask(__name__)

@app.route('/')
def hello_world():
    return 'Hello, World!'

@app.route('/user/<string:username>')
def user(username, methods=['GET']):
    return 'Hello, {}!'.format(username)

# https://pyliaorachel.github.io/blog/tech/system/2017/07/07/flask-app-with-gunicorn-on-nginx-server-upon-aws-ec2-linux.html

if __name__ == '__main__':
    app.run()
