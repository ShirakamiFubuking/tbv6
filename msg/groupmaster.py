import json
import time
import datetime as dt
from io import StringIO

from config import bot, const
from config.admins import check
from utils import db


class MessageDB(db.Handler):
    def save_pinned_message(self, message, pinned_message):
        cid = message.chat.id
        mid = message.message_id
        pinned_mid = pinned_message.message_id
        uid = message.from_user.id
        content = pinned_message.text or pinned_message.caption or pinned_message.content_type.title()
        timestamp = int(time.time())
        first_name = message.from_user.first_name
        last_name = message.from_user.last_name
        username = message.from_user.username
        self.cursor.execute("insert into pinnedMessages "
                            "(cid, uid, mid, content, timestamp, firstName, lastName, username,pinnedMid) "
                            "VALUES (?,?,?,?,?,?,?,?,?)",
                            (cid, uid, mid, content, timestamp, first_name, last_name, username, pinned_mid))

    def get_pinned_message(self, cid, limit=10):
        self.cursor.execute('select * from pinnedMessages where cid=? order by timestamp desc limit ?', (cid, limit))
        return self.cursor.fetchall()


@bot.message_handler(content_types=('pinned_message',))
def put_pinned_message(message):
    # import json
    # print(json.dumps(message, default=lambda obj: obj.__dict__))
    with MessageDB('messages.db') as d:
        d.save_pinned_message(message, message.pinned_message)


@bot.message_handler(commands=['pinnedmsgs'])
def get_pinned_message(message):
    try:
        limit = int(message.text.split()[1])
        if limit > 100:
            limit = 100
    except (ValueError, IndexError):
        limit = 10
    with MessageDB("messages.db") as d:
        msgs = d.get_pinned_message(message.chat.id, limit)
    pinned_msgs = []
    for msg in msgs:  # type:
        date = (dt.datetime.fromtimestamp(msg[5]) + dt.timedelta(**const.TINEZONE_DELTA)
                ).strftime("%m{}%d{} %H:%M").format('月', '日')
        link = f'https://t.me/c/{str(msg[1])[4:]}/{msg[9]}'
        content = msg[4] if len(msg[4]) < 10 else f'{msg[4][:3]}...{msg[4][-3:]}'
        msg_temp = '该消息由{user}置顶于{date}:<a href="{link}">{content}</a>'.format(
            user=msg[6], date=date, link=link, content=content
        )
        pinned_msgs.append(msg_temp)
    text = "\n".join(pinned_msgs)
    bot.send_message(message.chat.id, text, parse_mode="HTML")


@bot.message_handler(commands=['minfo'], func=check(100))
def msg_info(message):
    f = StringIO()
    f.name = "Response.txt"
    json.dump(message, f, default=lambda obj: obj.__dict__)
    f.seek(0)
    bot.send_document(const.GOD, f)
