import asyncio
import logging
import multiprocessing
import os
import sys
import uvicorn

import paths

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_web():
    src_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, src_dir)
    os.chdir(paths.get_base_path())
    from web import app
    uvicorn.run(app, host="0.0.0.0", port=7860, reload=False)


def run_bot():
    src_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, src_dir)
    os.chdir(paths.get_base_path())
    from bot import main as bot_main
    asyncio.run(bot_main())


if __name__ == "__main__":
    multiprocessing.freeze_support()

    if len(sys.argv) > 1 and sys.argv[1] in ('-v', '--version'):
        from version import print_version_info
        print_version_info()
        sys.exit(0)

    os.chdir(paths.get_base_path())

    web_process = multiprocessing.Process(target=run_web, name="WebUI")
    bot_process = multiprocessing.Process(target=run_bot, name="TelegramBot")

    try:
        logger.info("Starting WebUI...")
        web_process.start()
        logger.info("Starting Bot...")
        bot_process.start()
        web_process.join()
        bot_process.join()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        web_process.terminate()
        bot_process.terminate()
        web_process.join()
        bot_process.join()
