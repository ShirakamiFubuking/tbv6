class BaseBotError(Exception):
    pass


class SearchError(BaseBotError):
    def __init__(self):
        super(SearchError, self).__init__()

    def __str__(self):
        return "这是一个搜索错误基类,你不应该遇见这个错误,如果你看到了这行文字请联系开发者 @Ytyan"


class NoResultError(SearchError):
    def __init__(self, query=''):
        super(NoResultError, self).__init__()
        self.query = query

    def __str__(self):
        if self.query:
            return f"你搜索的 {self.query} 没有找到"
        else:
            return "你什么也没有搜索"


class TagNoResult(NoResultError):
    def __init__(self, tags):
        tags_txt = ' '.join('#' + tag for tag in tags)
        super(TagNoResult, self).__init__(tags_txt)


class MagnetNoReuslt(NoResultError):
    def __init__(self, magnets):
        super(MagnetNoReuslt, self).__init__(magnets)


class AdminBaseError(BaseBotError):
    pass


class AdminLevelError(AdminBaseError):
    def __init__(self, level):
        super(AdminLevelError, self).__init__()
        self.level = level

    def __str__(self):
        return f"管理员的等级被限制在1-99级,您定义的等级为:{self.level},不满足条件"


class AdminNotExistsError(AdminBaseError):
    def __init__(self, user):
        super(AdminNotExistsError, self).__init__()
        self.user = user

    def __str__(self):
        return f"用户id{self.user}不在管理员列表中"
