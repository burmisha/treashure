#!/usr/bin/env python
# coding: utf-8

from __future__ import unicode_literals

import flask
import json
import logging
import random
import collections
import datetime

app = flask.Flask(__name__)
log = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

version = '0.2 от %s' % datetime.datetime.now()

class LogInfo(object):
    def __init__(self):
        self.Logger = logging.getLogger('LOG:' + __name__)
        self.LogItems = {}

    def Reset(self):
        self.LogItems = {}        

    def __call__(self, *args):
        self.Logger.info(*args)
        self.LogItems[str(datetime.datetime.now())] = args

    def GetItems(self):
        return self.LogItems

logInfo = LogInfo()

class SessionId(object):
    def __init__(self, userId, sessionId):
        self.UserId = userId
        self.SessionId = sessionId

class Events(object):
    def __init__(self):
        self.Items = [
            # (
            #     '23 мая',
            #     'Встреча в Воронеже',
            #     'https://www.facebook.com/choosetoteachrussia/posts/1990918467825161',
            # ),
            (
                '24 мая',
                'Завтрак в Жан-Жаке',
                'https://www.facebook.com/choosetoteachrussia/posts/1990802861170055',
            ),
            (
                '24 мая',
                'Встреча в Орле',
                'https://www.facebook.com/choosetoteachrussia/posts/1993750137541994',
            ),
            (
                '24–25 мая',
                'Встречи в Великом Новгороде',
                'https://vk.com/wall-88414131_3110'
            ),
            (
                '27 мая',
                'Очный тур в Москве',
                'https://www.facebook.com/choosetoteachrussia/photos/a.1552142791702733.1073741828.1549483155302030/1991323597784648',
            ),
            (
                '29 мая',
                'Анализ уроков, будет обсуждение в зуме, начало в 19:30',
                'https://zoom.us/j/929596305',
            ),
            (
                '4–22 июня',
                'Лагерь в Новорусаново и по Тамбовской области',
                'https://www.facebook.com/groups/221761485059584/permalink/255048321730900/',
            ),
            (
                '2 июня',
                'Очный тур в Воронеже',
                'https://www.facebook.com/choosetoteachrussia/photos/a.1552142791702733.1073741828.1549483155302030/1991323597784648',
            ),
            (
                '3 июня',
                '«Мысли вслух» в Москве (см. Фейсбук и рассылку 7)',
                None,
            ),
            (
                '10 июня',
                'Очный тур в Петербурге',
                'https://www.facebook.com/choosetoteachrussia/photos/a.1552142791702733.1073741828.1549483155302030/1991323597784648',
            ),
            (
                '10 июня',
                'Окончание приёма заявок',
                'https://www.facebook.com/choosetoteachrussia/videos/1990547747862233/',
            ),
            (
                '1–28 июля',
                'Летний институт — 1 сессия',
                'https://www.facebook.com/groups/221761485059584/permalink/250631605505905/',
            ),
            (
                '18–25 августа',
                'Летний институт — 2 сессия',
                None,
            ),
        ]

    def GetByIndex(self, index):
        return self.Items[index]


class SessionStorage(object):
    def __init__(self):
        self.Sessions = collections.defaultdict(dict)
        self.Events = Events()

    def GetSession(self, sessionId):
        return self.Sessions[sessionId.SessionId]

    def HasSession(self, sessionId):
        return sessionId.SessionId in self.Sessions

    def CreateSession(self, sessionId):
        self.Sessions[sessionId.SessionId] = {
            'last_index': -1,
        }

    def GetEvent(self, sessionId, delta=0):
        self.GetSession(sessionId)['last_index'] += delta
        lastIndex = self.GetSession(sessionId)['last_index']
        return self.Events.GetByIndex(lastIndex)


sessionStorage = SessionStorage()


def randomWord(groupName):
    words = {
        'hello': ['Привет', 'Фогель на связи', 'Мацкевич у аппарата', 'Кардаш слушает'],
        'ok': ['ок', 'угу', 'ага', 'отлично'],
        'end': ['Вот так вот. ', 'Ясно-понятно? ', ''],
        'wat': ['Непонятно', 'Чего говоришь?', 'Может тебе к куратору с этим?'],
        'coming': ['Будет', 'Пройдёт'],
    }[groupName]
    return random.choice(words)


class Command(object):
    def __init__(self, text):
        self.Text = text.lower().strip()

    def Has(self, *words):
        return any(word.lower() in self.Text for word in words)


@app.route('/', methods=['GET', 'POST'])
def alice():
    if flask.request.method == 'GET':
        return 'Привет, это версия %s' % version

    requestData = flask.request.json
    logInfo('Request: %r', requestData)

    try:
        response = handleDialog(requestData)
    except Exception as e:
        log.exception('Got error!')
        error = {
            'date': str(datetime.datetime.now()),
            'str': str(e),
            'repr': repr(e),
            'class': type(e),
        }
        response = {
            'text': 'У меня какая-то ошибка, черкани бурмише. Пока!',
            'buttons': [{
                'text': 'Телеграм @burmisha',
                'link': 'https://t.me/burmisha',
                'hide': False,
            }],
            'error': error,
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

    logInfo('Response: %r', fullResponse)

    return json.dumps(
        fullResponse,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )

@app.route('/debug', methods=['GET'])
def debug():
    return json.dumps(
        {
            'logs': logInfo.GetItems(),
            'sessions': sessionStorage.Sessions,
        },
        ensure_ascii=False,
        indent=4,
        sort_keys=True,
    )

@app.route('/reset', methods=['GET'])
def reset():
    logInfo.Reset()
    return 'ok'

def handleDialog(request):
    session = request['session']
    command = Command(request['request']['command'])

    sessionId = SessionId(session['user_id'], session['session_id'])

    buttons = []
    result = {
        'end_session': False,
    }
    if session['new']:
        sessionStorage.CreateSession(sessionId)

    if command.Has('привет'):
        text = '%s! Я расскажу тебе о матрикуляции, погружении, наборе и летнем институте.' % randomWord('hello')
    elif command.Has('что', 'ещё', 'а') and command.Has('дальше', 'потом'):
        eventDate, eventText, _ = sessionStorage.GetEvent(sessionId, delta=1)
        text = '%s %s %s' % (eventDate, randomWord('coming').lower(), eventText)
    elif command.Has('назад', 'перед'):
        eventDate, eventText, _ = sessionStorage.GetEvent(sessionId, delta=-1)
        text = 'Говорю же, %s %s %s' % (eventDate, randomWord('coming').lower(), eventText)
    elif command.Has('посмотреть пост'):
        text = 'Надеюсь, это сняло твой вопрос'
    elif command.Has('ссылк', 'пруф'):
        _, _, link = sessionStorage.GetEvent(sessionId)
        if 'vk.com' in link:
            linkName = 'во вконтакте'
        elif 'facebook.com' in link:
            linkName = 'на фейсбук'
        else:
            linkName = ''
        text = 'Лови ссылку %s' % linkName
        buttons.append({
            'title': 'Посмотреть пост',
            'url': link,
            'hide': True
        })
    elif command.Has('всё', 'хватит', 'пока'):
        text = '%s, пока' % randomWord('ok')
        result['end_session'] = True
    elif command.Has('ок', 'хорошо', 'спасибо', 'ясно'):
        text = randomWord('ok')
    else:
        text = randomWord('wat')

    result['text'] = text
    if buttons:
        result['buttons'] = buttons
    return result


logInfo('Version: %s, %s', __file__, version)


def run_tests():
    sid = SessionId('aaa', 'bbb')
    sessionStorage.CreateSession(sid)
    print sessionStorage.GetEvent(sid)
    print sessionStorage.GetEvent(sid)
    command = Command('Что ')
    assert command.Has('ч')
    assert command.Has('т')
    print handleDialog({
        'session': {'user_id': 'aaa', 'session_id': 'bbb', 'new': True},
        'request': {'command': 'привет'},
    })
    sameSession = lambda text: json.dumps(handleDialog({
        'session': {'user_id': 'aaa', 'session_id': 'bbb', 'new': False},
        'request': {'command': text},
    }), ensure_ascii=False)
    print sameSession('Что дальше?')
    print sameSession('Что дальше?')
    print sameSession('Что дальше?')
    print sameSession('Что дальше?')
    print sessionStorage.Sessions
    assert 'buttons' in sameSession('Ссылку?')
    print sameSession('Посмотреть пост')
    print sessionStorage.Sessions

# run_tests()
