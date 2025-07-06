from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, ChatPermissions
from aiogram.filters import Command, CommandObject
from aiogram.enums.chat_member_status import ChatMemberStatus
from aiogram.exceptions import TelegramBadRequest
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from datetime import datetime, timedelta
from contextlib import suppress
import pymorphy3
import re
import asyncio
import logging
proverka_row = ['***', '***', '***']
morph = pymorphy3.MorphAnalyzer()
proverka = set(morph.parse(pr)[0].normal_form for pr in proverka_row) # Приводим каждое слово к его начальной форме

checking = {} # Словарь для хранения предупреждений пользователей
logging.basicConfig(level=logging.INFO)

async def admin(bot, message):
    member = await bot.get_chat_member(message.chat.id, message.from_user.id)
    bot = await bot.get_chat_member(message.chat.id, bot.id)
    if member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR] or bot.status == ChatMemberStatus.ADMINISTRATOR:
        return True
    return False

def get_time(time: str | None):
    if not time:
        return None
    
    re_match = re.match(r"(\d+)([h|d|w|m])", time.lower().strip()) # Проверяем, что заданное время соответствует началу шаблона, например: 5h
    now_datetime = datetime.now()

    if re_match:
        value = int(re_match.group(1))
        unit = re_match.group(2)

        match unit:
            case "h": time_delta = timedelta(hours=value)
            case "d": time_delta = timedelta(days=value)
            case "w": time_delta = timedelta(weeks=value)
            case "m": time_delta = timedelta(days=30*value)
            case _: return None
    else:
        return None
    
    new_datetime = now_datetime + time_delta
    return new_datetime

router = Router()
router.message.filter(F.chat.type == 'supergroup', F.from_user.id == ***)

@router.message(Command('ban'))
async def ban(message: Message, bot: Bot, command: CommandObject):
    reply_message = message.reply_to_message
    if not await admin(bot, message):
        await message.reply('<b>Ошибка: у вас нет прав для мута!</b>')
    if not reply_message or not reply_message.from_user:
        await message.reply('<b>Ошибка: используйте команду в ответ на сообщение пользователя, которого хотите замутить!</b>')
    date = await get_time(command.args.strip() if command.args else None)
    if date is None:
        await message.reply('Ошибка: укажите корректный промежуток времени для бана (например, 1d, 5h, 2w)')
        return
    with suppress(TelegramBadRequest):
        await bot.ban_chat_member(chat_id=message.chat.id, user_id=reply_message.from_user.id, until_date=date)
        await message.answer('Пользователь успешно заблокирован!')

@router.message(Command('unban'))
async def unban(message: Message, bot: Bot):
    reply_message = message.reply_to_message
    if not await admin(bot, message):
        await message.reply('<b>Ошибка: у вас нет прав для мута!</b>')
    if not reply_message or not reply_message.from_user:
        await message.reply('<b>Ошибка: используйте команду в ответ на сообщение пользователя, которого хотите замутить!</b>')
    await bot.unban_chat_member(chat_id=message.chat.id, user_id=reply_message.from_user.id)
    await message.answer('Блокировка с пользователя была успешно снята!')

@router.message(Command("mute"))
async def func_mute(message: Message, bot: Bot, command: CommandObject):
    reply_message = message.reply_to_message
    
    if not reply_message or not await admin(bot, message):
        await message.reply("<b>❌  Произошла ошибка!</b>")
        return
    
    date = get_time(command.args.strip() if command.args else None)
    with suppress(TelegramBadRequest):
        await bot.restrict_chat_member(chat_id=message.chat.id, user_id=reply_message.from_user.id, until_date=date, permissions=ChatPermissions(can_send_messages=False, can_send_other_messages=False))
        await message.answer(f"🔇 Пользователь был заглушен!")

@router.message(Command('unmute'))
async def unmute(message: Message, bot: Bot):
    reply_message = message.reply_to_message
    if not await admin(bot, message):
        await message.reply('<b>Ошибка: у вас нет прав для мута!</b>')
    if not reply_message or not reply_message.from_user:
        await message.reply('<b>Ошибка: используйте команду в ответ на сообщение пользователя, которого хотите замутить!</b>')
    await bot.restrict_chat_member(
        chat_id=message.chat.id,
        user_id=reply_message.from_user.id,
        permissions=ChatPermissions(
            can_send_messages=True, can_send_other_messages=True
        )
    )
    await message.answer('Пользователь успешно размучен!')

@router.message(F.text)
async def check(message: Message, bot: Bot):
    if not message.text or not message.from_user:
        return
    user_id = message.from_user.id
    try:
        for msg in message.text.lower().strip().split(): # Проверяем каждое слово сообщения

            norm_word = morph.parse(msg)[0].normal_form
            if norm_word in proverka:
                checking[user_id] = checking.get(user_id, 0) + 1
                check = checking[user_id]
                if check < 3:
                    await message.reply(f'Ругательства запрещены. Предупреждение {check}/3')
                else:
                    checking[user_id] = 0
                    date = datetime.now() + timedelta(weeks=1)
                    with suppress(TelegramBadRequest): # Для игнора ошибок Telegram, чтобы бот не ломался
                        await bot.restrict_chat_member(
                            chat_id=message.chat.id,
                            user_id=user_id,
                            until_date=date,
                            permissions=ChatPermissions(can_send_messages=False)
                        )
                        await message.reply('Вы получили 3 предупреждения и были замучены на неделю!')
                break  # Только одно предупреждение за сообщение
    except Exception as e:
        print(f'Произошла ошибка при обработке текста: {e}')
async def main():
    bot = Bot(token='***', default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_router(router)
    await bot.delete_webhook(True)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
