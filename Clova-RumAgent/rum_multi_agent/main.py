"""
메인 실행 파일
"""
from search_agent import SearchAgent


def main():
    """메인 실행 함수"""
    agent = SearchAgent()

    # 예시 사용
    query = "하이브"

    print("=== LangGraph 통합 검색 테스트 ===")
    results = agent.search(query, preference="both")
    agent.print_results(results)

    print("\n=== 뉴스만 검색 테스트 ===")
    news_results = agent.search(query, preference="news")
    agent.print_results(news_results)


if __name__ == "__main__":
    main()