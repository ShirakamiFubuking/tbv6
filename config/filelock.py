import logging
import sys
logger = logging.getLogger('file lock')


def filelock(f):
    try:
        import fcntl
    except ImportError:
        return

    try:
        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return f
    except BlockingIOError:
        logger.critical('检测到同一个程序正在运行,本程序自动退出')
        sys.exit(255)


def unlock(f):
    try:
        import fcntl
    except ImportError:
        return
    f.write('')
    fcntl.flock(f, fcntl.LOCK_UN)
    f.close()
    logger.info("程序退出,并正常关闭文件锁")
