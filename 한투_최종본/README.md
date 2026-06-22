# Samsung Electronics Mock Auto Trader + Finance Engineering Report

한국투자증권 Open API의 **모의투자 REST API만** 사용해 삼성전자(`005930`) 지정가 주문을 실행하는 작은 Python 프로젝트입니다. WebSocket과 실전투자 주소/TR ID는 사용하지 않습니다.

기본값은 안전을 위해 `DRY_RUN=true`입니다. 이 상태에서는 시세와 잔고를 조회하고 주문 내용을 기록하지만 실제 모의주문은 전송하지 않습니다.

기말 프로젝트 제출용으로는 단순 주문 봇에 그치지 않도록, 강의에서 다룬 P&L, Brownian motion, Black-Scholes, put-call parity를 연결한 분석 리포트 생성 기능도 포함했습니다.

## 폴더 구조와 역할

```text
samsung_auto_trader/
├── main.py              # 실행 진입점
├── config.py            # 환경 변수, 거래 시간, 전략 설정
├── auth.py              # 당일 접근 토큰 캐시 및 재사용
├── api_client.py        # REST 호출, 간격 제한, timeout/retry
├── market_data.py       # 삼성전자 현재가 조회
├── account.py           # 보유수량 및 주문가능 현금 조회
├── orders.py            # 모의투자 현금 지정가 주문
├── trader.py            # 거래 시간과 전략 루프
├── finance_math.py      # P&L, Black-Scholes, put-call parity 계산
├── simulation.py        # Brownian motion 가격 경로와 P&L 시나리오
├── final_finance_report.py # CSV/Markdown 금융공학 리포트 생성
├── logger.py            # 콘솔/일별 파일 로그
├── tests/               # 네트워크를 사용하지 않는 단위 테스트
├── token_cache.json     # 실행 중 생성되는 토큰 캐시(Git 제외)
├── requirements.txt
└── .env.example
```

`token_cache.json`, `.env`, `logs/`는 Git에 커밋되지 않습니다.

## 전략과 API 호출 절약

- 거래 시간: 한국시간 09:10 이상, 15:30 미만
- 현재가 1회 조회 → 잔고 1회 조회
- Brownian motion 시뮬레이션으로 기대수익률과 손실확률 추정
- 기본 매수가: 현재가 - 1,000원
- 기본 매도가: 현재가 + 1,000원
- 각 주문 후 설정된 시간만큼 기다린 뒤 잔고를 1회 조회해 체결 여부 추정
- 미체결로 보이는 주문 방향은 같은 프로세스에서 중복 제출하지 않음
- 매도는 확인된 보유수량이 있을 때만 제출
- 기본 폴링 간격은 5분

기본값은 정규장 중심입니다. 장외/시간외까지 판단을 계속 돌리고 싶으면:

```text
TRADING_WINDOW_MODE=always
```

로 설정합니다. 단, 한국투자증권 API가 실제로 장외 주문을 접수하려면 주문구분 코드(`ORD_DVSN`)가 해당 거래 유형에 맞아야 합니다. 이 프로젝트는 이를 환경변수로 열어둡니다.

```text
ORDER_DIVISION=00
```

`00`은 기본 지정가 주문입니다. 시간외/장전/장후 주문은 한국투자증권 API 문서의 최신 주문구분 코드를 확인한 뒤 `ORDER_DIVISION`에 넣어야 합니다.

요구사항에 2,000원과 1,000원이 함께 기재되어 있어 기본값은 기능 요구사항의 1,000원으로 정했습니다. `PRICE_OFFSET_KRW=2000`으로 쉽게 변경할 수 있습니다.

잔고 변화만으로 체결 여부를 추정하므로 부분체결/동시 외부주문까지 완벽히 구분하지는 못합니다. 호출량을 최소화하기 위한 의도적인 절충입니다.

### 언제 사고 언제 파는가

기본 전략 모드는 `STRATEGY_MODE=finance`입니다.

매수 조건:

```text
보유수량이 0이고
Brownian simulation expected_return >= MIN_EXPECTED_RETURN 이고
loss_probability <= MAX_LOSS_PROBABILITY 이고
주문가능현금이 충분하면
현재가 - PRICE_OFFSET_KRW 에 지정가 매수
```

기본값:

```text
MIN_EXPECTED_RETURN = 0.1%
MAX_LOSS_PROBABILITY = 48%
```

매도 조건:

```text
보유수량이 있고
현재수익률 >= TAKE_PROFIT_PCT 이거나
현재수익률 <= -STOP_LOSS_PCT 이거나
Brownian simulation expected_return < 0 이면
현재가 + PRICE_OFFSET_KRW 에 지정가 매도
```

기본값:

```text
TAKE_PROFIT_PCT = 1%
STOP_LOSS_PCT = 1%
```

즉 단순히 현재가 아래/위에 주문을 내는 것이 아니라, Brownian motion 기반 기대수익과 손실확률 필터를 통과해야 매수하고, 보유 중에는 목표수익/손절/기대수익 악화를 기준으로 매도합니다.

## 금융공학 분석 리포트

계좌/API 키가 없어도 강의 개념을 보여줄 수 있도록, 현재가 하나를 기준으로 금융공학 분석 파일을 생성할 수 있습니다.

```bash
python final_finance_report.py --symbol 005930 --current-price 73500 --quantity 1
```

생성 파일:

```text
outputs/final_finance_report.md
outputs/pnl_scenarios.csv
outputs/brownian_paths.csv
```

포함 내용:

- 현재가 기준 지정가 매수/매도 가격
- 현물 포지션의 mark-to-market P&L
- 가격 충격별 P&L 시나리오
- Brownian motion 기반 가격 경로 시뮬레이션
- Black-Scholes call/put 가격
- put-call parity gap 검증

이 기능은 Week 5~13의 금융공학 내용을 API 프로젝트와 연결하기 위한 제출용 분석 파트입니다.

## GitHub Codespaces Secret 등록

1. [GitHub Codespaces settings](https://github.com/settings/codespaces)를 엽니다.
2. `Secrets`에서 아래 세 Repository secret을 등록하고 이 저장소에 접근 권한을 줍니다.
   - `GH_ACCOUNT`: 모의계좌 10자리, 예: `12345678-01`
   - `GH_APPKEY`: 모의투자 App Key
   - `GH_APPSECRET`: 모의투자 App Secret
3. 실제 값을 파일이나 채팅에 붙여넣지 마세요.

Codespaces secret은 새 Codespace를 만들 때 환경 변수로 전달됩니다. 기존 Codespace라면 재시작이 필요할 수 있습니다.

## 설치와 실행

Python 3.11 이상을 권장합니다.

```bash
python -m venv .venv
```

VS Code에서 `.venv` 인터프리터를 선택한 뒤:

```bash
python -m pip install -r requirements.txt
python main.py
```

로컬에서는 `.env.example`을 `.env`로 복사하고 값을 채웁니다. `.env`는 Git에서 제외됩니다.

처음에는 반드시 `DRY_RUN=true`로 로그와 응답을 확인하세요. 모의주문을 실제 전송하려면:

```text
DRY_RUN=false
```

## 설정값

| 환경 변수 | 기본값 | 설명 |
|---|---:|---|
| `SYMBOL` | `005930` | 거래할 국내 종목/ETF 코드 |
| `MARKET_CODE` | `J` | 국내주식/ETF 조회 시장 구분 |
| `EXCHANGE_CODE` | `KRX` | 국내 주문 거래소 구분 |
| `PRICE_OFFSET_KRW` | `1000` | 현재가 대비 지정가 차이 |
| `ORDER_QUANTITY` | `1` | 주문 수량 |
| `POLL_INTERVAL_SECONDS` | `300` | 거래 루프 간격(최소 30초) |
| `ORDER_VERIFY_DELAY_SECONDS` | `10` | 주문 후 잔고 재조회 대기 |
| `REQUEST_INTERVAL_SECONDS` | `0.5` | REST 요청 사이 최소 간격 |
| `REQUEST_TIMEOUT_SECONDS` | `10` | 요청 timeout |
| `MAX_RETRIES` | `2` | 네트워크/5xx 재시도 횟수 |
| `DRY_RUN` | `true` | 주문 전송 차단 |
| `TRADING_WINDOW_MODE` | `regular` | `regular` 또는 시간 제한 우회 `always` |
| `ORDER_DIVISION` | `00` | KIS `ORD_DVSN`; 정규장 지정가 기본값 |
| `STRATEGY_MODE` | `finance` | `finance` 또는 기존 방식 `limit_only` |
| `ANNUAL_DRIFT` | `0.05` | Brownian simulation 연율 기대수익 가정 |
| `ANNUAL_VOLATILITY` | `0.20` | Brownian simulation 연율 변동성 가정 |
| `SIMULATION_DAYS` | `20` | 시뮬레이션 기간 |
| `SIMULATION_PATHS` | `500` | 시뮬레이션 경로 수 |
| `MIN_EXPECTED_RETURN` | `0.001` | 매수에 필요한 최소 기대수익률 |
| `MAX_LOSS_PROBABILITY` | `0.48` | 매수 허용 최대 손실확률 |
| `TAKE_PROFIT_PCT` | `0.01` | 매도 목표수익률 |
| `STOP_LOSS_PCT` | `0.01` | 손절 기준 |

국내 ETF 예시:

```text
SYMBOL=069500  # KODEX 200
SYMBOL=102110  # TIGER 200
```

국내 ETF는 국내주식 REST API와 같은 형태로 조회/주문할 수 있다. 반면 TQQQ 같은 미국 ETF는 해외주식 API 엔드포인트와 TR ID가 별도이므로 이 프로젝트의 국내주식 모듈과 분리해서 구현해야 한다.

## 테스트

```bash
python -m pip install -r requirements-dev.txt
pytest
```

의존성 없이 문법만 확인하려면:

```bash
python -m py_compile *.py
```

## 확인한 공식 샘플 사양

- 모의투자 REST 기본 URL: `https://openapivts.koreainvestment.com:29443`
- 토큰: `POST /oauth2/tokenP`
- 현재가: `GET /uapi/domestic-stock/v1/quotations/inquire-price`, TR `FHKST01010100`
- 잔고: `GET /uapi/domestic-stock/v1/trading/inquire-balance`, TR `VTTC8434R`
- 현금주문: `POST /uapi/domestic-stock/v1/trading/order-cash`
  - 모의 매수 TR `VTTC0802U`
  - 모의 매도 TR `VTTC0801U`

한국투자증권이 샘플 및 필드를 변경할 수 있으므로, 주문 전 [공식 Open API 샘플 저장소](https://github.com/koreainvestment/open-trading-api)와 API 포털에서 다시 확인하세요.

## 주의

이 프로젝트는 모의투자용 예제이며 투자 조언이 아닙니다. 프로그램 재시작 뒤에는 이전 프로세스의 미체결 주문 상태를 기억하지 못하므로, 재실행 전 모의투자 주문내역을 직접 확인하세요.

`TRADING_WINDOW_MODE=always`는 내부 시간 제한만 해제합니다. 장외시장의 유동성, 호가 제한, 체결 가능성, API 주문구분 제한은 별도 리스크입니다. 이 설정은 수익을 보장하지 않으며, 기회 탐색 범위를 넓히는 대신 체결/가격 리스크가 커질 수 있습니다.
