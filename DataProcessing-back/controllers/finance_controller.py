from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from models.request_models import MetricsRequest
from services.finance_service import get_metrics_data_from_csv
from pydantic import BaseModel
from typing import Dict

router = APIRouter(prefix="/api/finance", tags=["Finance"])

class MetricsResponse(BaseModel):
    ticker: str
    tickerName: str
    metrics: Dict[str, float | str]

@router.post("/metrics", response_model=MetricsResponse)
async def get_financial_metrics(request: MetricsRequest):
    try:
        data = get_metrics_data_from_csv(request.ticker, request.metrics)
        return {
            "ticker": request.ticker,
            "tickerName": request.tickerName,
            "metrics": data
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": str(e)})
