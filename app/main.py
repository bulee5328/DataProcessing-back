from fastapi import FastAPI
from controllers.finance_controller import router as finance_router

app = FastAPI(title="Financial Metrics API")

app.include_router(finance_router)

# @app.get("/")
# def root():
#     return {"message": "Financial Metrics API Running 🚀"}

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app.mount("/static", StaticFiles(directory="static"), name="static")

# ✅ HTML 템플릿 (Jinja2 사용)
templates = Jinja2Templates(directory="templates")

# ✅ 기본 라우트: index.html 전송
@app.get("/", response_class=HTMLResponse)
def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})