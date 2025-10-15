"""
검색 에이전트 엣지 함수들
"""
from rum_multi_agent.state import SearchState


class SearchEdges:
    """검색 엣지 클래스"""

    @staticmethod
    def route_search(state: SearchState) -> str:
        """검색 라우팅 결정"""
        preference = state["search_preference"]

        if preference == "news":
            return "news_only"
        elif preference == "publications":
            return "pub_only"
        else:
            return "both"