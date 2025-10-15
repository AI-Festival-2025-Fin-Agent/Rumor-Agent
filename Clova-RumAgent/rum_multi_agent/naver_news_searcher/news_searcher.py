"""
네이버 뉴스 검색 모듈
"""
from dotenv import load_dotenv
load_dotenv()

import requests
import urllib.parse
import re
from datetime import datetime
from typing import Dict, List
from dateutil import parser
import os
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
import json

NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")
NAVER_NEWS_API_URL = "https://openapi.naver.com/v1/search/news.json"
DEFAULT_DISPLAY = 10
DEFAULT_SORT = "sim"  # sim: 유사도순, date: 날짜순

# 검색 프롬프트 생성 템플릿
search_prompt_template = ChatPromptTemplate.from_template("""
너는 검색 프롬프트 생성기야.

사용자가 한 질문을 바탕으로, 주제에 맞는 검색 키워드를 자동으로 생성해.
이 키워드들은 실제 뉴스·리포트·데이터 검색에 쓰일 수 있어야 해.

규칙:
1. 질문에서 핵심 개체(예: 기업, 인물, 사건, 주제)를 반드시 포함할 것.
2. 질문의 의도에 맞는 보조 키워드(예: 영향, 이유, 실적, 최근, 규모, 금액 등)를 추가할 수 있음.
3. 주제에서 벗어나지 않게, 관련성 높은 3~5개의 검색 프롬프트를 만들어라.
4. 결과는 JSON 형식으로 출력해라.

📘 참고 패턴:
- 재무/실적형 질문 → ["기업명 실적", "기업명 매출", "기업명 영업이익 최근"]
- 인물 영향형 질문 → ["인물명 기업명 영향", "기업명 실적 변화 이유", "인물명 기업명 최근 뉴스"]
- 사건형 질문 → ["사건명 배경", "사건명 영향", "사건명 관련 기업"]
- 금액/규모형 질문 → ["기업명 자사주 소각 규모", "기업명 자사주 소각 몇 조원", "기업명 자사주 소각 금액 최근"]

출력 예시:
입력: "방시혁 때문에 하이브 매출이 줄었어?"
출력:
{{
  "query": "방시혁 때문에 하이브 매출이 줄었어?",
  "search_prompts": [
    "방시혁 하이브 매출 영향",
    "하이브 매출 감소 이유",
    "방시혁 하이브 최근 뉴스"
  ]
}}

이제 아래 질문에 대해 같은 방식으로 검색 프롬프트를 만들어.
질문: {user_query}
""")

class NewsSearcher:
    """네이버 뉴스 검색 클래스"""

    def __init__(self, client_id: str = None, client_secret: str = None):
        """초기화"""
        self.client_id = client_id or NAVER_CLIENT_ID
        self.client_secret = client_secret or NAVER_CLIENT_SECRET

        if not self.client_id or not self.client_secret:
            raise ValueError("네이버 API 클라이언트 ID와 시크릿을 설정해주세요.")

        # Claude 모델 초기화
        self.llm = ChatAnthropic(
            model="claude-3-5-haiku-latest",
            temperature=0
        )

    def search_news(
        self, 
        query: str, 
        display: int = DEFAULT_DISPLAY, 
        start: int = 1, 
        sort: str = DEFAULT_SORT
    ) -> Dict:
        """뉴스 검색"""
        encoded_query = urllib.parse.quote(query)
        url = f"{NAVER_NEWS_API_URL}?query={encoded_query}&display={display}&start={start}&sort={sort}"
        
        headers = {
            "X-Naver-Client-Id": self.client_id,
            "X-Naver-Client-Secret": self.client_secret,
            "User-Agent": "StockNewsSearcher/1.0"
        }

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"뉴스 검색 중 오류 발생: {e}")

    def generate_search_prompts(self, user_query: str) -> List[str]:
        """사용자 질문을 바탕으로 검색 키워드 생성"""
        chain = search_prompt_template | self.llm

        try:
            response = chain.invoke({"user_query": user_query})
            response_text = response.content

            # JSON 파싱
            json_data = json.loads(response_text)
            search_prompts = json_data.get("search_prompts", [])

            print(f"생성된 검색 키워드: {search_prompts}")
            return search_prompts

        except json.JSONDecodeError as e:
            print(f"JSON 파싱 오류: {e}")
            print(f"응답 내용: {response_text}")
            # 파싱 실패 시 원본 질문 반환
            return [user_query]
        except Exception as e:
            print(f"검색 키워드 생성 중 오류: {e}")
            return [user_query]

    def search_query(self, query: str, display: int = DEFAULT_DISPLAY, sort: str = DEFAULT_SORT) -> Dict:
        """사용자 쿼리로 키워드 생성 후 뉴스 검색"""
        # 검색 키워드 생성
        search_keywords = self.generate_search_prompts(query)

        # 모든 키워드로 검색 결과 수집
        all_results = {"items": []}

        for keyword in search_keywords:
            print(f"키워드 '{keyword}'로 검색 중...")
            result = self.search_news(keyword, display//len(search_keywords) or 1, sort=sort)

            if 'items' in result:
                all_results['items'].extend(result['items'])

        # 중복 제거 (링크 기준)
        seen_links = set()
        unique_items = []
        for item in all_results['items']:
            link = item.get('link', '')
            if link and link not in seen_links:
                seen_links.add(link)
                unique_items.append(item)

        all_results['items'] = unique_items[:display]
        print(f"최종 검색된 뉴스 개수: {len(all_results['items'])}개")

        # 포맷팅
        if 'items' in all_results:
            all_results['items'] = [self.format_news_item(item) for item in all_results['items']]

        NewsSearcher.save_results_to_file(all_results, query, search_keywords)
        return all_results

    @staticmethod
    def clean_html_tags(text: str) -> str:
        """HTML 태그 제거"""
        if not text:
            return ""
        cleaned = re.sub(r'<[^>]+>', '', text)
        return cleaned.strip()

    @staticmethod
    def format_news_item(item: Dict) -> Dict:
        print(f"Item의 키들: {list(item.keys())}")
        """뉴스 아이템 포맷팅"""
        return {
            'title': NewsSearcher.clean_html_tags(item.get('title', '')),
            'description': NewsSearcher.clean_html_tags(item.get('description', '')),
            'link': item.get('link', ''),
            'original_link': item.get('originallink', ''),
            'pub_date': item.get('pubDate', ''),
            'formatted_date': NewsSearcher.format_date(item.get('pubDate', ''))
        }

    @staticmethod
    def format_date(date_str: str) -> str:
        """날짜 포맷팅"""
        if not date_str:
            return ""
        try:
            dt = parser.parse(date_str)
            return dt.strftime("%Y-%m-%d %H:%M")
        except:
            return date_str
    
    @staticmethod
    def save_results_to_file(results: Dict, original_query: str = None, search_keywords: List[str] = None) -> None:
        """검색 결과를 파일로 저장"""
        now = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"/home/sese/Clova-RumAgent/rum_multi_agent/naver_news_searcher/log/news_search_results_{now}.txt"
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                # 검색 정보 헤더 추가
                f.write("=" * 60 + "\n")
                f.write(f"검색 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                if original_query:
                    f.write(f"원본 질문: {original_query}\n")
                if search_keywords:
                    f.write(f"생성된 검색 키워드: {', '.join(search_keywords)}\n")
                f.write(f"검색 결과 개수: {len(results.get('items', []))}개\n")
                f.write("=" * 60 + "\n\n")

                for item in results.get('items', []):
                    f.write(f"Title: {item['title']}\n")
                    f.write(f"Link: {item['link']}\n")
                    f.write(f"Date: {item['formatted_date']}\n")
                    f.write(f"Description: {item['description']}\n")
                    f.write("-" * 40 + "\n")
            print(f"검색 결과가 {filename}에 저장되었습니다.")
        except Exception as e:
            print(f"파일 저장 중 오류 발생: {e}")
        
if __name__ == "__main__":
    # 테스트 코드
    searcher = NewsSearcher()
    query = "방시혁 때문에 하이브 매출이 줄었어?"

    print("=== 키워드 기반 검색 테스트 ===")
    news_data = searcher.search_query(query, display=10, sort="date")
    for item in news_data.get('items', []):
        print(f"Title: {item['title']}")
        print(f"Link: {item['link']}")
        print(f"Date: {item['formatted_date']}")
        print(f"Description: {item['description']}")
        print("-" * 40)