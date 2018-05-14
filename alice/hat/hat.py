#!/usr/bin/env python
# coding: utf-8

from __future__ import unicode_literals

import flask
import json
import logging
import random
import collections

app = flask.Flask(__name__)
log = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)


version = '0.2'


class SessionId(object):
    def __init__(self, userId, sessionId):
        self.UserId = userId
        self.SessionId = sessionId

class SessionStorage(object):
    def __init__(self):
        self.Sessions = {}

    def GetSession(self, sessionId):
        return self.Sessions[sessionId.SessionId]

    def CreateSession(self, sessionId):
        self.Sessions[sessionId.SessionId] = {
            'status': 'add_teams',
            'teams': collections.OrderedDict(),
            'words': [
                'Муравей',
                'Халк',
                'Пантера',
                'Старк',
                'Тор',
                'Капитан',
            ],
            'latest_words': [],
        }

    def GetStatus(self, sessionId):
        return self.GetSession(sessionId)['status']

    def SetStatus(self, sessionId, status):
        self.GetSession(sessionId)['status'] = status

    def AddTeam(self, sessionId, teamName):
        self.GetSession(sessionId)['teams'][teamName] = {
            'results': 0,
        }

    def GetTeamsCount(self, sessionId):
        return len(self.GetSession(sessionId)['teams'])

    def AddResult(self, sessionId, command):
        session = self.GetSession(sessionId)
        count = None
        resultTeam = None
        for teamName, team in session['teams'].iteritems():
            if teamName in command:
                resultTeam = teamName
                count = int(getNumber(command))
                team['results'] += count

        readyWords = set(session['latest_words'][:count])
        session['words'] = [word for word in session['words'] if word not in readyWords]
        return resultTeam, count

    def GetResults(self, sessionId):
        for teamName, team in self.GetSession(sessionId)['teams'].iteritems():
            yield teamName, team['results']

    def GenerateWords(self, sessionId):
        session = self.GetSession(sessionId)
        wordsCopy = list(session['words'])
        random.shuffle(wordsCopy)
        wordsCount = 4
        del wordsCopy[wordsCount:]
        session['latest_words'] = wordsCopy
        return wordsCopy


sessionStorage = SessionStorage()


def randomWord(groupName):
    words = {
        'points': ['очков', 'слов'],
        'hooray': ['угу', 'ага', 'отлично'],
        'wat': ['Вот так вот. ', 'Ясно-понятно? ', '' ],
        'what': ['Непонятно', 'Чего говоришь?'],
    }[groupName]
    return random.choice(words)


def commandHas(command, words):
    for word in words:
        if word in command:
            return True
    return False


def getNumber(command):
    for word in command.split():
        candidate = {
            'одного': 0,
            'одно': 1,
            'один': 1,
            'два': 2,
            'три': 3,
            '0': 0,
            '1': 1,
            '2': 2,
            '3': 3,
            '4': 4,
        }.get(word)
        if candidate is not None:
            return candidate
    return None


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

    buttons = []
    if session['new']:
        sessionStorage.CreateSession(sessionId)
        text = 'Привет! Скажите, пожалуйста, названия ваших команд по одному слову на каждую. Как закончишь — скажите: «Всё!»'
    else:
        status = sessionStorage.GetStatus(sessionId)
        if status == 'add_teams':
            if command == 'всё':
                sessionStorage.SetStatus(sessionId, 'play')
                text = '''
Ура, начинаем играть.
У нас %d команды. Время засекайте сами.
Будете готовы — скажите: «Поехали», персонажи будут в подсказках. Объясняйте их строго по очереди.
Не забывайте меня отключать, пока отгадываете, а то и я буду участвовать.
''' % (
    sessionStorage.GetTeamsCount(sessionId),
)
            else:
                text = '%s, %s, запомнила' % (randomWord('hooray'), command)
                sessionStorage.AddTeam(sessionId, command)
        elif status == 'play':
            if commandHas(command, ['поехали']):
                text = 'Лови!'
                for word in sessionStorage.GenerateWords(sessionId):
                    buttons.append({
                        'title': word,
                        'hide': True,
                    })
            elif 'команда' in command and commandHas(command, ['отгадала', 'получила']):
                teamName, count = sessionStorage.AddResult(sessionId, command)
                text = '%s, добавляю команде %s %d очков' % (randomWord('hooray'), teamName, count)
            elif commandHas(command, ['результат', 'счёт', 'таблиц']):
                text = 'Текущие результаты. '
                for teamName, count in sessionStorage.GetResults(sessionId):
                    text += '%s: %d %s. ' % (teamName, count, randomWord('points'))
                text += randomWord('wat')
            else:
                text = randomWord('what')
        else:
            text = 'Что-то непонятное творится'

    result = {
        'text': text,
        'end_session': False,
    }
    if buttons:
        result['buttons'] = buttons
    return result


log.info('Version: %s, %s', __file__, version)


def run_tests():
    assert getNumber('два или что там') == 2
    assert len(randomWord('hooray')) in [3, 7]
    ss = SessionStorage()
    sid = SessionId('aaa', 'bbb')
    ss.CreateSession(sid)
    ss.AddTeam(sid, 'букля')
    assert ss.GetTeamsCount(sid) == 1
    print ss.GenerateWords(sid)
    ss.AddResult(sid, 'букля получает три')
    print list(ss.GetResults(sid))

run_tests()
