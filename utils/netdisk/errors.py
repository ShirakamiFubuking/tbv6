class BaseError(Exception):
    pass


class PathNotFindError(BaseError):
    def __init__(self, target, closest, id_):
        super().__init__()
        self.target = target
        self.closest = closest
        self.id = id_

    def __str__(self):
        return f"你要找的{self.target}没有找到,找到了最接近的父目录{self.closest},id为{self.id}"


class ShareError(BaseError):
    def __init__(self, path, field, type_):
        super().__init__()
        self.path = path
        self.field = field
        self.type = type_

    def __str__(self):
        return f"你输入的远程名称{self.field}类型为{self.type},现在无法支持分享"
