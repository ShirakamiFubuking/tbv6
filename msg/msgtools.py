import sys
import time
from threading import Thread, Lock

import telebot
from utils import functionhelper
from config import bot, logger, const

schedule_delete_list = []
lock = Lock()


def schedule_delete(waittime, cid, mid):
    with lock:
        schedule_delete_list.append((waittime + time.time(), cid, mid))


@functionhelper.endless_loop
def _schedule_delete():
    for i in range(len(schedule_delete_list) - 1, 0 - 1, -1):
        deltime, cid, mid = schedule_delete_list[i]
        if time.time() > deltime:
            with lock:
                try:
                    bot.delete_message(cid, mid)
                except telebot.apihelper.ApiException as e:
                    pass
                finally:
                    schedule_delete_list.pop(i)
    time.sleep(1)


_del_thread = Thread(target=_schedule_delete, name='Schedul delete thread')
_del_thread.setDaemon(True)
_del_thread.start()
