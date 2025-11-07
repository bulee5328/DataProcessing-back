from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
import redis
import uuid
import pymysql
import re
app = FastAPI()
# -------------------------------
# Redis 연결 설정
# -------------------------------
r = redis.Redis(host="myredis", port=6379, decode_responses=True)
# -------------------------------
# DB 연결 함수 (PHP 환경과 동일 설정)
# -------------------------------
def get_db():
    return pymysql.connect(
        host="mysql",
        user="php-mysql",
        password="123456",
        database="php-mysql",
        cursorclass=pymysql.cursors.DictCursor
    )
# -------------------------------
# PHP 세션 직렬화 함수
# -------------------------------
def php_session_encode(session_dict: dict) -> str:
    """
    Python dict → PHP 세션 직렬화 문자열 변환
    예: {"useremail": "abc@gctask.com", "username": "홍길동"}
     → useremail|s:14:"abc@gctask.com";username|s:9:"홍길동";
    """
    session_str = ""
    for key, value in session_dict.items():  #인자 이름 일치시킴
        byte_len = len(value.encode("utf-8"))  # UTF-8 바이트 길이 계산
        session_str += f"{key}|s:{byte_len}:\"{value}\";"
    return session_str
# -------------------------------
# PHP 세션 역직렬화 함수
# -------------------------------
def php_session_decode(session_data: str) -> dict:
    """
    PHP 세션 문자열 → Python dict 변환
    예: 'useremail|s:14:"abc@gctask.com";username|s:9:"홍길동";'
     → {'useremail': 'abc@gctask.com', 'username': '홍길동'}
    """
    if not session_data:
        return {}
    return dict(re.findall(r'(\w+)\|s:\d+:"([^"]*)"', session_data))
# -------------------------------
# 세션 쿠키 이름
# -------------------------------
COOKIE_NAME = "GCTASKID"
# ================================================================
# 1. 로그인 API
# URL: http://gctask.com/user/login
# ================================================================
#@app.post("/login")
@app.get("/login")
async def login(request: Request, response: Response):
    """
    PHP 세션 구조(useremail|s:len:"...";username|s:len:"...";)에 맞춰 Redis에 저장
    PHP 서버(taskapi)와 완전 호환.
    """
    email = None
    password = None
    # 1. JSON 또는 Form 방식 구분 없이 데이터 읽기
    '''
    try:
        form = await request.json()
    except:
        form = await request.form()
    email = form.get("email")
    password = form.get("password")
    '''
    # (테스트용 GET 허용 — 개발 중에만 사용)
    email = email or request.query_params.get("email")
    password = password or request.query_params.get("password")
    # 2. 필수값 검증
    if not email or not password:
        return JSONResponse(status_code=400, content={"result": "no", "msg": "이메일 또는 비밀번호 누락"})
    # 3. DB 조회
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM user WHERE email=%s AND pass=%s", (email, password))
        user = cur.fetchone()
    conn.close()
    if not user:
        return JSONResponse(status_code=401, content={"result": "no", "msg": "로그인 정보가 틀립니다."})
    # 4. 세션 ID 생성
    session_id = str(uuid.uuid4())
    # 5. PHP 직렬화 포맷으로 세션 문자열 생성
    session_data = php_session_encode({
        "useremail": email,
        "username": user["name"]
    })
    # 6. Redis 저장 (TTL 1시간)
    r.setex(f"session:{session_id}", 3600, session_data)
    # 7. 쿠키 발급
    response.set_cookie(
        key=COOKIE_NAME,
        value=session_id,
        httponly=True,
        samesite="Lax"
    )
    # 8. 결과 반환
    return {
        "result": "ok",
        "msg": "정상 로그인이 되었습니다.",
        "email": email,
        "username": user["name"]
    }
# ================================================================
# 2. 인증 확인 API
# URL: http://gctask.com/user/check
# ================================================================
@app.get("/check")
async def check_session(request: Request):
    """
    Redis에 저장된 PHP 세션 문자열을 파싱하여
    PHP의 $_SESSION 구조로 복원
    """
    session_id = request.cookies.get(COOKIE_NAME)
    if not session_id:
        return {"result": "no", "msg": "세션 없음"}
    data = r.get(f"session:{session_id}")
    if not data:
        return {"result": "no", "msg": "세션 만료"}
    # PHP 세션 문자열 파싱
    session_vars = php_session_decode(data)
    if "useremail" not in session_vars or "username" not in session_vars:
        return {"result": "no", "msg": "세션 파싱 실패"}
    return {
        "result": "ok",
        "msg": "세션 유지 중",
        "email": session_vars["useremail"],
        "username": session_vars["username"]
    }
# ================================================================
# 3. 로그아웃 API
# URL: http://gctask.com/user/logout
# ================================================================
@app.post("/logout")
async def logout(request: Request, response: Response):
    """
    Redis 세션 제거 + 쿠키 삭제
    """
    session_id = request.cookies.get(COOKIE_NAME)
    if session_id:
        r.delete(f"session:{session_id}")
    response.delete_cookie(COOKIE_NAME)
    return {"result": "ok", "msg": "로그아웃 완료"}

