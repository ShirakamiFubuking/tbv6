import json
import subprocess
from pathlib import Path
import requests
from requests.cookies import RequestsCookieJar
import os

from config import logger, bot, const

baidu_headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/"
                  "537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36",
    "Connection": "keep-alive",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.8"}

with Path('./files/baidu_cookies.json').open() as file:
    cookies = json.load(file)
with Path('./files/baidu_params.json').open() as file:
    params = json.load(file)

bdpc = './bin/BaiduPCS-Go mkdir /永久分享用/神社/{baidu_folder} && ' \
       './bin/BaiduPCS-Go mkdir /永久分享用/神社/{baidu_folder}/欢迎加入Telegram补档频道@liuli_link'
bdpu = './bin/BaiduPCS-Go u "{file}" ./files/说明.txt /永久分享用/神社/{baidu_folder} -p 1 --nosplit --norapid'


def jinjia_upload(local_files, name, proxy=None):
    remote_folder = f'/永久分享用/神社/{name}'
    readme = str(Path('./files/说明.txt').absolute())
    bdpc1 = ['./bin/BaiduPCS-Go', 'mkdir', remote_folder]
    bdpc2 = ['./bin/BaiduPCS-Go', 'mkdir', f'{remote_folder}/欢迎加入Telegram补档频道 @liuli_link']
    bdpu = ['./bin/BaiduPCS-Go', 'u', *local_files, remote_folder, '-p', '1', '--nosplit',
            '--norapid']
    bdpu2 = ['./bin/BaiduPCS-Go', 'u', readme, remote_folder, '-p', '1', '--nosplit',
             '--norapid']
    if proxy:
        env_ = dict(os.environ)
        env_['HTTP_PROXY'] = proxy
    else:
        env_ = None
    subprocess.run(bdpc1, check=True, capture_output=True, env=env_)
    subprocess.run(bdpc2, check=True, capture_output=True, env=env_)
    subprocess.run(bdpu, check=True, capture_output=True, env=env_)
    subprocess.run(bdpu2, check=True, capture_output=True, env=env_)
    return remote_folder


def share(path, period=0, pwd=''):
    def join_cookies(func_cookies):
        c = RequestsCookieJar()
        for cookie in func_cookies:
            c.set(cookie['name'], cookie['value'], path=cookie['path'], domain=cookie['domain'])
        return c

    data = {
        "path_list": f'["{path}"]',
        "period": f"{period}",
        "channel_list": "[]",
        "schannel": "4"
    }
    if pwd:
        data['pwd'] = pwd
    session = requests.Session()
    session.cookies.update(join_cookies(cookies))
    r = session.post(
        'https://pan.baidu.com/share/pset', params=params, data=data,
        headers=baidu_headers)
    try:
        r.raise_for_status()
        return r.json()['link']
    except Exception as e:
        logger.warning(e, exc_info=True)
        bot.send_message(const.GOD, '分享出现错误了，还是自己弄一下吧~')

