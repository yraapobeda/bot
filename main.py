import asyncio
import importlib
import subprocess
import sys
import os
from aiogram import Bot, Dispatcher
from bot import load_config

from commands.users.start import GroupGuardMiddleware
from commands.admins.subscription import SubscriptionMiddleware
from commands.admins.baned import BanMiddleware

# ============================================================
AUTO_INSTALL_REQ = False  #!True - автоустановка зависимостей \ False - отключено
# ============================================================


def install_requirements():
    if not AUTO_INSTALL_REQ:
        return

    req_file = os.path.join(os.path.dirname(__file__), "requirements.txt")
    if not os.path.exists(req_file):
        print("⚠️ Файл requirements.txt не найден!")
        return

    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", req_file, "-q", "--disable-pip-version-check"],
            check=True
        )
        print("✅ Проверка зависимостей завершена.")
    except subprocess.CalledProcessError:
        print("⚠️ Не удалось установить зависимости.")


HANDLER_PATHS = [
#============================================================
    "commands.users.start",
    "commands.users.proful",
    "commands.users.shlaf",
    "commands.admins.give",
    "commands.admins.admin_ponel",
    "commands.admins.subscription",
    "commands.users.pay",
    "commands.users.random_gifts",
    "commands.admins.mailing",
    "commands.admins.baned",
    
#----------
    
#----------
    
#===========================================================
    
#==========================================================
]  


async def register_handlers(dp: Dispatcher):
    for path in HANDLER_PATHS:
        module = importlib.import_module(path)
        if hasattr(module, "router"):
            dp.include_router(module.router)


async def main():
    install_requirements()

    config = load_config()
    bot = Bot(token=config.bot_token)
    dp = Dispatcher()

    dp.message.middleware(GroupGuardMiddleware())
    dp.callback_query.middleware(GroupGuardMiddleware())
    dp.message.middleware(SubscriptionMiddleware())

    dp.message.outer_middleware(BanMiddleware())
    dp.callback_query.outer_middleware(BanMiddleware())



    await register_handlers(dp)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)



if __name__ == "__main__":
    print("✅ Bot started successfully.")
    asyncio.run(main())