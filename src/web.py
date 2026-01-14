import os
import logging
import requests
from fastapi import FastAPI, Request, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

import db
import paths
from services import get_router
from services import get_router

logger = logging.getLogger(__name__)

app = FastAPI()

# Get config from database  
SECRET_KEY = db.get_config('secret_key', 'change-me-in-production')
WEBUI_PASSWORD = db.get_config('webui_password', 'admin')

app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

templates = Jinja2Templates(directory=paths.get_resource_path("templates"))


def is_authenticated(request: Request) -> bool:
    return request.session.get("authenticated") is True


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    if is_authenticated(request):
        return RedirectResponse(url="/dashboard")
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/login", response_class=HTMLResponse)
async def login(request: Request, password: str = Form(...)):
    if password == WEBUI_PASSWORD:
        request.session["authenticated"] = True
        return RedirectResponse(url="/dashboard", status_code=303)
    return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid Password"})


@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/")


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    if not is_authenticated(request):
        return RedirectResponse(url="/")

    router = get_router()
    current_provider = db.get_config("ai_provider", "lm_studio")
    
    # Configure the router's current provider
    router.set_current_provider(current_provider)
    
    # Configure providers based on saved settings
    lm_studio_url = db.get_config("lm_studio_url", "http://127.0.0.1:1234/v1")
    ollama_url = db.get_config("ollama_url", "http://127.0.0.1:11434")
    
    router.configure_provider("lm_studio", base_url=lm_studio_url)
    router.configure_provider("ollama", base_url=ollama_url)
    
    # Get models from current provider
    try:
        models = await router.list_models(current_provider)
    except Exception as e:
        logger.warning(f"Could not fetch models from {current_provider}: {e}")
        models = []
    
    users = db.get_users()
    access_password = db.get_config("access_password", "secret")
    current_model = db.get_config("model", "local-model")
    system_prompt = db.get_config("system_prompt", "You are a helpful assistant.")

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "users": users,
        "models": models,
        "current_model": current_model,
        "current_provider": current_provider,
        "system_prompt": system_prompt,
        "access_password": access_password,
        "lm_studio_url": lm_studio_url,
        "ollama_url": ollama_url,
        "providers": router.list_providers()
    })

@app.post("/update_config")
async def update_config(
    request: Request,
    ai_provider: str = Form(...),
    access_password: str = Form(...),
    model: str = Form(...),
    system_prompt: str = Form(...),
    lm_studio_url: str = Form(...),
    ollama_url: str = Form(...)
):
    if not is_authenticated(request):
        return RedirectResponse(url="/")
    
    db.set_config("ai_provider", ai_provider)
    db.set_config("access_password", access_password)
    db.set_config("model", model)
    db.set_config("system_prompt", system_prompt)
    db.set_config("lm_studio_url", lm_studio_url)
    db.set_config("ollama_url", ollama_url)
    
    return RedirectResponse(url="/dashboard", status_code=303)


@app.get("/settings")
async def settings(request: Request):
    if not is_authenticated(request):
        return RedirectResponse(url="/")
    
    config = {
        'bot_token': db.get_config('bot_token', ''),
        'webui_password': db.get_config('webui_password', 'admin'),
        'secret_key': db.get_config('secret_key', 'change-me-in-production'),
        'access_password': db.get_config('access_password', 'secret')
    }
    
    return templates.TemplateResponse("settings.html", {
        "request": request, 
        "config": config
    })


@app.post("/update_app_config")
async def update_app_config(
    request: Request,
    bot_token: str = Form(...),
    webui_password: str = Form(...),
    secret_key: str = Form(...),
    access_password: str = Form(...)
):
    if not is_authenticated(request):
        return RedirectResponse(url="/")
    
    # Update configurations in database
    db.set_config("bot_token", bot_token.strip())
    db.set_config("webui_password", webui_password)
    db.set_config("secret_key", secret_key)
    db.set_config("access_password", access_password)
    
    return RedirectResponse(url="/settings?saved=1", status_code=303)


@app.post("/add_user")
async def add_user(request: Request, user_id: int = Form(...), username: str = Form(None)):
    if not is_authenticated(request):
        return RedirectResponse(url="/")
    db.add_user(user_id, username or "Manual")
    return RedirectResponse(url="/dashboard", status_code=303)


@app.post("/delete_user")
async def delete_user(request: Request, user_id: int = Form(...)):
    if not is_authenticated(request):
        return RedirectResponse(url="/")
    db.remove_user(user_id)
    return RedirectResponse(url="/dashboard", status_code=303)


@app.post("/toggle_super_admin")
async def toggle_super_admin(request: Request, user_id: int = Form(...), is_super: bool = Form(False)):
    if not is_authenticated(request):
        return RedirectResponse(url="/")
    db.make_super_admin(user_id, is_super)
    return RedirectResponse(url="/dashboard", status_code=303)


if __name__ == "__main__":
    import uvicorn
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    uvicorn.run("web:app", host="0.0.0.0", port=7860, reload=True)
