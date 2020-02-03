class Switch:
    def __init__(self, default=False):
        self._flag = default

    @property
    def flag(self):
        return self._flag

    def set(self, value):
        if not isinstance(value, bool):
            raise TypeError(f"The type of value:{value} error")
        if self._flag == value:
            return False
        else:
            self._flag = value
            return True

    def on(self):
        self._flag = True

    def off(self):
        self._flag  = False

    def __bool__(self):
        return self._flag

    def __eq__(self, other):
        return self._flag == other.flag

    def __str__(self):
        return f"Switch. Current state:{self._flag}"

    __repr__ = __str__
       

class Number:
    def __init__(self, default=0):
        self._data = default

    @property
    def data(self):
        return self._data

    def set(self, value):
        if not isinstance(value, (int, float)):
            raise TypeError(f"The type of value:{value} error")
        if self._data == value:
            return False
        else:
            self._data = value
            return True

    def __add__(self, other):
        return self._data + other

    def __sub__(self, other):
        return self._data - other

    def __mul__(self, other):
        return self._data * other

    def __truediv__(self, other):
        return self._data / other

    def __iadd__(self, other):
        self._data += other

    def __isub__(self, other):
        self._data -= other

    def __imul__(self, other):
        self._data *= other

    def __itruediv__(self, other):
        self._data /= other

    def __eq__(self, other):
        return self._data == other.data

    def __ne__(self, other):
        return self._data != other.data

    def __lt__(self, other):
        return self._data < other.data

    def __le__(self, other):
        return self._data <= other.data

    def __ge__(self, other):
        return self._data >= other.data

    def __bool__(self):
        return self._data

    def __str__(self):
        return f"Number. Current number:{self._data}"

    __repr__ = __str__
