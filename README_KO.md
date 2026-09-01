# ABA 프로그램 운영용 MVP

## 포함 기능
- 관리자/재활사 로그인
- 비밀번호 해시 저장
- 관리자 전체 아동 조회
- 재활사는 담당 아동만 조회
- 관리자 재활사 계정 생성/비밀번호 재설정/비활성화
- 아동 등록 및 담당 재활사 배정
- 1~9 영역 프로그램
- 회기당 10회 + / P / - 입력
- 데이터베이스 저장
- 영역별 초기-최근 비교 결과지
- 결과지 인쇄

## 기본 관리자
- 아이디: na102502
- 비밀번호: 0673

**첫 로그인 후 비밀번호를 변경하는 것을 권장합니다.**

## 로컬 실행
Python 3.11 이상 기준

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
python app.py
```

브라우저에서:
http://127.0.0.1:5000

## 실제 인터넷 운영 시
권장:
1. Render / Railway / Fly.io 등 HTTPS 지원 서버
2. PostgreSQL 데이터베이스
3. 환경변수 설정
   - SECRET_KEY: 충분히 긴 임의 문자열
   - DATABASE_URL: PostgreSQL 연결 문자열
4. gunicorn으로 실행
   `gunicorn app:app`

## 매우 중요
아동 개인정보와 치료기록은 민감한 정보입니다.
실제 배포 전에는 아래를 반드시 적용/검토하세요.
- HTTPS
- 강한 관리자 비밀번호
- 정기 백업
- 최소권한 원칙
- 퇴사자 계정 즉시 비활성화
- 개인정보 보유/파기 정책
- 접근 로그
- 한국 개인정보보호법 및 기관 내부 개인정보 처리방침 검토

현재 패키지는 '운영 가능한 MVP'이지만, 의료/민감정보를 장기간 보관하는 상용 시스템으로 확장하기 전에는 보안 전문가 또는 개발자의 배포 점검을 권장합니다.
