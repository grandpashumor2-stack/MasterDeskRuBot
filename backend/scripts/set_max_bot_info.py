import sys
sys.path.insert(0, "/app")

import asyncio
from maxapi import Bot
from maxapi.types.attachments.image import PhotoAttachmentRequestPayload

DESCRIPTION = (
    "МастерДеск — виртуальный администратор автосервиса.\n\n"
    "Отвечаю клиентам 24/7: подскажу актуальные цены, запишу на ремонт "
    "и напомню о визите.\n\n"
    "Подключить свой автосервис: https://master-desk.ru/register\n"
    "Мы также в Telegram: @MasterDeskRuBot"
)

AVATAR_URL = "https://master-desk.ru/static/masterdesk_avatar.jpg"


async def main():
    bot = Bot()
    result = await bot.change_info(
        description=DESCRIPTION,
        photo=PhotoAttachmentRequestPayload(url=AVATAR_URL),
    )
    print("OK, обновлено:", result)


if __name__ == "__main__":
    asyncio.run(main())
