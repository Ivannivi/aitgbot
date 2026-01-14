import asyncio
import logging
import os
import base64
import io
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Command

import db
import paths
from services import get_router
from services.base import Message

logger = logging.getLogger(__name__)

# Get config from database
TOKEN = db.get_config('bot_token', '')
if not TOKEN:
    raise ValueError("BOT_TOKEN not configured. Please set it in the web UI at http://localhost:7860")

WEBUI_PASSWORD = db.get_config('webui_password', 'admin')

dp = Dispatcher()
bot = Bot(token=TOKEN)


def get_access_password():
    return db.get_config('access_password', 'secret')

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
    
    router = get_router()
    current_provider = db.get_config('ai_provider', 'lm_studio')
    router.set_current_provider(current_provider)
    
    # Configure providers based on saved settings
    lm_studio_url = db.get_config('lm_studio_url', 'http://127.0.0.1:1234/v1')
    ollama_url = db.get_config('ollama_url', 'http://127.0.0.1:11434')
    
    router.configure_provider('lm_studio', base_url=lm_studio_url)
    router.configure_provider('ollama', base_url=ollama_url)
    
    try:
        models_list = await router.list_models()
        text = f"Available Models ({current_provider.replace('_', ' ').title()}):\n"
        current = db.get_config('model')
        for m in models_list:
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

    model_name = db.get_config('model', 'local-model')
    system_prompt = db.get_config('system_prompt', 'You are a helpful assistant.')
    current_provider = db.get_config('ai_provider', 'lm_studio')
    
    router = get_router()
    router.set_current_provider(current_provider)
    
    # Configure providers based on saved settings
    lm_studio_url = db.get_config('lm_studio_url', 'http://127.0.0.1:1234/v1')
    ollama_url = db.get_config('ollama_url', 'http://127.0.0.1:11434')
    
    router.configure_provider('lm_studio', base_url=lm_studio_url)
    router.configure_provider('ollama', base_url=ollama_url)

    await bot.send_chat_action(chat_id=message.chat.id, action="typing")

    try:
        messages = [Message(role="system", content=str(system_prompt))]

        if message.photo:
            photo = message.photo[-1]
            file_io = io.BytesIO()
            await bot.download(photo, destination=file_io)
            file_io.seek(0)
            base64_image = base64.b64encode(file_io.getvalue()).decode('utf-8')
            user_content = [
                {"type": "text", "text": text or "What is in this image?"},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
            ]
            messages.append(Message(role="user", content=user_content))
        else:
            messages.append(Message(role="user", content=text))

        response = await router.chat(messages, model=model_name)
        await message.answer(response.text or "Empty response from AI.")
    except Exception as e:
        logger.exception("AI request failed")
        await message.answer(f"Error: {e}")

async def main():
    logger.info("Starting bot...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
