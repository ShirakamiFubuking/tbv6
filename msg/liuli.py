import requests

from io import BytesIO
from queue import Queue, Empty, Full
from threading import Thread, Lock
from net.upload import Upload
from utils.netdisk import Rclone
from config.admins import check
from . import qbitmsg
from net import liuli as ll
from telebot import types
from utils import functionhelper, db
from config import const, bot, proxy, logger


class MessagesDB(db.Handler):
    def save_message(self, post_url_path, cid, mid):
        self.cursor.execute('insert into MakeupMessage (PostUrlPath,cid,mid) values (?,?,?)',
                            (post_url_path, cid, mid))

    def search_uploaded(self, magnet):
        self.cursor.execute('select * from MagnetNetspace where magnet=?', (magnet,))
        return self.cursor.fetchall()

    def save_share(self, share_obj, url_path):
        self.cursor.execute(share_obj.db_query(), share_obj.db_params)
        lrid = self.cursor.lastrowid
        self.cursor.execute('insert into PostToShareId (postUrlPath, shareId) VALUES (?,?)', (url_path, lrid))

    def search_share(self, url_path):
        self.cursor.execute('select * from NetDiskShare where id=(select * from PostToShareId where postUrlPath=?)',
                            (url_path,))
        return self.cursor.fetchall()


class MessageHandler:
    def __init__(self, post, magnets):
        self._name_temp = 'Message handler, ti hash count {hash_count}. Url: {url},complete:{com},failed:{failed}'
        if not magnets:
            return
        self.post = post  # type:ll.ll_crawler.post_info
        self.magnets = magnets
        self.barrier = len(magnets)
        self.photo = 'AgADBQAD1qgxG05W-VTgxpRzji2dvuQ4GzMABAEAAwIAA3gAAzrKAgABFgQ'
        try:
            self.download_pic()
        except requests.RequestException:
            pass
        self.remote_basepath = '/神社新/{post_name}'.format(post_name=post.title)
        self.bd_path = f'/神社新/{self.post.url_path.rsplit("/", 1)[1].rsplit(".", 1)[0]}/'
        self._count = 0
        self._faild_count = 0
        self.remote_rar_path = f'/神社新/{post.title}/压缩文件'
        self.remote_unrar_path = '/解压文件/{magnet}/'
        self.tm_list = []
        self._lock = Lock()
        self._set_name()

    def _set_name(self):
        self.__name__ = self._name_temp.format(hash_count=len(self.magnets),
                                               url=self.post.url,
                                               com=self._count,
                                               failed=self._faild_count)

    @functionhelper.max_exc(exc_types=requests.HTTPError)
    def download_pic(self):
        if not self.post.pic_url:
            return
        f = BytesIO()
        f.name = f'Picture.{self.post.pic_url.rsplit(".", 1)[-1]}'
        res = requests.get(self.post.pic_url, proxies=proxy)
        f.write(res.content)
        f.seek(0)
        self.photo = f

    def __call__(self, tm):
        if isinstance(tm, str):
            # if tm.startswith(self.remote_basepath):
            self._count += 1
            self._prepare_msg()
            return
        if tm.overtime:
            self._faild_count += 1
            self._count += 1
            self._prepare_msg()
            return
        path = tm.torrent['save_path'] + tm.torrent['name']
        unc_remote_path = self.remote_basepath + "/" + tm.torrent['name']  # unc: uncensored remote path
        up_obj = Upload(path)
        up_obj.set('magnet', tm.magnet)
        up_obj.all_in_one(tm.torrent, unc_remote_path, self.remote_rar_path.format(magnet=tm.torrent['hash'].upper()),
                          self.remote_unrar_path.format(magnet=tm.torrent['hash']), tm.torrent['hash'].upper())
        self._count += 1
        self._prepare_msg()

    def _prepare_msg(self):
        self._set_name()
        if self._count != self.barrier:
            return
        od_share_link = ''
        gd_share_link = ''
        if self._count == self._faild_count:
            logger.warning(f"所有种子上传尝试全部失败,将仅发送")
        rc = Rclone(config_path=const.RCLONE_CONFIG)
        with MessagesDB('main.db', none_stop=True) as mdb:
            od_share = rc.share("od", self.remote_basepath)
            od_share_link = od_share.link
            logger.info(f"分享{od_share.field},链接{od_share.link}")
            mdb.save_share(od_share, self.post.url_path)
        with MessagesDB('main.db', none_stop=True) as mdb:
            gd_share = rc.share('gdedu', self.remote_basepath)
            gd_share_link = gd_share.link
            logger.info(f"分享{gd_share.field},链接{gd_share.link}")
            mdb.save_share(gd_share, self.post.url_path)
        self.send_message(od=od_share_link, gd=gd_share_link)

    def send_message(self, od='', bd='', gd='', **kwargs):
        btns = types.InlineKeyboardMarkup()
        btn = types.InlineKeyboardButton('原始链接', url=self.post.url)
        btns.row(btn)
        msg_text = (f'<a href="{self.post.url}">{self.post.title}</a>\n'
                    f'由{self.post.author}发表于{self.post.time}\n'
                    f'分类: #{self.post.category}\n'
                    '{share_links}\n'
                    f'tags: {" ".join(("#{}".format(tag.strip().replace(" ", "_")) for tag in self.post.tags))}')
        share_links = []
        if od:
            btn = types.InlineKeyboardButton('OneDrive', url=od)
            btns.row(btn)
            share_links.append(f'<a href="{od}">OneDrive</a>')
        if gd == 'goindex':
            goindex = f"https://falling-union-6e5b.ytyan.workers.dev/{self.remote_basepath}/"
            btn = types.InlineKeyboardButton('GoIndex', url=goindex)
            btns.row(btn)
            share_links.append(f'<a href="{goindex}">GoIndex</a>')
        elif gd != "":
            btn = types.InlineKeyboardButton('GoogleDrive', url=gd)
            btns.row(btn)
            share_links.append(f'<a href="{gd}">GoogleDrive</a>')
        bot.send_chat_action(const.GOD, 'typing')
        msg_text = msg_text.format(share_links='\n'.join(share_links))
        msg = bot.send_photo(const.CHANNEL, self.photo, caption=msg_text, parse_mode="HTML", reply_markup=btns,
                             disable_notification=True)
        with MessagesDB('main.db', none_stop=True) as msgdb:
            msgdb.save_message(self.post.url_path, msg.chat.id, msg.message_id)
        bot.forward_message(const.GOD, msg.chat.id, msg.message_id)


page_queue = Queue(1)
running = False


class RunningCrawlerError(Exception):
    pass


@bot.message_handler(commands=('get',), func=check(80))
def check_site_update(message):
    try:
        if running:
            raise RunningCrawlerError
        page = int(message.text[5:])
        page_queue.put_nowait((page, message.chat.id, message.from_user.id))
    except (Full, RunningCrawlerError):
        logger.info("被正在进行的任务阻塞")
        bot.send_message(message.chat.id, '现在还在忙呢,别着急啊')
        return
    except Exception as e:
        logger.warning(e)
        return
    bot.send_message(message.chat.id, 'GETTING...')


@functionhelper.endless_loop
@functionhelper.max_exc(0, wait=0)
def main():
    global running
    try:
        page, cid, uid = page_queue.get(timeout=1800)
    except Empty:
        page, cid, uid = 1, const.GOD, const.GOD
    running = True
    try:
        for post_info, magnets in ll.main(page):
            bot.send_message(const.GOD, f'找到新文章[{post_info.title}]({post_info.url})', parse_mode='markdown',
                             disable_notification=True)
            handler = MessageHandler(post_info, magnets)
            for magnet in magnets:
                with MessagesDB('main.db')as d:
                    res = d.search_uploaded(magnet)
                if res:
                    handler(res[0][3])
                else:
                    qbitmsg.qm.add(magnet, funcs=[handler])
    except Exception as e:
        logger.warning(e)
    finally:
        running = False
        logger.info("查找新发布已完成")


loop_crawler = Thread(target=main, name='LiuliCrawlerThread')
loop_crawler.setDaemon(True)
loop_crawler.start()

if __name__ == '__main__':
    pass
