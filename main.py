from config import bot
from msg import game, groupmaster, liuli, onedrive, programmaster, qbitmsg, searchmsg

if __name__ == '__main__':
    bot.polling(none_stop=True, timeout=180)
