#!/usr/bin/env python3

import json
import collections
import os
from dataclasses import dataclass, field

FILENAME = os.path.join(os.environ['HOME'], 'Downloads', 'Telegram Desktop', 'ChatExport_2023-07-25', 'result.json')


@dataclass
class Message:
    date: str
    text: str

    @property
    def short_date(self):
        return self.date[:10]


@dataclass
class PersonData:
    name: str
    messages: list[Message]
    join_date: str
    unique_messages: int

    @property
    def short_name(self):
        return self.name[:30]

    @property
    def messages_count_key(self):
        return self.unique_messages, (self.messages[0].date if self.messages else (self.join_date or ''))
    
    @property
    def last_date_key(self) -> str:
        return self.messages[-1].date if self.messages else (self.join_date or '')

    @property
    def first_date_key(self) -> str:
        return self.messages[0].date if self.messages else (self.join_date or '')

    @property
    def last_lines(self) -> str:
        seen_lines = set()
        lines = []
        for message in self.messages:
            parts = message.text.split('\n')
            if len(parts) > 1 and len(parts[-1]) < 50 and (parts[-1] not in seen_lines):
                lines.append(parts[-1])
                seen_lines.add(parts[-1])
        return lines

    @property
    def nabor(self) -> int:
        if '2023-06-10' <= self.join_date < '2024-05':
            return 7
        elif '2022-06-19' <= self.join_date < '2023-06-10':
            return 6
        elif '2021-06-13' <= self.join_date < '2022-06-19':
            return 5
        elif '2020-06-01' <= self.join_date < '2021-06-13':
            return 4
        else:
            return 0

    def add_message(self, message: Message, same_id: bool):
        self.messages.append(message)
        if not same_id:
            self.unique_messages += 1


def load_messages(data):
    person_data_by_id = dict()
    prev_user_id = None
    for row in data['messages']:
        try:
            user_id = row.get('from_id') or row['actor_id']

            name = row.get('from')
            if not name:
                name = row.get('actor')
            if not name:
                continue

            if row.get('forwarded_from'):
                continue

            if user_id not in person_data_by_id:
                person_data_by_id[user_id] = PersonData(
                    name=name,
                    messages=[],
                    join_date='',
                    unique_messages=0,
                )

            date = row['date']

            if row.get('action') == 'join_group_by_link':
                person_data_by_id[user_id].join_date = date
                continue

            raw_text = row['text']
            if isinstance(raw_text, str):
                text = raw_text
            elif isinstance(raw_text, list):
                text = ''.join([
                    part['text'] if isinstance(part, dict) else part
                    for part in raw_text
                ])
            else:
                raise ValueError('invalid text')

            message = Message(date=date, text=text)
            person_data_by_id[user_id].add_message(
                message,
                same_id=user_id == prev_user_id,
            )
            prev_user_id = user_id

        except Exception as e:
            print(e)
            print(row['id'])
            raise

    return person_data_by_id


def main():
    with open(FILENAME) as f:
        data = json.load(f)

    person_data_by_id = load_messages(data)

    print(len(person_data_by_id))

    items = list(person_data_by_id.items())
    # items.sort(key=lambda name_pd: name_pd[1].last_date_key)
    items.sort(key=lambda name_pd: name_pd[1].messages_count_key)

    for _, person_data in items:
        if person_data.nabor not in {5}:
            continue

        if not person_data.messages:
            continue

        last_lines = person_data.last_lines

        print(
            f'{person_data.unique_messages:3d}/{len(person_data.messages):3d}  {person_data.nabor}  '
            f'{person_data.short_name:30s} '
            f'({person_data.join_date[:10]:10s})  '
            f'{person_data.first_date_key[:10]}...{person_data.last_date_key[:10]}'
        )
        for last_line in last_lines[:30]:
            print(f'            - {last_line}')


if __name__ == '__main__':
    main()
