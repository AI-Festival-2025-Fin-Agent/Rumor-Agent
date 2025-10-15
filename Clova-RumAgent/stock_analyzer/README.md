# 🔍 Rumor Verification API

기업 루머 및 뉴스 팩트체킹 AI 분석 시스템

## 개요

실시간 뉴스 데이터를 기반으로 기업 관련 루머의 사실 여부를 검증하는 AI 시스템입니다. 네이버 뉴스 API를 통해 최신 뉴스를 수집하고, Google Gemini AI를 활용하여 팩트체킹을 수행합니다.

## 주요 기능

- 🔍 **루머 검증**: 특정 루머 내용과 회사명을 입력하면 사실 여부 판단
- 📰 **뉴스 수집**: 네이버 뉴스 API를 통한 실시간 뉴스 검색
- 🤖 **AI 분석**: Google Gemini를 활용한 신뢰성 있는 팩트체킹
- 📊 **신뢰도 평가**: 뉴스 출처 공신력 및 확신도 평가
- 💾 **자동 저장**: 모든 검증 결과와 수집된 뉴스 데이터 자동 저장
- 🔎 **결과 조회**: 과거 검증 결과 검색 및 조회 기능

## API 사용법

### 루머 검증
```bash
curl -X POST "http://localhost:9000/verify" \
     -H "Content-Type: application/json" \
     -d '{
       "rumor_text": "삼성전자 이재용이 자사주 매입했다는 거 사실이야?",
       "company_name": "삼성전자",
       "news_count": 10
     }'
```

### 요청 파라미터
- `rumor_text` (required): 검증할 루머 내용
- `company_name` (required): 관련 회사명
- `news_count` (optional): 검색할 뉴스 개수 (기본값: 10)

### 응답 예시
```json
{
  "rumor_text": "삼성전자 이재용이 자사주 매입했다는 거 사실이야?",
  "company_name": "삼성전자",
  "verification_result": "## 🔍 \"삼성전자 이재용이 자사주 매입했다는 거 사실이야?\" 루머 검증 분석\n\n### 🎯 루머 검증 결과\n- **전체 신뢰도**: 높음\n- **루머 판정**: **사실**\n- **확신도**: ⭐⭐⭐⭐⭐ (5점 만점)\n\n### 📋 근거 분석\n- **사실 근거**: 공식 보도자료 확인됨\n- **의심 요소**: 없음\n- **추가 확인 필요**: 매입 규모 및 시기\n\n### 🚨 결론\n해당 정보는 공식 발표를 통해 확인된 사실입니다.",
  "news_count": 10,
  "status": "success",
  "timestamp": "2025-01-31T12:00:00",
  "saved_file_path": "verification_results/2025-01-31/삼성전자_120000_abc12345.json"
}
```

### API 상태 확인
```bash
curl http://localhost:9000/
```

### 헬스 체크
```bash
curl http://localhost:9000/health
```

### 최근 검증 결과 조회
```bash
# 최근 10개 결과 조회 (기본값)
curl http://localhost:9000/recent

# 최근 5개 결과 조회
curl http://localhost:9000/recent?limit=5
```

### 검증 결과 검색
```bash
# 회사명으로 검색
curl "http://localhost:9000/search?company_name=삼성전자"

# 키워드로 검색
curl "http://localhost:9000/search?keyword=자사주"

# 회사명과 키워드 조합 검색
curl "http://localhost:9000/search?company_name=삼성전자&keyword=매입"
```

### 특정 검증 결과 상세 조회
```bash
# 검증 ID로 상세 정보 조회 (뉴스 데이터 포함)
curl http://localhost:9000/verification/abc12345
```

## CLI 사용법

```bash
# 기본 사용법
python main.py "루머 내용" "회사명"

# 뉴스 개수 지정
python main.py "루머 내용" "회사명" 20

# 예시
python main.py "삼성전자 이재용이 자사주 매입했다는 거 사실이야?" "삼성전자"
```

## 설치 및 실행

### 1. 환경 설정
```bash
# 의존성 설치
pip install -r requirements.txt

# 환경 변수 설정 (.env 파일 생성)
NAVER_CLIENT_ID=your_naver_client_id
NAVER_CLIENT_SECRET=your_naver_client_secret
GOOGLE_API_KEY=your_google_api_key
```

### 2. 서버 실행
```bash
python main.py
```

서버는 기본적으로 `http://localhost:9000`에서 실행됩니다.

## 프로젝트 구조

```
stock_analyzer/
├── main.py                 # FastAPI 서버 메인 파일
├── src/
│   ├── news_searcher.py    # 네이버 뉴스 검색 모듈
│   ├── ai_analyzer.py      # AI 분석 모듈 (Google Gemini)
│   └── result_storage.py   # 검증 결과 저장 모듈
├── config/
│   └── settings.py         # 설정 파일
├── prompts/
│   └── prompts.yaml        # AI 프롬프트 템플릿
├── verification_results/   # 검증 결과 저장 폴더 (자동 생성)
│   ├── index.json          # 검색용 인덱스 파일
│   ├── 2025-01-31/         # 날짜별 폴더
│   │   ├── 삼성전자_120000_abc12345.json
│   │   └── LG전자_130000_def67890.json
│   └── 2025-02-01/
│       └── 현대차_140000_ghi11111.json
└── requirements.txt        # 의존성 목록
```

## 저장된 데이터 구조

모든 검증 결과는 JSON 형태로 자동 저장되며, 다음 정보를 포함합니다:

```json
{
  "id": "abc12345",
  "timestamp": "2025-01-31T12:00:00",
  "request": {
    "rumor_text": "삼성전자 이재용이 자사주 매입했다는 거 사실이야?",
    "company_name": "삼성전자",
    "news_count": 10
  },
  "news_data": [
    {
      "title": "뉴스 제목",
      "description": "뉴스 내용 요약",
      "link": "뉴스 링크",
      "pub_date": "발행일",
      "formatted_date": "2025-01-31 12:00"
    }
  ],
  "analysis_details": "개별 뉴스 분석 결과",
  "final_result": "AI 루머 검증 최종 결과",
  "status": "success",
  "metadata": {
    "total_news_found": 10,
    "processing_time": "2025-01-31T12:00:00"
  }
}
```

### 저장 시스템 특징

- 📅 **날짜별 분류**: 검증 날짜별로 폴더 자동 생성
- 🔍 **빠른 검색**: 인덱스 파일을 통한 효율적인 검색
- 📊 **완전한 기록**: 요청부터 결과까지 모든 과정 저장
- 🏷️ **고유 ID**: 각 검증마다 고유 식별자 부여

## 분석 결과 형식

AI 분석 결과는 다음과 같은 구조로 제공됩니다:

- **뉴스 신뢰성 분석**: 각 뉴스의 신뢰도, 출처, 검증 상태
- **루머 검증 결과**: 전체 신뢰도, 루머 판정, 확신도
- **근거 분석**: 사실 근거, 의심 요소, 추가 확인 필요 사항
- **결론**: 명확한 사실/루머 판단과 그 이유

## 판정 기준

### 루머 판정 유형
- **사실**: 공식 발표나 신뢰할 수 있는 언론사에서 확인된 정보
- **부분 사실**: 일부는 맞지만 과장되거나 왜곡된 부분이 있는 정보
- **루머**: 근거가 없거나 허위인 정보
- **검증 불가**: 충분한 정보가 없어 판단하기 어려운 경우

### 신뢰도 평가
- **높음**: 공식 발표, 주요 언론사 보도
- **보통**: 일반 언론사, 부분적 확인 가능
- **낮음**: 개인 블로그, 커뮤니티, 미확인 정보

## 주의사항

- 이 시스템은 뉴스 기반 분석이며, 투자나 중요한 결정에는 추가적인 확인이 필요합니다
- AI 분석 결과는 참고용이며, 최종 판단은 사용자의 책임입니다
- 실시간 뉴스 데이터에 의존하므로, 최신 정보가 반영되지 않을 수 있습니다

## 라이선스

MIT License