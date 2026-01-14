import asyncio
import logging
import multiprocessing
import uvicorn
import os
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def run_web():
    """Runs the FastAPI WebUI"""
    # Change directory to ensure templates/static files are found
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    # Disable duplicate logging setup from uvicorn to avoid conflicts if needed,
    # but simple run is usually fine.
    uvicorn.run("web:app", host="0.0.0.0", port=7860, reload=False)

def run_bot():
    """Runs the Aiogram Bot"""
    # Import here to avoid issues with multiprocessing if imported at top level
    from bot import main as bot_main
    asyncio.run(bot_main())

if __name__ == "__main__":
    # Ensure we are in the correct directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # Create processes
    web_process = multiprocessing.Process(target=run_web, name="WebUI")
    bot_process = multiprocessing.Process(target=run_bot, name="TelegramBot")
    
    try:
        logging.info("Starting WebUI...")
        web_process.start()
        
        logging.info("Starting Bot...")
        bot_process.start()
        
        # Wait for processes to finish (they generally won't unless crashed/stopped)
        web_process.join()
        bot_process.join()
    except KeyboardInterrupt:
        logging.info("Stopping services...")
        web_process.terminate()
        bot_process.terminate()
        web_process.join()
        bot_process.join()
        logging.info("Stopped.")
