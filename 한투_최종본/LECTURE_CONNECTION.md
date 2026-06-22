# 강의 내용과 Samsung Auto Trader 연결

## 프로젝트 위치

`samsung_auto_trader`는 한국투자증권 Open API를 이용해 삼성전자(`005930`) 현재가, 잔고, 주문 흐름을 구현한 모의투자 프로젝트다. 강의계획서상 Week 12의 Postman, Week 13의 KIS + Excel 내용과 직접 연결된다.

## 금융공학 개념 적용

### P&L

전략의 기본 손익 구조는 다음과 같이 해석할 수 있다.

```text
P&L = 보유수량 * (현재가격 - 매입가격) - 거래비용
```

코드는 현재가를 조회한 뒤 다음 가격으로 지정가 주문을 구성한다.

```text
매수가 = 현재가 - PRICE_OFFSET_KRW
매도가 = 현재가 + PRICE_OFFSET_KRW
```

이는 가격 변화와 거래비용을 고려해 포지션 손익을 관리하는 P&L 관점의 단순화된 구현이다.

### Risk Control

기본값은 보수적으로 설계되어 있다.

- `DRY_RUN=true`: 실제 주문 전송 방지
- `ORDER_QUANTITY=1`: 주문 수량 제한
- 거래시간 제한: 09:10~15:30
- 미체결 추정 주문 방향 중복 제출 방지
- 요청 간격 제한과 retry 적용

이는 수익률 극대화보다 API 안정성, 주문 실수 방지, 리스크 제한을 우선한 구조다.

### Deep Hedging과의 연결

수업의 deep hedging은 기초자산 가격 경로와 현재 포지션을 바탕으로 hedge ratio를 조정한다. 이 프로젝트는 옵션 hedge ratio를 학습하지는 않지만, 다음 구조가 유사하다.

| Deep Hedging | 이 프로젝트 |
|---|---|
| 기초자산 가격 경로 | 삼성전자 현재가 |
| 현재 hedge position | 현재 보유수량 |
| P&L 계산 | 현재가 대비 지정가 전략 |
| transaction cost | 주문 수량, 지정가, 중복주문 제한 |
| rebalancing | polling loop |

## 강의 주차별 연결

- Week 5 pfhedge: 금융상품과 hedge를 코드 객체로 표현하는 관점
- Week 6 Brownian motion: 가격 경로의 확률적 움직임에 대한 관점
- Week 7 P&L/Dataset: 거래 결과를 손익 구조로 해석
- Week 8 Fit: 반복 학습/반복 실행 구조 이해
- Week 9 Loss/prev_hedge: 이전 포지션을 고려하는 사고방식
- Week 12 Postman: API 요청 검증
- Week 13 KIS + Excel: 한국투자증권 API와 데이터 처리

## 보고서 문장

본 프로젝트는 Week 12~13에서 다룬 Postman과 한국투자증권 Open API를 Python 코드로 구현한 것이다. 또한 Week 5~9의 deep hedging/P&L 관점에서, 현재가 조회, 보유수량 확인, 지정가 주문, 중복주문 방지 로직을 하나의 거래 시스템으로 구성하였다.
