"""
LangGraph 기반 통합 검색 에이전트
"""
from typing import Dict
from langgraph.graph import StateGraph, END
from naver_news_searcher.news_searcher import NewsSearcher

from rum_multi_agent.state import SearchState
from rum_multi_agent.nodes import SearchNodes
from rum_multi_agent.edges import SearchEdges


class RumMultiAgent:
    """LangGraph 기반 통합 검색 에이전트"""

    def __init__(self, naver_client_id: str = None, naver_client_secret: str = None):
        """초기화"""
        try:
            news_searcher = NewsSearcher(naver_client_id, naver_client_secret)
        except ValueError as e:
            print(f"Warning: News searcher initialization failed: {e}")
            news_searcher = None

        self.nodes = SearchNodes(news_searcher)
        self.edges = SearchEdges()

        # LangGraph 워크플로우 생성
        self.workflow = self._create_workflow()
        self.app = self.workflow.compile()

    def _create_workflow(self) -> StateGraph:
        """LangGraph 워크플로우 생성"""
        workflow = StateGraph(SearchState)

        # 노드 추가
        workflow.add_node("analyze_query", self.nodes.analyze_query)
        workflow.add_node("search_news", self.nodes.search_news)
        workflow.add_node("search_publications", self.nodes.search_publications)
        workflow.add_node("format_results", self.nodes.format_results)

        # 엣지 정의
        workflow.set_entry_point("analyze_query")

        # 조건부 라우팅
        workflow.add_conditional_edges(
            "analyze_query",
            self.edges.route_search,
            {
                "news_only": "search_news",
                "pub_only": "search_publications",
                "both": "search_news"
            }
        )

        workflow.add_edge("search_news", "search_publications")
        workflow.add_edge("search_publications", "format_results")
        workflow.add_edge("format_results", END)

        return workflow

    def search(self, query: str, preference: str = "both") -> Dict:
        """검색 실행"""
        initial_state = SearchState(
            query=query,
            search_preference=preference,
            news_results=None,
            publication_results=None,
            errors=[],
            search_summary=""
        )

        # LangGraph 워크플로우 실행
        final_state = self.app.invoke(initial_state)

        return {
            "query": final_state["query"],
            "news_results": final_state["news_results"],
            "publication_results": final_state["publication_results"],
            "errors": final_state["errors"],
            "formatted_output": final_state["search_summary"]
        }

    def print_results(self, results: Dict):
        """결과 출력"""
        print(results["formatted_output"])