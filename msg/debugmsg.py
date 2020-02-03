import re

from config import bot
from config.admins import check
from utils import db

name = re.compile(r'/wp/\d+.html')


@bot.message_handler(commands=('delpost',), func=check(100))
def del_post_in_database(message):
    with db.Handler('main.db') as d:
        d.cursor.execute('select id from CrawlerMain where UrlPath=?', (name.findall(message.text)[0],))
        url_id = d.cursor.fetchall()[0][0]
        d.cursor.execute('delete from CrawlerMain where id=?', (url_id,))
    bot.send_message(message.chat.id, 'execute over.')
