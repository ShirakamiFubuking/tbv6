from utils import db
from .exceptions import AdminLevelError, AdminNotExistsError


class AdminPersistence(db.Handler):
    def read(self):
        self.cursor.execute('select user,level from Admin')
        return self.cursor.fetchall()

    def add(self, user, level=1):
        self.cursor.execute('insert into Admin (user,level) values(?,?)', (user, level))

    def edit(self, user, level):
        self.cursor.execute('update Admin set level=? where user=?', (level, user))

    def delete(self, user):
        self.cursor.execute('delete from Admin where user=?', (user,))


class AdminList:
    def __init__(self, file='main.db'):
        self.file = file
        with AdminPersistence(file) as d:
            self._admins = d.read()

    def __contains__(self, item):
        for user, _ in self._admins:
            if user == item:
                return True
        return False

    def __getitem__(self, item):
        for user, level in self._admins:
            if user == item:
                return level
        raise AdminLevelError(item)

    def get(self, item):
        for user, level in self._admins:
            if user == item:
                return level
        return 0

    def _get_index(self, user):
        for i, item in enumerate(self._admins):
            if user == item[0]:
                return i
        return -1

    def __setitem__(self, user, level):
        if not 0 < level < 100:
            raise AdminLevelError(level)
        index = self._get_index(user)
        if index == -1:
            self._admins.append((user, level))
            with AdminPersistence(self.file) as d:
                d.add(user, level)
        else:
            self._admins[index] = (user, level)
            with AdminPersistence(self.file) as d:
                d.edit(user, level)

    def __delitem__(self, user):
        index = self._get_index(user)
        if index == -1:
            raise AdminNotExistsError(user)
        else:
            self._admins.pop(index)
            with AdminPersistence(self.file) as d:
                d.delete(user)

    delete = __delitem__

    def add(self, user, level=1):
        self.__setitem__(user, level)

    edit = __setitem__


admin = AdminList()


def check(level=1):
    def wrapper(message):
        if admin.get(message.from_user.id) >= level:
            return True
        return False

    return wrapper


def check_dec(level=1, callback=None):
    def decorator(func):
        def wrapper(message):
            user_level = admin.get(message.from_user.id)
            if user_level >= level:
                return func(message)
            elif callback is not None:
                return callback(message, user_level, level)
            raise AdminLevelError(level)

        return wrapper

    return decorator
