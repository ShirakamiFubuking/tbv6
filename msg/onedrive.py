from config.admins import check
from net import upload
from utils import qbit
from . import qbitmsg
from config import bot
import shlex


def _up2od(path):
    def _up2od_wrap(tm):
        up = upload.Upload(path)
        up.general_upload(tm.torrent['save_path'] + tm.torrent['name'],"od", path)

    return _up2od_wrap


@bot.message_handler(commands=['od'],func=check(100))
def up2od(message):
    magnets = qbit.search_hash(message.text)
    if not magnets:
        bot.send_message(message.chat.id, "没有找到磁力链接,请检查消息")
    cmd = shlex.split(message.text)
    od_path = 'od:/默认上传路径'
    for opword in cmd:
        if opword.startswith('od:'):
            od_path = opword[3:]
    for magnet in magnets:
        qbitmsg.qm.add(magnet, message.chat.id, message.from_user.id, funcs=[_up2od(od_path)])
