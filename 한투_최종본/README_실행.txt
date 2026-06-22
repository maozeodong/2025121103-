한국투자증권 모의투자 자동매매 최종본
==================================

가장 쉬운 실행 방법

1. run_trader.cmd를 더블클릭합니다.
2. 토큰 발급 또는 당일 토큰 재사용, 현재가 조회, 잔고 조회,
   전략 판단 결과가 명령창에 표시됩니다.
3. .env의 DRY_RUN=false 상태에서는 전략 판단이 buy 또는 sell일 때
   한국투자증권 모의계좌 주문이 실제로 접수됩니다.

PowerShell 실행

cd C:\Projects\한투_최종본
.\run_trader.cmd

주요 파일

- kis_live_once_stdlib.py : 외부 패키지 없이 한 번 실행하는 권장 실행기
- run_trader.cmd          : 더블클릭 실행 파일
- .env                    : 실제 모의계좌 설정
- token_cache.json        : 실행 후 생성되는 당일 토큰 캐시
- logs\status.json        : 최근 실행 결과
- main.py                 : requests 기반 반복 실행 진입점

보안 주의

이 로컬 폴더와 ZIP에는 실제 계좌번호, App Key, App Secret이 포함됩니다.
다른 사람에게 전달하거나 공개 GitHub 저장소에 업로드하지 마세요.

GitHub 업로드 시에는 .env, token_cache.json, logs 폴더를 제외해야 합니다.
.gitignore에 해당 항목이 이미 등록되어 있습니다.
