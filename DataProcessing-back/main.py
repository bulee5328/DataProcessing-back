from fastapi import FastAPI
from controllers.finance_controller import router as finance_router

app = FastAPI(title="Financial Metrics API")

app.include_router(finance_router)

@app.get("/")
def root():
    return {"message": "Financial Metrics API Running 🚀"}
