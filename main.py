from config import bot
from msg import game, groupmaster, liuli, onedrive, programmaster, qbitmsg, searchmsg

if __name__ == '__main__':
    bot.polling(none_stop=True, timeout=180)
# import msg,json,io
# f = io.StringIO()
# f.name = "torrents.json"
# json.dump(msg.qbitmsg.qb.client.get_torrent_files("67bdaeda02ef1dab6d7db42bb4572a75d9cb86bc"),f)
# f.seek(0)
# bot.send_document(message.chat.id,f)
from config import  qb
qb.pause_all()