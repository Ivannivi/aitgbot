# AI Telegram Bot with WebUI

A powerful Telegram bot interface for LM Studio (or compatible OpenAI API endpoints) featuring a WebUI dashboard for user management, role-based access control, and multi-modal (image) support.

## Features

- **Telegram Bot Interface**: Chat with your local LLMs directly from Telegram.
- **Multi-Modal Support**: Send images to the bot to use vision capabilities (requires a vision-capable model loaded in LM Studio).
- **WebUI Dashboard**: Manage users, settings, and models from a clean web interface.
- **Access Control**:
  - **Password Protection**: Users must enter a password or invite code to use the bot.
  - **Invites**: Generate one-time invite codes for users or admins.
  - **Roles**: User, Admin, and Super Admin roles.
- **Admin Commands**: Kick users, manage models, and generate invites directly from Telegram.

## Prerequisites

- **Python 3.8+**
- **LM Studio** (running locally on port 1234, or another OpenAI-compatible API)
- **Telegram Bot Token** (from @BotFather)

## Installation

1. **Clone or Download** this repository.
2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Configure Environment**:
   - Rename `.env.example` to `.env`.
   - Open `.env` and set your variables:
     - `BOT_TOKEN`: Your Telegram Bot Token.
     - `BOT_ACCESS_PASSWORD`: The master password to gain access to the bot.
     - `WEBUI_PASSWORD`: The password for the Web Dashboard (and Super Admin access in the bot).
     - `SECRET_KEY`: A random string for web session security.

## Usage

### Starting the Application

You can start both the Bot and the WebUI with a single command:

- **Windows**: Double-click `start.bat`
- **Linux/Mac**: Run `./start.sh`
- **Manual**: `python main.py`

The WebUI will be available at `http://localhost:7860`.

### First Time Setup

1. Start the bot.
2. Open the WebUI (`http://localhost:7860`).
3. Log in with your `WEBUI_PASSWORD`.
4. Configure your System Prompt and ensure LM Studio URL is correct.

### Telegram Commands

- `/start` - Initialize the bot.
- **Authentication**:
  - Send the `BOT_ACCESS_PASSWORD` to authorize yourself as a **User**.
  - Send an **Invite Code** to authorize yourself.
  - Send the `WEBUI_PASSWORD` to authorize yourself as a **Super Admin**.

#### Admin Commands (Admin/Super Admin only)
- `/users` - List all authorized users.
- `/kick <user_id>` - Remove a user's access (Super Admins cannot be kicked).
- `/deadmin <user_id>` - Remove admin privileges from a user.
- `/invite` - Generate a one-time invite code for a new **User** (expires in 1 hour).
- `/inviteadmin` - Generate a one-time invite code for a new **Admin** (expires in 1 hour).
- `/models` - List available models from LM Studio.
- `/setmodel <model_id>` - Switch the active model.

### Roles Explained

- **User**: Can chat with the AI.
- **Admin**: Can chat, manage users (kick/invite), and change models.
- **Super Admin**: Has all Admin privileges but cannot be kicked or demoted by other admins. Managed via WebUI.

## Vision / Image Support

To use image recognition:
1. Load a vision-capable model in LM Studio (e.g., `llava`, `bakllava`, etc.).
2. Send an image to the bot in Telegram.
3. (Optional) Add a caption to ask a specific question about the image. If no caption is provided, the bot will be asked "What is in this image?".

## Troubleshooting

- **Bot not responding?** Check the console logs. Ensure `BOT_TOKEN` is correct.
- **LLM Error?** Ensure LM Studio is running and the Server is started (default port 1234).
- **Images not working?** Ensure the loaded model supports vision.
