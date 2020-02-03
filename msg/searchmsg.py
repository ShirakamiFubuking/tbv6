import re
import traceback
import requests
from io import BytesIO
from itertools import repeat
from utils import db
from telebot import types
from config import bot, logger
from config.exceptions import SearchError, TagNoResult, NoResultError, MagnetNoReuslt
from config.admins import check


class SearchDB(db.Handler):
    def tag(self, tags, searchmode=' intersect '):
        if searchmode.lower() not in (' intersect ', ' union ', ' except '):
            raise SearchError()
        if not tags:
            raise TagNoResult(tags)
        sql = repeat('select UrlPath from CrawlerCorr where tag=(select tag from CrawlerTags where tagS=?)', len(tags))
        query = searchmode.join(sql)
        self.cursor.execute(f'select * from CrawlerMain where UrlPath in ({query})', tags)
        return self.cursor.fetchall()

    def magnet(self, url_path):
        self.cursor.execute(
            'select * from NetDiskShare where id in (select shareId from PostToShareId where postUrlPath=?)',
            (url_path,))
        return self.cursor.fetchall()

    def search_by_url_paths(self, url_paths):
        self.cursor.execute(
            f'select * from CrawlerMain where UrlPath in ({" ,".join(repeat("?", len(url_paths)))}) '
            f'order by PostTime desc',
            url_paths)
        return self.cursor.fetchall()

    def search_url_path(self, url_path):
        self.cursor.execute('select * from Magnets where UrlPath=?', (url_path,))
        return self.cursor.fetchall()


def query_response(res, row_name=None, exc_type=NoResultError, query=None):
    if not res:
        raise exc_type(query)
    f = BytesIO()
    f.name = 'SearchResult.txt'
    if row_name:
        f.write(','.join(row_name).encode('utf-8'))
    f.write('\n'.join((str(r) for r in res)).encode('utf-8'))
    f.seek(0)

    return f


@bot.message_handler(commands=['tag'])
def search_tag(message):
    tags = []
    for entity in message.entities:
        if entity.type == 'hashtag':
            start, end = entity.offset + 1, entity.offset + entity.length
            tags.append(message.text[start:end].lower())
    with SearchDB('main.db') as d:
        res = d.tag(tags)
    res_file = query_response(res, exc_type=TagNoResult, query=tags)
    bot.send_document(message.chat.id, res_file, caption='执行成功,并返回查询结果')


part_magnet = re.compile(r'\s[a-fA-f\d]{,40}$')


# @bot.message_handler(commands=['magnet'])
def search_magnet(message):
    all_part_magnet = part_magnet.search(message.text)
    if all_part_magnet is None:
        raise NoResultError()
    with SearchDB('main.db') as d:
        res = d.magnet(all_part_magnet.group().lower())
    res_file = query_response(res, exc_type=MagnetNoReuslt, query=all_part_magnet.group())
    bot.send_document(message.chat.id, res_file, caption='执行成功,并返回查询结果')


@bot.message_handler(commands=['sql'], func=check(100))
def exec_sql(message):
    try:
        with db.Handler('main.db') as d:
            sql = message.text[5:]
            d.cursor.execute(sql)
            res = d.cursor.fetchall()
    except Exception as e:
        logger.warning(e)
        traceback.print_exc()
        bot.send_message(message.chat.id, 'SQL 执行遇到失败,数据库已回滚')
    else:
        res_file = query_response(res, exc_type=NoResultError, query=sql)
        bot.send_document(message.chat.id, res_file, caption='执行成功,并返回查询结果')


@bot.message_handler(commands=['search'])
def search(message):
    try:
        query = message.text.split(' ', 1)[1]
    except IndexError:
        bot.send_message(message.chat.id, "你什么也没有搜索!\n使用方法:`/search 关键词1 关键词2`\n"
                                          "Tips:长按命令列表中的命令可快速将命令发送至输入框", parse_mode="markdown")
        return
    res = requests.get('http://127.0.0.1:23434/api/search', {'query': query, 'limit': 100}).json()
    with SearchDB("main.db") as d:
        res = d.search_by_url_paths(res)
    text = ("为你显示距离发布时间最近的十条结果\n点击按钮可获得磁力链接,如数据库中查找到了补档链接则会返回补档链接\n\n"
            "{}\n")

    intro_list = []
    btns = types.InlineKeyboardMarkup(1)
    for i, r in enumerate(res[:10]):
        intro = '{}:<a href="https://liuli.se{}">{}</a>'.format(i + 1, r[2], r[1])
        btn = types.InlineKeyboardButton(r[1], callback_data=f'~:search:{r[2]}')
        btns.add(btn)
        intro_list.append(intro)
    text = text.format("\n".join(intro_list))
    if message.chat.type != "private":
        text += '\n\n检测到当前环境不是私聊,为避免机器人消息刷屏,将不会发送按钮,如需获取相关的磁力链接或补档链接,请私聊发送搜索'
        btns = None
    bot.send_message(message.chat.id, text, reply_markup=btns, parse_mode="HTML")
    # res_file = query_response(res, exc_type=NoResultError, query=query)
    # bot.send_document(message.chat.id, res_file, caption='执行成功,并返回查询结果')


@bot.callback_query_handler(func=lambda call: call.data.startswith('~:search:'))
def search2(call):
    url_path = call.data.split(":")[2]
    with SearchDB("main.db") as d:
        res = d.search_url_path(url_path)
        o_res = d.magnet(url_path)
    m_list = []
    for r in res:
        m_list.append('<code>magnet:?xt=urn:btih:{}</code>'.format(r[2]))
    o_list = []
    for r in o_res:
        o_list.append(r[3])
    text = "{}\n\n{}".format("\n".join(m_list), "\n".join(o_list))
    if not text:
        text = "什么也没找到(包括磁力链接)!"

    bot.send_message(call.message.chat.id, text, parse_mode="HTML")
