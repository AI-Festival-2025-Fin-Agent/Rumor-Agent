# Search Agent Documentation

## 개요
LangGraph 기반 통합 검색 에이전트로 뉴스와 출판물(정기보고서, 정정보고서)을 병렬 검색하고 결과를 정리하는 시스템

## 그래프 구조
```
analyze_query → search_news (병렬)
               ↘
                search_publications (병렬) → format_results → select_documents → generate_response → END
               ↗
```

## State 구조 (`SearchState`)

### 입력 데이터
- `query: str` - 검색 쿼리
- `search_preference: str` - "news", "publications", "both" (기본값: "both")

### 중간 처리 데이터
- `news_results: Optional[Dict]` - 네이버 뉴스 API 원본 응답
- `publication_results: Optional[Dict]` - 출판물 API 원본 응답
- `news_errors: List[str]` - 뉴스 검색 에러 목록
- `pub_errors: List[str]` - 출판물 검색 에러 목록

### 출력 데이터
- `searched_list: Optional[Dict]` - 정리된 검색 결과 (LLM 처리용)
- `selected_documents: Optional[Dict]` - LLM이 선택한 확인할 문서들
- `search_summary: str` - 검색 결과 요약 텍스트
- `generated_response: Optional[str]` - 최종 생성된 답변

## 노드별 상세 흐름

### 1. `analyze_query` 노드
**입력**: `query`, `search_preference` (선택)
**처리**:
- `search_preference` 기본값 설정 ("both")
- 에러 리스트 초기화 (`news_errors`, `pub_errors`)

**출력**: 초기화된 state

### 2. `search_news` 노드 (병렬 실행)
**입력**: `query`, `search_preference`
**처리**:
- 네이버 뉴스 API 호출 (display=20, sort="sim")
- 에러 발생 시 `news_errors`에 추가

**출력**:
```python
{
    "news_results": {...},  # 네이버 API 원본 응답
    "news_errors": [...]    # 에러 목록
}
```

### 3. `search_publications` 노드 (병렬 실행)
**입력**: `query`
**처리**:
- 출판물 API 호출 (http://211.188.53.220:2024/runs/wait)
- 에러 발생 시 `pub_errors`에 추가

**출력**:
```python
{
    "publication_results": {...},  # 출판물 API 원본 응답
    "pub_errors": [...]            # 에러 목록
}
```

### 4. `format_results` 노드
**입력**: 모든 검색 결과
**처리**:
1. 검색 결과를 정리하여 `searched_list` 생성
2. 요약 정보 생성
3. 메모리 절약을 위해 원본 데이터 삭제

**출력**: 정리된 결과 + 요약

### 5. `select_documents` 노드 (DocumentNodes 클래스)
**입력**: `searched_list`, `query`
**처리**:
1. LLM(HCX-007)을 사용하여 검색된 문서들 중에서 분석할 문서 선택
2. 사용자 쿼리와 관련성이 높은 문서들을 우선순위별로 선정
3. API 1-28 상세 설명을 포함하여 정기보고서 API 키 선별
4. JSON 형태로 선택된 문서 목록 생성

**출력**:
```python
{
    "selected_documents": {
        "news": [
            {
                "title": "선택된 뉴스 제목",
                "date": "2024-10-09",
                "link": "...",
                "reason": "선택 이유",
                "priority": 1
            }
        ],
        "regular": [
            {
                "company_name": "LG",
                "year": 2025,
                "quarter": 2,
                "filename": "003550_LG.json",
                "api_keys_to_check": ["api_01", "api_05", "api_10"],
                "reason": "선택 이유",
                "priority": 1
            }
        ],
        "revision": [
            {
                "basic_info": {...},
                "reason": "선택 이유",
                "priority": 2
            }
        ],
        "selection_summary": "총 5개 문서 선택: 뉴스 2건, 정기보고서 2건, 정정보고서 1건"
    }
}
```

## 데이터 변환 과정

### News Results 변환
**원본** (`news_results`):
```json
{
  "lastBuildDate": "...",
  "total": 100,
  "start": 1,
  "display": 20,
  "items": [
    {
      "title": "뉴스 제목",
      "originallink": "...",
      "link": "...",
      "description": "뉴스 내용 전체...",
      "pubDate": "...",
      "formatted_date": "2024-10-09"
    }
  ]
}
```

**변환** (`searched_list.news`):
```json
[
  {
    "title": "뉴스 제목",
    "date": "2024-10-09",
    "link": "...",
    "description": "뉴스 내용 전체..."
  }
]
```

### Publication Results 변환
**원본** (`publication_results`):
```json
{
  "regular_results": {
    "available_reports": [
      {
        "year": 2025,
        "quarter": 2,
        "company_name": "LG",
        "filename": "003550_LG.json",
        "processed_data": {
          "metadata": {
            "corp_code": "00120021",
            "corp_name": "LG",
            "stock_code": "003550",
            "year_quarter": "2025_Q2",
            "collection_date": "2025-09-29T11:57:03.993855",
            "successful_apis": 28
          },
          "api_data": {
            "api_01": [...],
            "api_02": [...],
            ...
          }
        }
      }
    ]
  },
  "revision_results": {
    "revision_documents": [
      {
        "basic_info": {
          "company": "LG",
          "report_name": "[기재정정]타법인주식및출자증권취득결정",
          "submitter": "LG",
          "date": "2025.10.01",
          "rcept_no": "20251001800707",
          "url": "https://dart.fss.or.kr/...",
          "title": "LG/타법인주식및출자증권취득결정/2025.10.01"
        },
        "content_length": 3669,
        "index": 0
      }
    ]
  }
}
```

**변환** (`searched_list`):
```json
{
  "news": [...],
  "regular": [
    {
      "year": 2025,
      "quarter": 2,
      "company_name": "LG",
      "filename": "003550_LG.json",
      "metadata": {
        "corp_code": "00120021",
        "corp_name": "LG",
        "stock_code": "003550",
        "year_quarter": "2025_Q2",
        "collection_date": "2025-09-29T11:57:03.993855",
        "successful_apis": 28
      },
      "api_keys": ["api_01", "api_02", ..., "api_28"]
    }
  ],
  "revision": [
    {
      "basic_info": {
        "company": "LG",
        "report_name": "[기재정정]타법인주식및출자증권취득결정",
        "submitter": "LG",
        "date": "2025.10.01",
        "rcept_no": "20251001800707",
        "url": "https://dart.fss.or.kr/...",
        "title": "LG/타법인주식및출자증권취득결정/2025.10.01"
      },
      "content_length": 3669,
      "index": 0
    }
  ]
}
```

## Final Output 형태
```
=== 검색 결과 요약: '삼성전자 매출' ===
📰 뉴스: 5건
   뉴스 제목:
   - 삼성전자 3분기 실적 발표 (2024-10-09)
   - 삼성전자 매출 증가세 (2024-10-08)

📊 정기보고서: 12건
   회사명:
   - 삼성전자 (2025년 2분기)
   - 삼성전자 (2025년 1분기)

🔄 정정보고서: 3건
   문서 인덱스:
   - 2025.10.01 [기재정정]타법인주식및출자증권취득결정
   - 2025.09.15 [기재정정]주요경영사항

⚠️ 에러 0건
```

## 병렬 처리
- `search_news`와 `search_publications` 노드가 동시 실행
- 각각 다른 state 키를 업데이트하여 충돌 방지:
  - `search_news`: `news_results`, `news_errors`
  - `search_publications`: `publication_results`, `pub_errors`

## 메모리 최적화
- `format_results` 완료 후 원본 데이터 삭제
- `searched_list`에 필요한 정보만 유지
- LLM 처리에 필요한 모든 정보는 `searched_list`에 보존

## LLM 프롬프트 (select_documents 노드)

### 시스템 프롬프트
```
당신은 검색된 문서들 중에서 사용자 쿼리에 가장 관련성이 높은 문서들을 선택하는 AI 어시스턴트입니다.

다음 기준으로 문서를 선택하세요:
1. 사용자 쿼리와의 직접적 관련성
2. 정보의 신뢰성 (정기보고서 > 정정보고서 > 뉴스)
3. 정보의 최신성
4. 정보의 구체성

각 문서 유형별로 최대 선택 개수:
- 뉴스: 최대 3개
- 정기보고서: 최대 5개 (관련 API 키도 선별)
- 정정보고서: 최대 5개

반드시 JSON 형태로 응답하세요.
```

### 사용자 프롬프트 템플릿
```
사용자 쿼리: "{query}"

검색된 문서 목록:
{searched_list}

위 문서들 중에서 사용자 쿼리에 가장 관련성이 높은 문서들을 선택하고, 선택 이유와 우선순위를 포함하여 JSON 형태로 응답해주세요.

정기보고서의 경우 관련성이 높은 API 키들만 선별해서 포함해주세요.
API 키 설명:
- api_01: 증자(감자) 현황
- api_02: 배당에 관한 사항
- api_03: 자기주식 취득 및 처분 현황
- api_04: 최대주주 현황
- api_05: 최대주주 변동현황
- api_06: 소액주주 현황
- api_07: 임원 현황
- api_08: 직원 현황
- api_09: 이사·감사의 개인별 보수현황(5억원 이상)
- api_10: 이사·감사 전체의 보수현황(보수지급금액 - 이사·감사 전체)
- ... (api_11~api_28까지 전체 목록)
```

## 구현 클래스 구조

### SearchNodes 클래스
- `analyze_query()`: 쿼리 분석 및 초기화
- `search_news()`: 네이버 뉴스 검색
- `search_publications()`: 출판물 검색
- `format_results()`: 검색 결과 정리

### DocumentNodes 클래스
- `select_documents()`: LLM 기반 문서 선택
- API 1-28 전체 설명 매핑 포함
- HCX-007 모델 사용

### GenerationNodes 클래스 (예정)
- `generate_response()`: 선택된 문서 기반 최종 답변 생성
- 문서 내용 분석 및 종합
- 사용자 쿼리에 맞는 답변 생성

## 다음 단계
- **generate_response 노드 구현**
  - 선택된 문서들의 실제 내용 로딩
  - LLM을 통한 문서 분석 및 답변 생성
  - 정기보고서 API 데이터 활용
  - 뉴스/정정보고서 본문 활용