import os
import sys
import shutil
import paths


def ensure_env_exists():
    """Check if .env exists, create it if not, then exit with error message"""
    env_path = paths.get_data_path('.env')
    
    if not os.path.exists(env_path):
        print("ERROR: .env file not found!")
        print(f"Expected location: {env_path}")
        
        # Create .env with default content
        default_content = """# Telegram Bot Token from @BotFather
BOT_TOKEN=your_bot_token_here

# Web UI admin password
WEBUI_PASSWORD=admin

# Bot access password for users
BOT_ACCESS_PASSWORD=secret

# Session secret key (change in production)
SECRET_KEY=change-me-in-production
"""
        with open(env_path, 'w') as f:
            f.write(default_content)
        print(f"Created .env with default values")
        
        print("\nPlease edit the .env file with your actual values and run the program again.")
        print("Required: Set BOT_TOKEN to your Telegram bot token from @BotFather")
        sys.exit(1)