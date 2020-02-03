import traceback
from config import const, autobackup, bot
from config.admins import check


@bot.message_handler(commands=['backupnow'], func=check(100))
def backup_database_now(message):
    autobackup.event.set()
    bot.send_message(message.chat.id, "启动立即备份数据库")


@bot.message_handler(commands=['handler'], func=check(100))
def check_handler(message):
    bot.send_message(message.chat.id, str(bot.message_handlers))


@bot.message_handler(commands=['group'], func=lambda msg: msg.chat.type == "private" and check(80)(msg))
def send_group_message(message):
    bot.send_message(const.GROUP, message.text[7:])


@bot.message_handler(commands=['exec'], func=check(100))
def remote_exec(message):
    command = message.text[6:]
    try:
        exec(command)
    except Exception as exc:
        bot.send_message(message.chat.id, traceback.format_exc(), reply_to_message_id=message.message_id)
    else:
        bot.send_message(message.chat.id, '执行成功', reply_to_message_id=message.message_id)
