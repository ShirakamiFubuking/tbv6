from threading import Thread, Event
import shutil
import datetime
from utils import functionhelper
import logging

logger = logging.getLogger("Database backup logger")
event = Event()
exc_info = False
db_names = ('main.db', 'messages.db')


@functionhelper.endless_loop
@functionhelper.max_exc(0)
def autobackup():
    for db_name in db_names:
        backup_name = 'backup/{}.{}.backup'.format(
            db_name,
            datetime.datetime.utcnow().strftime("%Y-%m-%d_%H-%M-%S-UTC0")
        )
        try:
            shutil.copy(db_name, backup_name)
        except Exception as e:
            logger.error(e,exc_info=exc_info)
            logger.error('无法正常完成数据库备份')
        finally:
            pass
        logger.info(f"已自动备份数据库至{backup_name}")
        if event.is_set():
            event.clear()
    event.wait(86400)


_backup_thread = Thread(target=autobackup, name="Database auto backup thread")
_backup_thread.setDaemon(True)
_backup_thread.start()
