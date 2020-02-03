import configparser
import os
import subprocess
from datetime import datetime
import requests
import json
import time

from .errors import ShareError
from . import gdrive, errors
from ._types import ShareLink


def quote(text: str, escape_chars='\\', safe_chars='/'):
    del_chars = "\""
    for dc in del_chars:
        text = text.replace(dc, "")
    if len(escape_chars) != len(safe_chars):
        raise ValueError("转义字符与安全字符数量不等！")
    for ec, sc in zip(escape_chars, safe_chars):
        text = text.replace(ec, sc)

    return text


def od_quote(text):
    od_escape_chars = '#%*:<>?|\\'
    od_safe_chars = '＃％＊：＜＞？｜/'
    return quote(text, od_escape_chars, od_safe_chars)


def od_share(path, remote, proxy):
    headers = {"Authorization": json.loads(remote['token'])['access_token']}
    res = requests.post(f"https://graph.microsoft.com/v1.0/me/drive/root:/{path}:/createLink",
                        json={"type": "view"},
                        headers=headers,
                        proxies=proxy)
    res.raise_for_status()
    return res


def gd_share(fileid, remote, proxy):
    params = None
    if 'team_drive' in remote:
        params = {"supportsTeamDrives": True,
                  "supportsAllDrives": True}
    token = json.loads(remote['token'])
    headers = {"Authorization": "{} {}".format(token['token_type'], token['access_token'])}
    res = requests.post(f"https://www.googleapis.com/drive/v3/files/{fileid}/permissions",
                        params=params,
                        json={"role": "reader",
                              "type": "anyone"},
                        headers=headers,
                        proxies=proxy)
    res.raise_for_status()
    return res


def is_expiry(fmt):
    def _custom_tz(fmt):
        h, m = int(fmt[1:3]), int(fmt[4:6])
        tz_s = 3600 * h + 60 * m
        if fmt[0] == '+':
            tz_s = -tz_s
        return tz_s

    lo_timestamp = datetime.strptime(fmt[:19], "%Y-%m-%dT%H:%M:%S").timestamp() + _custom_tz(fmt[-6:])
    return time.time() > lo_timestamp - 180


class Rclone:
    def __init__(self, bin_path="rclone", config_path=None, proxy=None):
        self.bin_path = bin_path  # type:str
        self.config = config_path  # type:str
        self.proxy = proxy  # type:dict

    def check_expiry(self, filed):
        conf = configparser.ConfigParser()
        conf.read(self.config)
        if filed not in conf:
            raise ValueError("远程名称没有在rclone配置文件中找到!")
        fmt = json.loads(conf[filed]['token'])['expiry']
        if is_expiry(fmt):
            conf.read(self.config)
            self._exe_bin([self.bin_path, f"--config={self.config}", 'lsf', f"{filed}:"])
            new_conf = configparser.ConfigParser()
            new_conf.read(self.config)
            return new_conf[filed]
        return conf[filed]

    def _exe_bin(self, cmd) -> subprocess.CompletedProcess:
        env = dict(os.environ)
        if self.proxy is not None:
            env.update({"HTTP_PROXY": self.proxy['http']})
        return subprocess.run(cmd, check=True, capture_output=True, env=env)

    def general_upload(self, local_path, field, remote_path):
        cmd = [self.bin_path, 'copy', local_path, f'{field}:{remote_path}', f"--config={self.config}"]
        self._exe_bin(cmd)
        return cmd

    def gd_get_fileid_by_path(self, path: str, conf):
        gd = gdrive.GDrive(conf, self.proxy)
        path = path.lstrip('/')
        return gd.get_by_full_path(path)

    def share_by_py(self, field, path) -> ShareLink:
        remote = self.check_expiry(field)
        if remote['type'] == 'drive':
            fileid = self.gd_get_fileid_by_path(path, remote)
            res = gd_share(fileid, remote, self.proxy)
            other_info = res.json()
            other_info.update({"fileId": fileid})
            return ShareLink(field, path, f"https://drive.google.com/open?id={fileid}", other_info)
        elif remote['type'] == 'onedrive':
            path = od_quote(path)
            res = od_share(path, remote, self.proxy)
            link = ShareLink(field, path, res.json()['link']['webUrl'], res.json())
            return link
        else:
            raise ShareError(path, field, remote['type'])

    def share(self, field, path) -> ShareLink:
        cmd = [self.bin_path, 'link', f'--config={self.config}', f"{field}:{path}"]
        res = self._exe_bin(cmd)
        link = res.stdout.decode('utf-8').strip()
        return ShareLink(field, path, link)


if __name__ == '__main__':
    pass
