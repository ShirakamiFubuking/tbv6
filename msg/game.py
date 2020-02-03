from config import bot
import random
from . import msgtools as tools


@bot.message_handler(commands=['roll'])
def roll(message):
    cmd = message.text.split()
    try:
        x = int(cmd[1])
    except (IndexError, TypeError, ValueError):
        x = 20
    rand = random.randint(1, x)
    text = f'在`1-{x}`的roll点中,你掷出了`{rand}`\n本消息将会在5分钟后自动删除'
    msg = bot.send_message(message.chat.id, text, reply_to_message_id=message.message_id, parse_mode='markdown')
    tools.schedule_delete(300, message.chat.id, message.message_id)
    tools.schedule_delete(300, msg.chat.id, msg.message_id)
