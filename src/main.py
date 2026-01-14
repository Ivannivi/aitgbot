import asyncio
import logging
import multiprocessing
import os
import sys
import uvicorn
import secrets
import string

import paths
import db

def generate_random_password(length=12):
    """Generate a random password with letters, digits, and some special characters"""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    password = ''.join(secrets.choice(alphabet) for _ in range(length))
    return password

def setup_first_run():
    """Setup configuration on first run"""
    webui_password = db.get_config('webui_password', None)
    
    if webui_password is None:
        # First run - generate random password
        random_password = generate_random_password()
        db.set_config('webui_password', random_password)
        
        print("=" * 60)
        print("🎉 AITG Bot - First Run Setup Complete!")
        print("=" * 60)
        print(f"Web UI Password: {random_password}")
        print("Web UI URL: http://localhost:7860")
        print()
        print("⚠️  IMPORTANT: Save this password! You'll need it to access the web UI.")
        print("   You can change it later in the App Settings.")
        print()
        print("📝 Next Steps:")
        print("   1. Go to http://localhost:7860")
        print("   2. Login with the password above")
        print("   3. Click 'App Settings' to configure your bot token")
        print("=" * 60)
        print()

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

    # Setup first run configuration
    setup_first_run()

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
