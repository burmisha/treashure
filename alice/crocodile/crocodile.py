#!/usr/bin/env python
# coding: utf-8

from __future__ import unicode_literals

import flask
import json
import logging
import random

app = flask.Flask(__name__)
log = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

version = '1.2'

class SessionStorage(object):
    def __init__(self):
        self.Sessions = {}

    def AddUser(self, userId):
        self.Sessions[userId] = {
            'availableWords': [
                'пустота',
                'антихайп',
            ]
        }

    def GetWord(self, userId):
        session = self.Sessions[userId]

        words = session['availableWords']
        if words:
            index = random.randint(0, len(words) - 1)
            word = words[index]
            del words[index]

            return word
        else:
            return None


sessionStorage = SessionStorage()

@app.route('/', methods=['GET', 'POST'])
def alice():
    if flask.request.method == 'GET':
        return 'Привет, это версия %s' % version

    requestData = flask.request.json
    log.info('Request: %r', requestData)

    try:
        response = handleDialog(requestData)
    except:
        log.exception('Got error!')
        response = {
            'text': 'У меня какая-то ошибка, посмотри в логи. Пока!',
            'end_session': True,
        }

    fullResponse = {
        'version': requestData['version'],
        'session': requestData['session'],
        'response': {
            'end_session': False,  # по умолчанию продолжаем
        },
    }
    fullResponse['response'].update(response)

    log.info('Response: %r', fullResponse)

    return json.dumps(
        fullResponse,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )


def handleDialog(request):
    userId = request['session']['user_id']

    if request['session']['new']:
        sessionStorage.AddUser(userId)
        text = 'Привет! Твоё слово в подсказке ниже, никому её не показывай!'
    else:
        text = 'Новое слово в подсказке ниже, никому её не показывай!'

    word = sessionStorage.GetWord(userId)
    if word:
        return {
            'text': text,
            'buttons': [
                {
                    'title': word,
                    'hide': True,
                },
            ],
            'end_session': False,
        }
    else:
        return {
            'text': 'Извини, у меня нет для тебя новых слов. Пока!',
            'end_session': True,
        }

log.info('Version: %s', version)
