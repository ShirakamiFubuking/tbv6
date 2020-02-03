import threading
from telebot.types import InlineKeyboardButton, CallbackQuery, InlineKeyboardMarkup
from collections import OrderedDict
from config import bot, const
from utils import variable
import re

split_mark = '|'
replace_mark = re.compile(r'`.*?`')
space_mark = re.compile(r'<<.*?>>')


# 代替eval的函数
def switch_interpret(s: str) -> bool:
    if s == 'T':
        return True
    elif s == 'F':
        return False
    return False


class ButtonMan:
    def __init__(self, header, uid=0, row_width=3, cid=0, mid=0, refresh_flag=None, callback=None):
        self._refresh_flag = refresh_flag  # type: variable.Switch
        self._callback = callback
        self.header = header
        self.uid = uid
        self._cid = cid
        self._mid = mid
        self._listening_callback_funcs_list = []
        self._buttons = OrderedDict()
        # 一行有几个
        self.row_width = row_width

    def set_id(self, cid, mid):
        """
        因为按钮会在发送之前初始化,所以为了按钮的鉴权必须要在消息发送之后将机器人的消息id拿回来
        :param cid:
        :param mid:
        :return:
        """
        self._cid = cid
        self._mid = mid

    def _check(self, text: str):
        def wrapper(call: CallbackQuery) -> bool:
            # 最先验证是否对应本次消息
            if call.message.message_id != self._mid or call.message.chat.id != self._cid:
                return False
            # 首先验证头部
            if not call.data.startswith(self.header + ':'):
                return False
            # 接着验证命令
            if call.data.split(':')[1] != text:
                return False
            # 最后检测操作用户的合法性
            if call.from_user.id == const.GOD:
                return True
            elif call.from_user.id == self.uid:
                return True
            "此处发送信息给验证失败的用户"
            return False

        return wrapper

    def _add_listener(self, func, text):
        @bot.callback_query_handler(self._check(text))
        def _handler(call: CallbackQuery):
            res = func(call)
            try:
                if not res[2]:
                    self._refresh_flag.on()
            except (TypeError, IndexError):
                pass
            if self._callback is not None:
                self._callback()
            return res

        self._listening_callback_funcs_list.append(_handler)

    def add_switch(self, text: str, flag: variable.Switch, answer: str = ''):
        display_text = re.sub(space_mark, '', re.sub(replace_mark, '{}', text))
        display_answer = re.sub(replace_mark, '{}', answer)

        text_mark = [s.strip('`').split(split_mark) for s in re.findall(replace_mark, text)]
        answer_mark = [s.strip('`').split(split_mark) for s in re.findall(replace_mark, answer)]

        s_data = ['T', 'F']

        def _get_mark(l, x):
            return [p[x] for p in l]

        def _refresh(switch: bool):
            new_text = display_text.format(*_get_mark(text_mark, switch.real))
            cb_data = f"{self.header}:{text}:{s_data[switch.real]}"
            button = InlineKeyboardButton(new_text, callback_data=cb_data)
            self._refresh_flag.on()
            self._buttons[text] = button

        def _listener(call: CallbackQuery):
            data = call.data.split(':')  # type:list
            # 这里不使用eval是因为避免注入(虽然觉得不会有这种注入发生,但还是有备无患)
            switch = switch_interpret(data[2])
            if flag.set(switch):
                if answer:
                    # 应答按钮
                    bot.answer_callback_query(call.id, display_answer.format(*_get_mark(answer_mark, switch.real)))
                _refresh(switch)

        _refresh(flag.flag)
        self._add_listener(_listener, text)

    def add_counter(self, text):  # 暂时不会用的，搁置
        """
        这个函数目前也用不上,打算以后开发
        而且仔细想一想单独弄这么一个计数器也没有什么意义,我做这个本来是为了简化消息处理流程的
        """
        pass

    def add_answer_callback(self, text, explain, alert=False):
        """就是简单的回复一下"""

        def _refresh():
            cb_data = f"{self.header}:{text}"
            button = InlineKeyboardButton(text, callback_data=cb_data)
            self._buttons[text] = button

        def _listener(call: CallbackQuery):
            # print('answer callback')
            bot.answer_callback_query(call.id, explain, show_alert=alert)

        _refresh()
        self._add_listener(_listener, text)

    def add_custom_handler(self, text: str, data: str, func, args=(), kwargs=None, no_refresh=False):
        """可以根据喜好自由的添加函数,但函数的第一个参数必须是call
        函数可以有返回值,也可以没有.
        但有返回值的情况下必须返回三个参数 `text`和`data`,和`_no_refresh`,用此可以更新
        """
        if kwargs is None:
            kwargs = {}

        def _refresh(new_text=None, new_data=None, _no_refresh=False):
            if no_refresh or _no_refresh:
                return
            _data = f"{self.header}:{text}:{new_data or data}"
            _text = new_text or text

            button = InlineKeyboardButton(_text, callback_data=_data)
            self._buttons[text] = button
            self._refresh_flag.on()

        def _listener(call: CallbackQuery):
            res = func(call, *args, **kwargs)
            # print(res)
            if res is None:
                _refresh()
            else:
                _refresh(*res)

        _refresh()
        self._add_listener(_listener, text)

    @property
    def buttons(self):
        handler = InlineKeyboardMarkup(self.row_width)
        handler.add(*self._buttons.values())
        return handler

    def del_manager(self):
        """
        当这个种子管理器被删除时,会进行必要的清理工作
        1.清理下载的硬盘文件为之后的下载腾出空间
        2.清理注册的python函数避免大量的函数占用内存以及拖慢轮询速度
        :return:
        """
        # 这里使用了一些比较hack的方式删除了加入的函数
        for func in self._listening_callback_funcs_list:
            for i in range(len(bot.callback_query_handlers) - 1, -1, -1):
                if bot.callback_query_handlers[i].func == func:
                    bot.callback_query_handlers.pop(i)
        self._listening_callback_funcs_list.clear()
        self._buttons.clear()
        self._callback = None


class ButtonPagesMan:
    def __init__(self, refresh_flag, callback=None):
        self._callback = callback
        self.__mid = 0
        self.__cid = 0
        self.button_pages = OrderedDict()
        self.listener_list = []
        self._c_page = None
        self._c_name = ''
        self._refresh_flag = True
        self._inited = False
        self._refresh_flag = refresh_flag  # type: variable.Switch
        self._lock = threading.Lock()

    def set_id(self, cid, mid):
        # 应该只需要执行一次,也就是发送消息后那一次
        self.__mid = mid
        self.__cid = cid
        for v in self.button_pages.values():  # type:ButtonMan
            v.set_id(cid, mid)

    def add_button_page(self, header, uid=0, row_width=3):
        buttons = ButtonMan(header, uid, row_width, self.__cid, self.__mid, refresh_flag=self._refresh_flag,
                            callback=self._callback)
        self.button_pages[header] = buttons
        return buttons

    def set_button_page(self, call: CallbackQuery, answer="切换到{}界面", alert=None):
        name = call.data.split(':')[2]
        answer = answer.format(name)
        with self._lock:
            if self._c_name == name:
                return None, None, True
            self._c_name = name
            self._c_page = self.button_pages.get(name)
        bot.answer_callback_query(call.id, answer, show_alert=alert)

    def init_button_page(self, name) -> None:
        if self._inited:
            return
        self._c_page = self.button_pages[name]
        self._c_name = name
        self._refresh_flag.off()
        self._inited = True

    @property
    def buttons(self):
        if self._c_page is None:
            return None
        return self._c_page.buttons

    def del_pages(self):
        self._refresh_flag.on()
        self._c_page = None
        for v in self.button_pages.values():
            v.del_manager()
        self.button_pages.clear()


if __name__ == '__main__':
    pass
