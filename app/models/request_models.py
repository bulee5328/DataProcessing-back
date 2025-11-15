from pydantic import BaseModel
from typing import List

# 리퀘스트 요소 바꾸기 
# metrics
# {
#   {지표 : 비중},
#   {지표 : 비중},
#   ...
#   }

# class MetricsRequest(BaseModel):
#     ticker: str                 # 예: "AAPL"
#     tickerName: str             # 예: "애플" 또는 "Apple Inc."
#     metrics: List[str]          # 예: ["ROE", "ROA", "PER"]


class MetricItem(BaseModel):
    name: str
    weight: float

class MetricsRequest(BaseModel):
    ticker_count: int
    metrics: List[MetricItem]