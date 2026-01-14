import asyncio
import logging
import os
import base64
import io
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from openai import AsyncOpenAI
from dotenv import load_dotenv
import db

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

TOKEN = os.getenv("BOT_TOKEN", "").strip()
if not TOKEN:
    raise ValueError("BOT_TOKEN is not set in .env file")

print(f"Loaded Token: {TOKEN[:5]}...{TOKEN[-5:]} (Check if this matches your BotFather token)")

# Initialize Bot and Dispatcher
dp = Dispatcher()
bot = Bot(token=TOKEN)

WEBUI_PASSWORD = os.getenv("WEBUI_PASSWORD", "admin")

def get_access_password():
    # Priority: DB -> Env -> Default
    pwd = db.get_config('access_password')
    if pwd:
        return pwd
    return os.getenv('BOT_ACCESS_PASSWORD', 'secret')

@dp.message(CommandStart())
async def command_start_handler(message: types.Message):
    if not message.from_user:
        return
    if db.is_user_authorized(message.from_user.id):
        await message.answer("Welcome back! I am ready to chat.")
    else:
        await message.answer("Welcome! This bot is password protected. Please enter the access password.")

@dp.message(Command("users"))
async def list_users(message: types.Message):
    if not message.from_user or not db.is_user_admin(message.from_user.id):
        return
    users = db.get_users()
    text = "Authorized Users:\n"
    for u in users:
        admin_tag = ""
        if u.get('is_super_admin'):
            admin_tag = " (Super Admin)"
        elif u.get('is_admin'):
            admin_tag = " (Admin)"
        text += f"- {u['username']} (ID: {u['user_id']}){admin_tag}\n"
    await message.answer(text)

@dp.message(Command("kick"))
async def kick_user(message: types.Message):
    if not message.from_user or not db.is_user_admin(message.from_user.id):
        return
    if not message.text:
        return
    try:
        args = message.text.split()
        if len(args) < 2:
            await message.answer("Usage: /kick <user_id>")
            return
        target_id = int(args[1])
        if db.is_user_super_admin(target_id):
            await message.answer("Cannot kick a Super Admin.")
            return
        
        if db.remove_user(target_id):
            await message.answer(f"User {target_id} kicked out.")
        else:
            await message.answer("Failed to kick user.")
    except ValueError:
        await message.answer("Invalid user ID.")

@dp.message(Command("deadmin"))
async def deadmin_user(message: types.Message):
    if not message.from_user or not db.is_user_admin(message.from_user.id):
        return
    if not message.text:
        return
    try:
        args = message.text.split()
        if len(args) < 2:
            await message.answer("Usage: /deadmin <user_id>")
            return
        target_id = int(args[1])
        
        if db.make_admin(target_id, is_admin=False):
            await message.answer(f"User {target_id} is no longer an admin.")
        else:
            await message.answer("Failed: Cannot remove admin privileges from a Super Admin.")
    except ValueError:
        await message.answer("Invalid user ID.")

@dp.message(Command("invite"))
async def generate_invite(message: types.Message):
    if not message.from_user or not db.is_user_admin(message.from_user.id):
        return
    code = db.create_invite(is_admin_invite=False)
    await message.answer(f"Generated One-Time Password (User): `{code}`", parse_mode="Markdown")

@dp.message(Command("inviteadmin"))
async def generate_admin_invite(message: types.Message):
    if not message.from_user or not db.is_user_admin(message.from_user.id):
        return
    code = db.create_invite(is_admin_invite=True)
    await message.answer(f"Generated One-Time Password (Admin): `{code}`", parse_mode="Markdown")

@dp.message(Command("models"))
async def list_models(message: types.Message):
    if not message.from_user or not db.is_user_admin(message.from_user.id):
        return
    
    lm_studio_url = db.get_config('lm_studio_url', 'http://127.0.0.1:1234/v1')
    client = AsyncOpenAI(base_url=lm_studio_url, api_key="lm-studio")
    try:
        models_list = await client.models.list()
        text = "Available Models:\n"
        current = db.get_config('model')
        for m in models_list.data:
            mark = " [CURRENT]" if m.id == current else ""
            text += f"- `{m.id}`{mark}\n"
        await message.answer(text, parse_mode="Markdown")
    except Exception as e:
        await message.answer(f"Error fetching models: {e}")

@dp.message(Command("setmodel"))
async def set_model(message: types.Message):
    if not message.from_user or not db.is_user_admin(message.from_user.id):
        return
    if not message.text:
        return
    try:
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            await message.answer("Usage: /setmodel <model_id>")
            return
        model_id = parts[1].strip()
        db.set_config('model', model_id)
        await message.answer(f"Model set to: {model_id}")
    except Exception as e:
        await message.answer(f"Error: {e}")

@dp.message()
async def chat_handler(message: types.Message):
    text = message.text or message.caption
    
    if not message.from_user:
        return

    # Allow authorized users to send images without text
    if not text and not (message.photo and db.is_user_authorized(message.from_user.id)):
        return
        
    if not text:
        text = ""

    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name or "Unknown"
    
    if not db.is_user_authorized(user_id):
        if text == get_access_password():
            db.add_user(user_id, username, is_admin=False)
            await message.answer("Password accepted! You are now authorized to use this bot.")
        elif text == WEBUI_PASSWORD:
            db.add_user(user_id, username, is_admin=True)
            await message.answer("Admin Access Granted! You can now control models and users.")
        else:
            invite_result = db.use_invite(text)
            if invite_result and invite_result["success"]:
                is_admin = invite_result["is_admin"]
                db.add_user(user_id, username, is_admin=is_admin)
                role_msg = "Admin Access Granted!" if is_admin else "Invite accepted!"
                await message.answer(f"{role_msg} You are now authorized to use this bot.")
            else:
                await message.answer("Access denied. Please enter the correct password.")
        return

    # User is authorized
    # Check for admin promotion
    if text == WEBUI_PASSWORD:
        db.make_admin(user_id)
        await message.answer("You are now an admin.")
        return

    # User is authorized, send to LM Studio
    model_name = db.get_config('model', 'local-model')
    system_prompt = db.get_config('system_prompt', 'You are a helpful assistant.')
    lm_studio_url = db.get_config('lm_studio_url', 'http://127.0.0.1:1234/v1')

    # Initialize OpenAI client for LM Studio (using dynamic URL)
    client = AsyncOpenAI(base_url=lm_studio_url, api_key="lm-studio")
    
    # Notify user that we are thinking (optional, but good UX)
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    
    try:
        logging.info(f"Sending request to LM Studio ({lm_studio_url}) with model {model_name}...")
        
        messages = [{"role": "system", "content": str(system_prompt)}]
        
        if message.photo:
            # Get the largest photo
            photo = message.photo[-1]
            logging.info(f"Processing image: {photo.file_id}")
            
            # Download photo to memory
            file_io = io.BytesIO()
            await bot.download(photo, destination=file_io)
            file_io.seek(0)
            
            # Encode to base64
            base64_image = base64.b64encode(file_io.getvalue()).decode('utf-8')
            
            user_content = [
                {"type": "text", "text": str(text) if text else "What is in this image?"},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{base64_image}"
                    }
                }
            ]
            messages.append({"role": "user", "content": user_content})
        else:
            messages.append({"role": "user", "content": str(text)})

        completion = await client.chat.completions.create(
            model=model_name,
            messages=messages
        )
        logging.info("Received response from LM Studio")
        response_text = completion.choices[0].message.content
        if response_text:
            await message.answer(response_text)
        else:
            await message.answer("LM Studio returned an empty response.")
    except Exception as e:
        logging.error(f"LM Studio Error: {e}")
        await message.answer(f"Error communicating with LM Studio. Is it running on port 1234?\nError: {e}")

async def main():
    logging.info("Starting bot polling...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
