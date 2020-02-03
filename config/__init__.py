import atexit
import os
import telebot
import logging
import qbittorrent
from utils import qbit_ as qbit
from utils import functionhelper

from . import admins, const, autobackup, filelock, exceptions

qb = qbittorrent.Client(const.QBIT_HOST)  # type:qbittorrent.Client
qb.login(const.QBIT_USR, const.QBIT_PWD)

functionhelper.exc_info = const.PRINT_EXC
autobackup.exc_info = const.PRINT_EXC

logging.basicConfig(format='%(asctime)s %(pathname)s %(funcName)s %(lineno)s '
                           '%(levelname)s - %(message)s"', level=logging.WARNING)
logger = logging.getLogger('Main bot logger')
logger.setLevel(logging.WARNING)

f = open(const.LOCK_FILE, 'w')
f.write(str(os.getpid()))
filelock.filelock(f)
atexit.register(filelock.unlock, f)


class CustomBot(telebot.TeleBot):
    def exec_task(self, func, message):
        try:
            logger.debug(f"执行任务{func.__name__}")
            func(message)
        except exceptions.AdminBaseError as e:
            self.send_message(message.chat.id, str(e))
        except exceptions.SearchError as e:
            self.send_message(message.chat.id, str(e))
        except Exception as e:
            logger.warning(e, exc_info=True)
        finally:
            pass


proxy = None
if os.name == 'nt':
    proxy = {'https': 'socks5://localhost:1080',
             'http': 'http://127.0.0.1:1081'}
telebot.apihelper.proxy = proxy
bot = CustomBot(const.BOT_API_TOKEN, num_threads=8)
