import requests
import json
import time

# http://web.archive.org/web/20161026011307/http://tofmal.ru/?xclasses
ALL_CLASSES = '''
2016а 2016б 2016в 2016г 2016ж 2016к
2015а 2015б 2015в 2015г 2015ж 2015к
2014а 2014б 2014в 2014ж 2014к
2013а 2013б 2013в 2013г 2013ж 2013к
2012а 2012б 2012в 2012ж 2012к
2011а 2011б
2010а 2010в 2010ж 2010к
2009а 2009б 2009в 2009ж 2009к
2008а 2008б 2008в 2008г 2008ж 2008к
2007а 2007б 2007в 2007ж 2007к
2006а 2006б 2006в 2006д 2006ж
2005б 2005в 2005г 2005д 2005ж 2005к
2004б 2004в 2004г 2004д 2004ж 2004к
2003а 2003б 2003в 2003г 2003е 2003ж
2002а 2002б 2002в 2002г 2002е 2002ж
2001а 2001б 2001в 2001г 2001е 2001ж
2000а 2000б 2000в 2000г 2000д 2000е
1999б 1999г 1999д 1999е 1999ж
1998б 1998г 1998д 1998е
1997б 1997г 1997д
1996а 1996б 1996в 1996г
1995а 1995б 1995в
1994а 1994б 1994в 1994г
1993а 1993б 1993в 1993г 1993д
1992а 1992б 1992в 1992г 1992д
1991а 1991б 1991в 1991г 1991д
1990а 1990б
'''

import logging
log = logging.getLogger(__name__)


def LoadClass(yearLetter):
    log.info(f'Getting class {yearLetter}')
    path = requests.utils.reqoute_url(yearLetter)
    return requests.get(f'http://tofmal.ru/?{path}').decode('cp1251')


def ParseHtml(html):
    for rawLine in html.replace('<div class=xpupil>', '\n').replace('</div></div>', '\n').split('\n'):
        if 'whereDidLern' in rawLine and 'Ф.И.О.' not in rawLine:
            line = rawLine.replace('<div class=name>', '').replace('</div><div class=medal>', '\t').replace('</div><div class=whereDidLern>', '\t').rstrip(' ')
            try:
                fio, flags, unversity = line.split('\t')
            except:
                log.exception('%r', [rawLine, line])
                raise
            newFlags = []
            for png, flag in [ ('gold', 'GOLD'), ('silver', 'SILVER'), ('best', 'BEST') ]:
                if '<img src=../img/{}.png>'.format(png) in flags:
                    newFlags.append(flag)
            yield {
                'FIO': fio,
                'Flags': newFlags,
                'University': unversity,
            }


def populate_parser(parser):
    parser.add_argument('--file', help='File to use', default='all.json')
    parser.add_argument('--mode', help='Mode', choices=['save', 'print'])
    parser.set_defaults(func=main)


def main(args):
    mode = args.mode
    filename = args.file
    if mode == 'save':
        if os.path.exists(filename):
            raise RuntimeError(f'File {filename!r} already exists, exiting')

        yearLetters = ALL_CLASSES.split()
        yearLetters.sort()

        result = {}
        for yearLetter in yearLetters:
            html = LoadClass(yearLetter)
            result[yearLetter] = list(ParseHtml(html))
            time.sleep(1)

        with open(filename, 'w') as f:
            f.write(json.dumps(
                result,
                indent=4,
                ensure_ascii=False,
                sort_keys=True,
            ).encode('utf-8'))

    elif mode == 'print':
        with open(filename) as f:
            result = json.load(f)
        for year, people in result.iteritems():
            for person in people:
                log.info('{}\t{}'.format(year, person['FIO']))
