from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from models.request_models import MetricsRequest
from services.finance_service import get_metrics_data_from_csv, makeFactor, makePortpolio
from pydantic import BaseModel
from typing import Dict

router = APIRouter(prefix="/api/finance", tags=["Finance"])

# class MetricsResponse(BaseModel):
#     ticker: str
#     tickerName: str
#     metrics: Dict[str, float | str]
from typing import List

class AllocationItem(BaseModel):
    ticker: str
    allocation: float

class MetricsResponse(BaseModel):
    annual: Dict[str, float]
    allocations: List[AllocationItem]

@router.post("/metrics", response_model=MetricsResponse)
async def get_financial_metrics(request: MetricsRequest):
    try:
        # data = get_metrics_data_from_csv(request.ticker, request.metrics)
        # return {
        #     "ticker": request.ticker,
        #     "tickerName": request.tickerName,
        #     "metrics": data
        # }
        
        weights = {item.name: item.weight for item in request.metrics}
        ticker_count = request.ticker_count
        ticker_top, ticker_bottom = makeFactor(weights, ticker_count) 
        #metric, count 입력 / 팩터 상위,하위 count개 ticker_top,ticker_bottom 출력
        #상위, 하위 티커 리스트 입력 / annual : 상위,하위 n개 연평균수익률, allo_list : 종목과 포폴비중 출력
        allo_list, annual = makePortpolio(ticker_top, ticker_bottom)
        return {
            "annual" : annual,
            "allocations" : allo_list
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": str(e)})