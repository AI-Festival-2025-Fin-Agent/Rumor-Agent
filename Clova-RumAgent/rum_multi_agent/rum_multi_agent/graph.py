"""
LangGraph Studio용 검색 그래프 정의
"""
from langgraph.graph import StateGraph, END
from naver_news_searcher.news_searcher import NewsSearcher

from rum_multi_agent.state import SearchState
from rum_multi_agent.nodes import SearchNodes, DocumentNodes, GenerationNodes
from rum_multi_agent.edges import SearchEdges


def create_search_graph():
    """검색 그래프 생성"""
    # News searcher 초기화 (환경변수에서 자동 로드)
    try:
        news_searcher = NewsSearcher()
    except ValueError as e:
        print(f"Warning: News searcher initialization failed: {e}")
        news_searcher = None

    nodes = SearchNodes(news_searcher)
    doc_nodes = DocumentNodes()
    gen_nodes = GenerationNodes()
    edges = SearchEdges()

    # StateGraph 생성
    workflow = StateGraph(SearchState)

    # 노드 추가
    workflow.add_node("analyze_query", nodes.analyze_query)
    workflow.add_node("search_news", nodes.search_news)
    workflow.add_node("search_publications", nodes.search_publications)
    workflow.add_node("format_results", nodes.format_results)
    workflow.add_node("select_documents", doc_nodes.select_documents)
    workflow.add_node("generate_response", gen_nodes.generate_response)

    # 엣지 정의 - 병렬 실행 구조
    workflow.set_entry_point("analyze_query")

    # analyze_query에서 두 검색 노드로 병렬 분기
    workflow.add_edge("analyze_query", "search_news")
    workflow.add_edge("analyze_query", "search_publications")

    # 두 검색 노드에서 format_results로 수렴
    workflow.add_edge("search_news", "format_results")
    workflow.add_edge("search_publications", "format_results")
    workflow.add_edge("format_results", "select_documents")
    workflow.add_edge("select_documents", "generate_response")
    workflow.add_edge("generate_response", END)

    return workflow


# LangGraph Studio에서 사용할 그래프 인스턴스
graph = create_search_graph().compile()