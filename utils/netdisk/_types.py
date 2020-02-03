import json


class ShareLink:
    def __init__(self, field, path, share_link, other_info=None):
        self.field = field  # type:str
        self.path = path  # type:str
        self.link = share_link  # type:str
        self.other_info = other_info  # type:dict

    @staticmethod
    def db_query(table_name="NetDiskShare") -> str:
        return f"insert into {table_name} (remote, path, shareLink, otherInfo) VALUES (?,?,?,?)"

    @property
    def db_params(self) -> tuple:
        if self.other_info:
            other_info = json.dumps(self.other_info)
        else:
            other_info = None
        return self.field, self.path, self.link, other_info

    def __str__(self):
        return (f"网盘{self.field}\n"
                f"链接{self.link}\n"
                f"路径{self.path}")

    def __repr__(self):
        return f"{self.field}网盘分享链接{self.link[:10]}..."
