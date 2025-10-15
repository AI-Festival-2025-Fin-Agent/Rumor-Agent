"""
회사명 추출 모듈
사용자 쿼리에서 회사명을 추출하는 기능
"""

from typing import Dict, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_naver import ChatClovaX
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from dotenv import load_dotenv

from config.settings import GOOGLE_API_KEY, LLM_MODEL, LLM_TEMPERATURE

load_dotenv()


class CompanyExtractor:
    """사용자 쿼리에서 회사명을 추출하는 클래스"""

    def __init__(self):
        """초기화"""
        # Clova HCX-007 사용 (원본 코드와 동일)
        try:
            self.llm = ChatClovaX(
                model="HCX-007",
                temperature=0.1
            )
        except:
            # Clova 사용 불가시 Google Gemini 백업
            self.llm = ChatGoogleGenerativeAI(
                model=LLM_MODEL,
                temperature=LLM_TEMPERATURE,
                api_key=GOOGLE_API_KEY,
            )

    def extract_company_from_query(self, query: str) -> Optional[str]:
        """사용자 질문에서 회사명만 추출"""
        parser = JsonOutputParser()

        prompt = ChatPromptTemplate.from_template(
            """당신은 정보 추출 어시스턴트입니다.
            사용자의 질문에서 'company_name' 정보만 추출하는 것이 당신의 임무입니다.
            - 반드시 JSON 객체 형식으로만 답변해야 합니다.
            - JSON 객체는 반드시 'company_name' 키를 포함해야 합니다.
            - 어떤 설명도 추가하지 말고, JSON 객체만 반환하세요.
            - 회사명이 명확하지 않거나 없으면 null을 반환하세요.

            # 회사명 정규화 규칙 (줄임말을 정식명칭으로 변환)
            - "lg엔솔", "엘지엔솔", "lg 엔솔" → "LG에너지솔루션"
            - "카카오뱅크" → "카카오뱅크"
            - "kakao" → "카카오"
            - "삼전" → "삼성전자"
            - "현대차" → "현대자동차"
            - "sk하이닉스", "sk 하이닉스" → "SK하이닉스"
            - "네이버" → "NAVER"
            - 기타 줄임말이나 영문명이 나올 경우 가장 일반적인 한국 정식 회사명으로 변환

            # 예시
            - 사용자 질문: "삼성전자 주가가 어떻게 될까?"
            - JSON: {{"company_name": "삼성전자"}}
            - 사용자 질문: "카카오 실적"
            - JSON: {{"company_name": "카카오"}}
            - 사용자 질문: "lg엔솔 최근 소식"
            - JSON: {{"company_name": "LG에너지솔루션"}}
            - 사용자 질문: "주식 투자 방법이 궁금해"
            - JSON: {{"company_name": null}}

            사용자 질문: {query}
            {format_instructions}
            """
        )

        chain = prompt | self.llm | parser

        try:
            result = chain.invoke({
                "query": query,
                "format_instructions": parser.get_format_instructions()
            })
            return result.get("company_name")
        except Exception as e:
            print(f"회사명 추출 중 오류 발생: {e}")
            return None

    def extract_info_from_query(self, query: str) -> Optional[Dict]:
        """사용자 질문에서 회사명, 연도, 분기 추출 (원본 기능)"""
        parser = JsonOutputParser()

        prompt = ChatPromptTemplate.from_template(
            """당신은 정보 추출 어시스턴트입니다.
            사용자의 질문에서 'company_name', 'year', 'quarter' 정보를 추출하는 것이 당신의 임무입니다.
            - 반드시 JSON 객체 형식으로만 답변해야 합니다.
            - JSON 객체는 반드시 'company_name', 'year', 'quarter' 키를 포함해야 합니다.
            - 연도가 명시되지 않은 경우, 현재 연도인 2025년을 사용하세요.
            - 분기가 명시되지 않은 경우, 가장 최신 분기인 2025년 1분기를 사용하세요.
            - 분기는 반드시 1, 2, 3, 4 중 하나의 숫자여야 합니다.
            - 어떤 설명도 추가하지 말고, JSON 객체만 반환하세요.

            # 회사명 정규화 규칙 (줄임말을 정식명칭으로 변환)
            - "lg엔솔", "엘지엔솔", "lg 엔솔" → "LG에너지솔루션"
            - "카카오뱅크" → "카카오뱅크"
            - "kakao" → "카카오"
            - "삼전" → "삼성전자" (만약 삼성전자를 의미하는 경우)
            - "현대차" → "현대자동차"
            - "sk하이닉스", "sk 하이닉스" → "SK하이닉스"
            - "네이버" → "NAVER"
            - 기타 줄임말이나 영문명이 나올 경우 가장 일반적인 한국 정식 회사명으로 변환

            # 예시
            - 사용자 질문: "삼성전자 작년 1분기 실적 알려줘"
            - JSON: {{"company_name": "삼성전자", "year": 2024, "quarter": 1}}
            - 사용자 질문: "카카오 실적"
            - JSON: {{"company_name": "카카오", "year": 2025, "quarter": 1}}
            - 사용자 질문: "lg엔솔 최근 실적"
            - JSON: {{"company_name": "LG에너지솔루션", "year": 2025, "quarter": 1}}

            사용자 질문: {query}
            {format_instructions}
            """
        )

        chain = prompt | self.llm | parser

        try:
            info = chain.invoke({
                "query": query,
                "format_instructions": parser.get_format_instructions()
            })
            return info
        except Exception as e:
            print(f"정보 추출 중 오류 발생: {e}")
            return None