import base64
import sqlite3
import time
from datetime import datetime
import requests
from config import logger, const
from utils import db, ll_crawler

hostname_file = 'files/liuli_hostname.txt'


class CrawlerDB(db.Handler):
    def search(self, url_path):
        self.cursor.execute('select * from CrawlerMain where UrlPath=?', (url_path,))
        return self.cursor.fetchall()

    def search_msg(self, url_path):
        self.cursor.execute('select * from MakeupMessage where PostUrlPath=?', (url_path,))
        return self.cursor.fetchall()

    def save_post(self, info: ll_crawler.post_info):
        logger.info('存储发布的文章信息进入数据库')
        self.cursor.execute('insert into CrawlerMain (Title, UrlPath, PicUrl, PostTime, Author, Category)'
                            'values (?,?,?,?,?,?)', (info.title, info.url_path, info.pic_url,
                                                     info.accurate_time, info.author, info.category))
        self.cursor.executemany('insert or ignore into CrawlerTags (tag,tagS) values (?,?)',
                                map(lambda x: (x, x.strip().lower().replace(' ', '_')), info.tags))

        self.cursor.executemany("insert or ignore into CrawlerCorr (UrlPath,tag) values (?,?)",
                                ((info.url_path, tag) for tag in info.tags))
        logger.info('存储发布的文章信息进入数据库完成')

    def save_magnets(self, magnets, info):
        if not magnets:
            self.save_no_magnets(info)
            return
        self.cursor.executemany("insert or ignore into Magnets (magnet, UrlPath) values (?,?);",
                                ((magnet.lower(), info.url_path) for magnet in magnets))

    def save_no_magnets(self, info):
        self.cursor.execute('insert or ignore into CrawlerNoMagnet (urlPath, CrawlerGetTime,PostTime) values (?,?,?)',
                            (info.url_path, int(time.time()), info.accurate_time))

    def del_no_magnets(self, url_path):
        self.cursor.execute('delete from CrawlerNoMagnet where UrlPath=?', (url_path,))

    def all_no_magnets(self):
        threshold_time = int(time.time()) - 604800
        self.cursor.execute(
            'select * from CrawlerMain where UrlPath in  (select urlPath from CrawlerNoMagnet where PostTime > ?)',
            (threshold_time,))
        return self.cursor.fetchall()

    def search_tags(self, url_path):
        self.cursor.execute('select tag from CrawlerCorr where UrlPath=?', (url_path,))
        return {[t[0] for t in self.cursor.fetchall()]}


def save_hostname(crawler):
    with open(hostname_file, 'w', encoding='utf-8') as f:
        f.write(crawler.hostname)


def load_hostname():
    with open(hostname_file, encoding='utf-8') as f:
        return f.read()


def check_up_no_magnets(crawler):
    with CrawlerDB('main.db') as d:
        posts = d.all_no_magnets()
        for post_row in posts:
            tags = d.search_tags(post_row[2])
            post = ll_crawler.post_info(
                post_row[1],
                "https://" + crawler.hostname + post_row[2],
                post_row[2],
                post_row[3],
                datetime.fromtimestamp(post_row[4]).strftime('%m{}%d{}').format('月', '日'),
                post_row[4],
                post_row[6],
                post_row[5],
                tags
            )
            magnets = crawler.get_magnets(post.url)
            if magnets:
                yield post, magnets
                d.del_no_magnets(post.url_path)


def main(page=1):
    crawler = ll_crawler.Crawler()
    posts = crawler.get_list(page)
    with CrawlerDB('main.db') as d:
        for post in posts:
            try:
                post_info = ll_crawler.get_post_info(post)
                if d.search(post_info.url_path):
                    continue
                d.save_post(post_info)
            except IndexError:
                logger.warning("检测到不符合寻常的类型,跳过了本次遍历")
                continue
            except sqlite3.IntegrityError:
                logger.warning("数据库中已查找到,尝试直接进行下一步")
                pass
            except Exception as e:
                logger.warning(e, exc_info=const.PRINT_EXC)
                continue
            res = crawler.get_page(post_info.url)
            res.encoding = 'utf-8'
            data = {'path': post_info.url_path, 'post_time': post_info.accurate_time,
                    'bin': base64.b64encode(res.content).decode('ascii')}
            requests.post('http://127.0.0.1:23434/api/put', json=data)
            magnets = crawler.get_magnets(res.text)
            try:
                d.save_magnets(magnets, post_info)
            except sqlite3.IntegrityError:
                pass
            yield post_info, magnets
        for post, magnets in check_up_no_magnets(crawler):
            yield post, magnets
    save_hostname(crawler)
