"""
검색 에이전트 상태 정의
"""
from typing import Dict, List, Optional, TypedDict, Annotated


def merge_lists(left: List, right: List) -> List:
    """리스트 병합 함수"""
    return left + right if right else left


class SearchState(TypedDict):
    """검색 상태 정의"""
    query: str
    search_preference: str  # "news", "publications", "both"
    news_results: Optional[Dict]
    publication_results: Optional[Dict]
    news_errors: Annotated[List[str], merge_lists]  # 뉴스 검색 에러
    pub_errors: Annotated[List[str], merge_lists]   # 출판물 검색 에러
    searched_list: Optional[Dict]  # 정리된 검색 결과 리스트
    search_summary: str  # 검색 결과 요약
    selected_documents: Optional[Dict]  # LLM이 선택한 확인할 문서들
    generated_response: Optional[str]  # 최종 생성된 답변 (LangGraph CLI 배포용)