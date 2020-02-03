from pathlib import Path

encode_dict = {}
from collections import OrderedDict


class BDict:
    pass


class BList:
    pass


class BInt:
    pass


class BString:
    pass


class Obj:
    def __init__(self, data, pos):

        if isinstance(data, bytes):
            self._data = data
            self._type = 's'
        elif isinstance(data, int):
            self._data = data
            self._type = 'i'
        elif isinstance(data, OrderedDict):
            self._data = data
            self._type = 'd'
        elif isinstance(data, list):
            self._data = data
            self._type = 'l'
        else:
            raise Exception
        self._pos = pos

    def __new__(cls, *args, **kwargs):
        pass

    @property
    def data(self):
        return self._data

    def __getitem__(self, item):
        return self.data[item]

    @property
    def pos(self):
        return slice(self._pos)

    def __hash__(self):
        if self._type == 's':
            return hash(self._data)
        else:
            raise

    def __eq__(self, other):
        if self._data == other:
            return True
        return False

    def __str__(self):
        return str(self._data)

    __repr__ = __str__


class Decoder:
    dict = b'd'
    list = b'l'
    int = b'i'
    str = b'0123456789'
    end = b'e'

    def __init__(self, content):
        self.content = content
        self.offset = 0
        encode_dict[content] = None
        self.encoding = None

    def main_dc(self):
        if self.content[self.offset] in self.dict:
            return self.dc_dict()
        elif self.content[self.offset] in self.list:
            return self.dc_list()
        elif self.content[self.offset] in self.str:
            return self.dc_str()
        elif self.content[self.offset] in self.int:
            return self.dc_int()

    def dc_int(self):
        start = self.offset
        self.offset += 1
        int_list = []
        while self.content[self.offset] != 101:  # b'e':
            int_list.append(chr(self.content[self.offset]))
            self.offset += 1
        self.offset += 1
        return Obj(int(''.join(int_list)), (start, self.offset))

    def dc_str(self):
        start = self.offset
        str_len_list = []
        while self.content[self.offset] != 58:  # b':':
            str_len_list.append(chr(self.content[self.offset]))
            self.offset += 1

        self.offset += 1
        str_len = int(''.join(str_len_list))
        self.offset += str_len
        import chardet
        # res  =chardet.detect(self.content[self.offset - str_len:self.offset])
        # print(res)
        # print(self.content[self.offset - str_len:self.offset].decode('utf-8-sig', errors='ignore'))
        return Obj(self.content[self.offset - str_len:self.offset], (start, self.offset))

    def dc_dict(self):
        start = self.offset
        self.offset += 1
        temp = OrderedDict()
        while self.content[self.offset] != 101:  # b'e':
            key = self.main_dc()
            value = self.main_dc()
            temp[key] = value

        self.offset += 1
        if self.encoding is None:
            encoding = temp.get(b'encoding')
            if encoding:
                encode_dict[self.content] = encoding
                self.encoding = encoding
        return Obj(temp, (start, self.offset))

    def dc_list(self):
        start = self.offset
        self.offset += 1
        temp = []
        while self.content[self.offset] != 101:  # b'e':
            temp.append(self.main_dc())
        self.offset += 1
        return Obj(temp, (start, self.offset))


if __name__ == '__main__':
    pass
