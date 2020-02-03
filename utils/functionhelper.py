import logging
import time

_logger = logging.getLogger('generate logger')

exc_info = False


def max_exc(max_count=3, exc_types=Exception, logger=_logger, wait=3, err_level=logging.WARNING):
    count = 1

    def decorate(func):
        def wrapper(*args, **kwargs):
            nonlocal count
            try:
                res = func(*args, **kwargs)
            except exc_types as e:
                if count > max_count and max_count:
                    logger.error(e, exc_info=exc_info)
                    raise
                logger.log(err_level, e, exc_info=exc_info)
                if wait:
                    time.sleep(wait)
                count += 1
            else:
                count = 0
                return res

        return wrapper

    return decorate


def endless_loop(func):
    def wrapper(*args, **kwargs):
        while True:
            func(*args, **kwargs)

    return wrapper
