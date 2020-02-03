import traceback
from threading import Thread
import logging


class RunFuncs:
    def __init__(self, funcs):
        self._funcs = dict()
        self.add_func(funcs)

    @property
    def funcs(self):
        return self._funcs

    def add_func(self, value):
        if value is None:
            return
        for func in value:
            logging.debug(f"函数{func.__name__}已加入至执行队列")
            self._funcs[func] = {"thread": None,
                                 "ran": False,
                                 "result": None,
                                 "exc_type": None,
                                 "exc_info": None}

    def run(self, *args, **kwargs):
        def _run(f):
            s = self.funcs[f]
            try:
                logging.info(f"函数{f.__name__}开始执行")
                s['result'] = f(*args, **kwargs)
            except Exception as e:
                logging.warning(f"函数{f.__name__}出现错误,错误摘要{e}",exc_info=True)
                s['exc_type'] = e
                s['exc_info'] = traceback.format_exc()
            finally:
                logging.info(f"函数{f.__name__}执行完毕")
                s['ran'] = True

        for func, state in self.funcs.items():
            if state['thread'] is not None:
                continue
            name = func.__name__
            tf = Thread(target=_run, args=(func,), name=name)
            state['thread'] = tf
            tf.start()
            logging.info(f"启动线程{name}")

    @property
    def over(self):
        return all((t['ran'] for t in self.funcs.values()))

    @property
    def exc_occurred(self):
        return any(t['exc_type'] for t in self.funcs.values())
