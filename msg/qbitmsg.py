import time
import datetime
import requests
from threading import Thread, Event, Lock
from utils import threadedfunc, variable, qbit_ as qbit, functionhelper, db
from telebot.apihelper import ApiException
from telebot import types
from config.admins import check
from config import bot, logger, const, qb
from . import tools


class TorrentInfoDB(db.Handler):
    def save_metadata(self, torrent):
        self.cursor.execute('insert into MagnetMetaInfo (hash, size, fileCount, name) VALUES '
                            '(?,?,?,?)', (torrent['hash'], torrent['size'], qbit.file_count(torrent), torrent['name']))


adjust_queue_cache = []

auto_manager = qbit.AutoDownloadManager(qb)


class QbitManager:
    def __init__(self):
        self.thread = Thread(target=self.refresh, name='QbitTorrentManagerThread')
        self.torrent_managers = {}  # dict (magnet,cid,uid):QbitManager
        self.event = Event()
        self.lock = Lock()
        self.thread.setDaemon(True)
        self.thread.start()

    def add(self, magnet: str, cid=const.GOD, uid=const.GOD, delete=True, funcs=None):
        magnet = magnet.lower()
        qb.download_from_link(magnet)
        auto_manager.refresh()
        self.torrent_managers[(magnet, cid, uid)] = QbitMessage(magnet, cid, uid, funcs=funcs, del_torrent=delete)

    def remove(self, magnet, cid, uid):
        return self.torrent_managers.pop((magnet, cid, uid))

    def get_manager_by_magnet(self, magnet):
        for key, manager in self.torrent_managers.items():
            if magnet == key[0]:
                return manager
        return None

    @property
    @functionhelper.max_exc(const.MAX_ERR, requests.exceptions.BaseHTTPError, logger)
    def torrents(self):
        return qb.torrents()

    @functionhelper.endless_loop
    @functionhelper.max_exc(0, logger=logger, wait=3)
    def refresh(self):
        self.event.wait(3)
        auto_manager.refresh()
        for torrent in self.torrents:
            tm = self.get_manager_by_magnet(torrent['hash'])  # type:QbitMessage
            if tm is None:
                continue
            logger.debug(f'查看{tm}')
            tm.set_ti(auto_manager.torrents[torrent['hash']])
            tm.refresh()
            if tm.over:
                info = tm.delete()
                self.torrent_managers.pop(info)
        auto_manager.adjust()
        if self.event.is_set():
            self.event.clear()


qm = QbitManager()


class QbitMessage:
    def __init__(self, magnet, cid, uid, funcs=None, del_torrent=False):
        self.magnet = magnet
        self._sent_flag = False
        self.cid = cid
        self.uid = uid
        self.mid = 0
        self._text = ''
        self._start_time = time.time()
        self._last_refresh_time = self._start_time
        # 初始化开关
        self._display_hash = variable.Switch()
        self._display_func = variable.Switch()
        self._display_state = variable.Switch()
        self._display_queue = variable.Switch()
        self._delete_message = variable.Switch()
        self._states_sustain_time = {}
        if funcs is None:
            del_torrent = False
        self._del_torrent_flag = variable.Switch(del_torrent)
        self._msg_exc = False
        self._refresh_flag = variable.Switch(False)

        self.ti = auto_manager.torrents.get(magnet)  # type:qbit.TorrentDownloadInfo
        self.funcs = threadedfunc.RunFuncs(funcs)
        self.buttons = tools.ButtonPagesMan(self._refresh_flag, callback=self.refresh)

        self.set_ti(self.ti)
        self._init_buttons()
        self.refresh()
        logger.info(f'{self}已创建')

    def _init_buttons(self):
        logger.debug('开始初始化按钮')
        main = self.buttons.add_button_page('main', self.uid)
        torrent = self.buttons.add_button_page('ti', self.uid)
        manager = self.buttons.add_button_page('manager', self.uid)
        confirm = self.buttons.add_button_page('confirm', self.uid)

        main.add_custom_handler('Torrent', 'ti', self.buttons.set_button_page)
        main.add_custom_handler('Manager', 'manager', self.buttons.set_button_page)

        manager.add_switch('`○|●`Auto Delete', self._del_torrent_flag, answer='种子在下载完成后`不会|会`自动删除')
        manager.add_switch('`○|●`Show hash', self._display_hash, answer='已`关闭|开启`哈希显示')
        manager.add_switch('`○|●`Show Funcs', self._display_func, answer='已`隐藏|显示`函数状态')
        manager.add_switch('`○|●`Show State', self._display_state, answer='已`隐藏|显示`种子下载状态')
        manager.add_switch('`○|●`Show Queue', self._display_queue, answer='已`隐藏|显示`种子下载队列排名')
        manager.add_switch('`○|●`Delete Message', self._delete_message, answer="种子下载完成后这条消息`不会|会`自动删除")
        manager.add_custom_handler('<<Back', 'main', self.buttons.set_button_page)

        # ti.add_custom_handler(self.state, self.state, self._ctrl_torrent)
        torrent.add_custom_handler('Delete', 'confirm', self.buttons.set_button_page,
                                   args=('请在下方确认是否要删除这个种子,删除后无法恢复数据', True))
        torrent.add_custom_handler("Run funcs anyway", "timeout>0", self.set_timeout)
        torrent.add_custom_handler("Queue Top", 's_top',
                                   lambda call: qb.set_max_priority(self.magnet))
        torrent.add_custom_handler('<<Back', 'main', self.buttons.set_button_page)

        confirm.add_custom_handler('No', 'ti', self.buttons.set_button_page)
        confirm.add_custom_handler('Yes', 'delete', self._del_files)

        self.buttons.init_button_page('main')
        logger.debug("初始化按钮成功")

    def set_timeout(self, call):
        if hasattr(call, 'data'):
            self.ti.max_download_time = 0
            bot.answer_callback_query(call.id, "立即超时种子管理器!")

    def set_ti(self, ti: qbit.TorrentDownloadInfo):
        self.ti = ti
        new_text = self.format_message()
        if self._text != new_text:
            self._text = new_text
            self._refresh_flag.on()

    def _del_files(self):
        self._del_torrent_flag.set(True)
        qb.delete_permanently([self.magnet])

    def _refresh_time(self):
        refresh_time = time.time()
        self._states_sustain_time[self.ti['state']] = self._states_sustain_time.get(
            self.ti['state'], 0.0) + (refresh_time - self._last_refresh_time)
        self._last_refresh_time = refresh_time

    @property
    def torrent(self):
        return self.ti.torrent

    def refresh(self):
        if self.ti is None:
            return
        self._refresh_time()
        if self.ti['progress'] == 1:
            self.funcs.run(self)
        elif self.ti.overtime:
            self.funcs.run(self)
        if self.ti['state'] in ('queuedDL',):
            logger.info(f"当前的{self}还没有启动,不会发送消息")
            self._refresh_flag.off()
        if self._refresh_flag:
            try:
                self._msg_handler()
            except ApiException:
                qm.remove(self.magnet, self.cid, self.uid)

    @property
    def text(self):
        current_time = datetime.datetime.utcnow() + datetime.timedelta(**const.TINEZONE_DELTA)
        time_text = '最后更新于：' + current_time.strftime('%Y-%m-%d %H:%M:%S') + '\n'
        return time_text + self._text

    def format_message(self):
        if self.ti is None:
            return "目前还没有添加种子文件"
        format_list = [f"名称:{self.ti['name']}"]
        if self._display_queue:
            format_list.append(f"队列排序:{self.ti['priority']}")
        if self._display_hash:
            format_list.append(f"hash:<code>{self.ti['hash']}</code>")
        if self._display_state:
            format_list.append(f"State:{self.ti['state']}")
        format_list.append(f"进度:<code>{self.ti['progress'] * 100:.2f}/100</code>")
        if self._display_func:
            format_list.append("\n已加载的函数")
            format_list += [f.__name__ for f in self.funcs.funcs]
        return '\n'.join(format_list)

    @functionhelper.max_exc(3, wait=3, exc_types=ApiException)
    def _msg_handler(self):
        if self._sent_flag:
            self.msg = bot.edit_message_text(self.text, self.cid, self.mid,
                                             reply_markup=self.buttons.buttons,
                                             parse_mode='HTML')
            logger.debug(f"edit message for {self.msg.chat.id},manager {self}")
        else:
            self.msg = bot.send_message(self.cid, self.text, reply_markup=self.buttons.buttons, parse_mode='HTML')
            self.mid = self.msg.message_id
            self.buttons.set_id(self.cid, self.mid)
            self._sent_flag = True
            logger.debug(f"send message to {self.msg.chat.id},manager {self}")
        self._refresh_flag.off()

    @property
    def overtime(self):
        return self.ti.overtime

    @property
    def over(self):
        if self.ti.overtime:
            return self.funcs.over
        return self.ti.over and self.funcs.over

    def delete(self):
        if not self.over:
            logger.warning('函数未执行即调用了delete方法,请检查代码编写情况')
            return
        self.buttons.del_pages()
        self._msg_handler()
        with TorrentInfoDB('main.db', none_stop=True) as d:
            d.save_metadata(self.ti)
        if self.exc_occu():
            logger.warning('函数执行过程中发生了异常,管理器不会自动删除已下载的种子文件,请手动删除')
            return self.magnet, self.cid, self.uid
        if self.ti.overtime:
            bot.send_message(self.cid, f'{self}出现下载超时,下载时间{self._start_time}')
            logger.info(f'{self}出现下载超时,下载时间{self._start_time}')
        if self._del_torrent_flag:
            self._del_files()
            bot.send_message(self.cid, f'已删除管理器及硬盘文件{self.magnet}')
        if self._delete_message:
            bot.delete_message(self.cid, self.mid)
        logger.info(f'{self}成功执行所有任务,已正常结束种子生命周期')
        return self.magnet, self.cid, self.uid

    def exc_occu(self):
        return self.funcs.exc_occurred

    def __hash__(self):
        return hash((self.cid, self.mid))

    def __str__(self):
        return '种子管理器' + self.magnet

    def __repr__(self):
        return "种子管理器" + self.magnet

    def __eq__(self, other):
        if not isinstance(other, QbitMessage):
            return False
        if (self.cid, self.mid) == (other.cid, other.mid):
            return True
        return False


@bot.message_handler(content_types=['document'], func=check(50))
def qbit_download(message: types.Message):
    doc = message.document  # type:types.Document
    if not message.document.file_name:
        return
    if not message.document.file_name.lower().endswith('.ti'):
        return
    # 如果文件大于50MiB,就拒绝下载 50*1024*1024=52428800
    if doc.file_size > 52428800:
        return bot.send_message(message.chat.id, "文件过大,无法下载")
    file_info = bot.get_file(doc.file_id)

    try:
        response = requests.get('https://api.telegram.org/file/bot{0}/{1}'.format(bot.token, file_info.file_path))
    except requests.exceptions.HTTPError:
        bot.send_message(message.chat.id, "无法从网络中获取种子文件")
    except Exception as e:
        bot.send_message(message.chat.id, f"解析种子文件发生未知错误{e}")
    else:
        name = f'./$temp/{doc.file_name}'
        with open(name, 'wb') as fo:
            fo.write(response.content)


@bot.message_handler(['qbitadd'], func=check(100))
def qbitadd(message):
    magnets = qbit.search_hash(message.text)
    for magnet in magnets:
        qm.add(magnet, message.chat.id, message.from_user.id, False)
