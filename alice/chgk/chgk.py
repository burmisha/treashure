#!/usr/bin/env python
# coding: utf-8

from __future__ import unicode_literals

import flask
import json
import logging
import random
import collections
import time

app = flask.Flask(__name__)
log = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)


version = '0.32'


class SessionId(object):
    def __init__(self, userId, sessionId):
        self.UserId = userId
        self.SessionId = sessionId

class SessionStorage(object):
    def __init__(self):
        self.Sessions = {}
        self.Questions = {
            1: {
                'text': 'Столица Португалии?',
                'answer': 'Лиссабон',
            },
            2: {
                'text': 'Год основания Москвы?',
                'answer': '1147',
            },
            3: {
                'text': '2 в десятой степени?',
                'answer': '1024',
            },
            4: {
                'text': 'Висит груша, нельзя скушать.',
                'answer': 'Лампочка',
            }
        }

    def Now(self):
        return int(time.time())

    def GetStatus(self, sessionId):
        return self.GetSession(sessionId)['status']

    def GetSession(self, sessionId):
        return self.Sessions[sessionId.SessionId]

    def CreateSession(self, sessionId):
        self.Sessions[sessionId.SessionId] = {
            'latest_question_id': None,
            'latest_question_ts': None,
            'used_questions': [],
            'count': {
                'alice': 0,
                'player': 0,
            },
            'status': None,
        }

    def CheckAnswer(self, sessionId, command):
        session = self.GetSession(sessionId)
        correctAnswer = self.Questions[session['latest_question_id']]['answer']
        isCorrect = correctAnswer.lower() == command.lower()
        if isCorrect:
            session['count']['player'] += 1
        else:
            session['count']['alice'] += 1
        tooLong = (self.Now() - session['latest_question_ts']) >= 65
        session['status'] = None
        return isCorrect, correctAnswer, tooLong

    def GetQuestion(self, sessionId):
        session = self.GetSession(sessionId)
        questionIds = sorted(set(self.Questions.keys()) - set(session['used_questions']))
        questionId = random.choice(questionIds)
        session['latest_question_id'] = questionId
        session['latest_question_ts'] = self.Now()
        session['used_questions'].append(questionId)
        session['status'] = 'waiting_answer'
        return self.Questions[questionId]['text']

    def GetResults(self, sessionId):
        return self.GetSession(sessionId)['count']


sessionStorage = SessionStorage()



def commandHas(command, words):
    for word in words:
        if word in command:
            return True
    return False


@app.route('/', methods=['GET', 'POST'])
def alice():
    if flask.request.method == 'GET':
        return 'Привет, это версия %s' % version

    requestData = flask.request.json
    log.info('Request: %r', requestData)

    try:
        response = handleDialog(requestData)
    except Exception as e:
        log.exception('Got error!')
        response = {
            'text': 'У меня какая-то ошибка, посмотри в логи. Пока!',
            'error': {
                'str': str(e),
                'repr': repr(e),
                'class': type(e),
            },
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
    session = request['session']
    command = request['request']['command'].lower().strip()

    sessionId = SessionId(session['user_id'], session['session_id'])

    if session['new']:
        sessionStorage.CreateSession(sessionId)
        text = 'Привет! Мы начинаем игру «Что-где-когда»: Алиса против Знатоков. У вас будет по минуте на каждый вопрос. За временем следите сами. Готовы?'
    else:
        status = sessionStorage.GetStatus(sessionId)
        if status == 'waiting_answer':
            isCorrect, correctAnswer, tooLong = sessionStorage.CheckAnswer(sessionId, command)

            if tooLong:
                text = 'Что-то вы долго думали. Пожалуйста, соблюдайте правила клуба. '
            else:
                text = ''

            if isCorrect:
                text += 'Верно!'
            else:
                text += 'Господин Друзь, вы ходили в 7 классе на рисование? Конечно же, верный ответ: %s. Очко уходит Алисе.' % correctAnswer            
        else:
            if commandHas(command, ['поехали', 'да']):
                text = 'Внимание, вопрос. %s' % sessionStorage.GetQuestion(sessionId)
            elif commandHas(command, ['результат', 'счёт']):
                count = sessionStorage.GetResults(sessionId)
                text = 'Текущие результаты: Алиса — %d очков, Знатоки — %d.' % (count['alice'], count['player'])            
            else:
                text = 'Непонятно'

    result = {
        'text': text,
        'end_session': False,
    }
    return result


def run_tests():
    log.info('Version: %s, %s', __file__, version)
    ss = SessionStorage()
    sid = SessionId('aaa', 'bbb')
    ss.CreateSession(sid)
    print ss.GetQuestion(sid)
    print ss.CheckAnswer(sid, '1024')
    print ss.GetResults(sid)

# run_tests()
