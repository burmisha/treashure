#!/usr/bin/env python3

import json
import collections
import os
from dataclasses import dataclass
import re


FILENAME = os.path.join(os.environ['HOME'], 'Downloads', 'Telegram Desktop', 'ChatExport_2023-09-21', 'result.json')
LINK_TEMPLATE = 'https://t.me/relocationarmenia/{message_id}'

@dataclass
class Message:
    person_name: str
    date: str
    text: str
    link: str


@dataclass
class Flat:
    area: int
    rooms: int
    price: int
    location: str
    message: Message

    def __str__(self):
        return (
            f'{self.rooms:1d}к - {self.area:3d} м² - ${self.price:4d}: '
            f'{self.location:30}   {self.message.link}   {self.message.date}'
        )


# https://stackoverflow.com/questions/33404752/removing-emojis-from-a-string-in-python
EMOJI_RE = re.compile('['
    '\U0001F600-\U0001F64F'  # emoticons
    '\U0001F300-\U0001F5FF'  # symbols & pictographs
    '\U0001F680-\U0001F6FF'  # transport & map symbols
    '\U0001F1E0-\U0001F1FF'  # flags (iOS)
    '\U00002500-\U00002BEF'  # chinese char
    '\U00002702-\U000027B0'
    '\U000024C2-\U0001F251'
    '\U0001f926-\U0001f937'
    '\U00010000-\U0010ffff'
    '\u2640-\u2642' 
    '\u2600-\u2B55'
    '\u200d'
    '\u23cf'
    '\u23e9'
    '\u231a'
    '\ufe0f'  # dingbats
    '\u3030'
']+', re.UNICODE)


def remove_emojis(line):
    return re.sub(EMOJI_RE, '', line)


def get_rooms(line: str):
    if re.match(r'.*\b1\-?[хx]? ?ком.*', line):
        return 1
    elif re.match(r'.*\b2\-?[хx]? ?ком.*', line):
        return 2
    elif re.match(r'.*\b3\-?[хx]? ?ком.*', line):
        return 3
    elif re.match(r'.*\b4\-?[хx]? ?ком.*', line):
        return 4

    return None


def get_price(line: str):
    is_price = False
    rate = 1
    if( '$' in line) or ('USD' in line):
        is_price = True
    elif ('Դ' in line) or ('AMD' in line):
        is_price = True
        rate = 386.35

    if not is_price:
        return None

    digits = ''.join([a for a in line if a.isdigit()])
    if not digits:
        return None

    return int(int(digits) / rate)


def get_area(line: str):
    line = line.lower()
    is_area = False
    rate = 1
    if re.match(r'.+\bкв?\. ?м\.?.+', line):
        is_area = True

    if not is_area:
        return None

    area_str = ''.join([a for a in line if a.isdigit()])
    if not area_str:
        return None

    area = int(area_str)
    if 20 < area < 1000:
        return area

    return None


def get_location(line: str):
    result = None
    if 'осмотреть адрес на карте' in line:
        return None
    if re.match(r'.*[Аа]дресу?\b(.+)', line):
        result = re.sub(r'.*[Аа]дресу?\s+(.+)', '\1', line)

    elif re.match(r'.*[Уу]л\..*', line):
        result = line

    elif re.match(r'.*[Уу]лица .*', line):
        result = line

    if not result:
        return None

    result = remove_emojis(line).strip()
    result = re.sub(r'.дрес:?\s+', '', result)
    result = re.sub(r'\b[Уу]л\.', 'улица ', result)
    result = re.sub(r'\bУлица\b', 'улица ', result)
    result = re.sub(r'(по )?\b[Аа]дресу?', '', result)
    result = re.sub(r'\s+', ' ', result)
    result = re.sub(r'\. Квартира .+', '', result)
    result = re.sub(r'(в )?Ереване?\b', '', result)

    # print(result)
    if len(result) <= 3:
        return None

    return result.strip().strip('.').strip(',')


assert get_rooms('🏘 Сдается 3х комнатная Пентхаус 🧡') == 3
assert get_rooms('сдается 3х комнатная квартира') == 3
assert get_rooms('🏨Сдается 2-комнатная квартира местоположение👇') == 2
assert get_price('💵  Цена 3000 $ на месяц') == 3000
assert get_area('300 к.м.') == 300
assert get_location('🔸 1-я улица Мгера Мкртчян') == '1-я улица Мгера Мкртчян'
assert get_location('Улица Арама, 48') == 'улица Арама, 48'
assert get_location('Адрес ⤵️') is None
assert get_location('по адресу улица Ханджяна 33') == 'улица Ханджяна 33'
assert get_location('Сдаётся 2-комнатная квартира в новостройке, расположенная по адресу пр. М. Баграмян 59, Малый Центр, Ереван.')


def skip_message(message: Message) -> bool:
    if 'Генеральная уборка' in message.text:
        return True

    return False


def message_to_flat(message: Message) -> Flat:
    # if message.link != 'https://t.me/relocationarmenia/398267':
    #     return None

    if skip_message(message):
        return None

    area = None
    rooms = None
    price = None
    location = None
    for line in message.text.split('\n'):
        if not line.strip():
            continue
        candidate_rooms = get_rooms(line)
        if candidate_rooms:
            if rooms and candidate_rooms != rooms:
                raise RuntimeError(f'Already has rooms: {rooms} -> {candidate_rooms}')
            rooms = candidate_rooms

        candidate_price = get_price(line)
        if candidate_price:
            if price:
                # raise RuntimeError(f'Already has price: {price} -> {candidate_price}')
                price = min(price, candidate_price)
            else:
                price = candidate_price

        candidate_area = get_area(line)
        if candidate_area:
            if area:
                raise RuntimeError(f'Already has area: {area} -> {candidate_area}')
            area = candidate_area

        candidate_location = get_location(line)
        if candidate_location:
            # if location:
            #     raise RuntimeError(f'Already has location: {location} -> {candidate_location}')
            location = candidate_location


    if rooms and price and area and location:
        return Flat(
            rooms=rooms, 
            price=price, 
            area=area, 
            location=location,
            message=message,
        )
    else:
        print([bool(rooms), bool(price), bool(area), bool(location), message.link])

    # print(f'rooms: {rooms}, price: {price}, area: {area}')
    return None



def parse_raw_message(raw_message):
    try:
        user_id = raw_message.get('from_id') or raw_message['actor_id']

        name = raw_message.get('from')
        if not name:
            name = raw_message.get('actor')
        if not name:
            return None

        if raw_message.get('forwarded_from'):
            return None

        if raw_message.get('action') == 'join_group_by_link':
            return None

        # missing_file_message = '(File not included. Change data exporting settings to download.)'
        # if raw_message.get('photo') == missing_file_message:
        #     return None
        # elif raw_message.get('file') == missing_file_message:
        #     return None
        # elif raw_message.get('thumbnail') == missing_file_message:
        #     return None


        date = raw_message['date']
        raw_text = raw_message['text']
        if isinstance(raw_text, str):
            text = raw_text
        elif isinstance(raw_text, list):
            text = ''.join([
                part['text'] if isinstance(part, dict) else part
                for part in raw_text
            ])
        else:
            raise ValueError('invalid text')

        if not text:
            return None

        return Message(
            person_name=name,
            date=date,
            text=text,
            link=LINK_TEMPLATE.format(message_id=raw_message['id']),
        )

    except Exception as e:
        print(e)
        print(raw_message['id'])
        raise



def main():
    with open(FILENAME) as f:
        raw_messages = json.load(f)['messages']

    flats = []
    for raw_message in raw_messages:
        message = parse_raw_message(raw_message)
        if message:
            try:
                flat = message_to_flat(message)
            except:
                for line in message.text.split('\n'):
                    print(line)

                print(message.link)
                raise

            if flat:
                flats.append(flat)

    unique_flats = dict()
    for flat in flats:
        key = flat.area, flat.rooms, flat.price, flat.location
        unique_flats[key] = flat

    unique_flats = list(unique_flats.values())
    unique_flats.sort(key=lambda flat: flat.message.date)
    
    matching_flats = [
        flat
        for flat in unique_flats
        if (600 <= flat.price <= 1200) and (45 <= flat.area <= 120)
    ]
    for flat in matching_flats:
        print(flat)

    print(f'Has {len(unique_flats)} unique flats (of {len(flats)} and {len(raw_messages)} messages) -> {len(matching_flats)}')


if __name__ == '__main__':
    main()
