from pydantic import BaseModel
from typing import List

class MetricsRequest(BaseModel):
    ticker: str                 # 예: "AAPL"
    tickerName: str             # 예: "애플" 또는 "Apple Inc."
    metrics: List[str]          # 예: ["ROE", "ROA", "PER"]
