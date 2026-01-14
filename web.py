import os
import logging
import requests
from fastapi import FastAPI, Request, Form, Depends, HTTPException, status
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from dotenv import load_dotenv
import db

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

app = FastAPI()

# Session for simple auth
SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-key-change-me")
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))

WEBUI_PASSWORD = os.getenv("WEBUI_PASSWORD", "admin")

def is_authenticated(request: Request):
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
    
    # Fetch data
    users = db.get_users()
    
    # Configs
    access_password = db.get_config("access_password") or os.getenv("BOT_ACCESS_PASSWORD", "secret")
    current_model = db.get_config("model", "local-model")
    system_prompt = db.get_config("system_prompt", "You are a helpful assistant.")
    lm_studio_url = db.get_config("lm_studio_url", "http://localhost:1234/v1")
    
    # Fetch models from LM Studio
    models = []
    try:
        # Construct models URL from base URL
        models_url = f"{lm_studio_url.rstrip('/')}/models"
        r = requests.get(models_url, timeout=2)
        if r.status_code == 200:
            data = r.json()
            models = data.get("data", [])
    except Exception as e:
        logging.error(f"Failed to fetch models: {e}")
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "users": users,
        "models": models,
        "current_model": current_model,
        "system_prompt": system_prompt,
        "access_password": access_password,
        "lm_studio_url": lm_studio_url
    })

@app.post("/update_config")
async def update_config(request: Request, access_password: str = Form(...), model: str = Form(...), system_prompt: str = Form(...), lm_studio_url: str = Form(...)):
    if not is_authenticated(request):
        return RedirectResponse(url="/")
    
    db.set_config("access_password", access_password)
    db.set_config("model", model)
    db.set_config("system_prompt", system_prompt)
    db.set_config("lm_studio_url", lm_studio_url)
    
    return RedirectResponse(url="/dashboard", status_code=303)

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
    # Change cwd to directory of script so templates load correctly
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    # Port 8080 might be restricted or in use. Using 7860.
    uvicorn.run("web:app", host="0.0.0.0", port=7860, reload=True)
