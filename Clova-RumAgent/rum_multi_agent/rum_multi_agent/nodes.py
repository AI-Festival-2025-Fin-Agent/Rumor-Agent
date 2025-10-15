"""
검색 에이전트 노드 함수들
"""
import json
import asyncio
import concurrent.futures
from typing import Dict
from rum_multi_agent.state import SearchState
from naver_news_searcher.news_searcher import NewsSearcher
from pub_searcher.pub_searcher import search_publications
from langchain_naver import ChatClovaX
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI

class SearchNodes:
    """검색 노드 클래스"""

    def __init__(self, news_searcher: NewsSearcher = None):
        self.news_searcher = news_searcher

    def analyze_query(self, state: SearchState) -> SearchState:
        """쿼리 분석 노드"""
        if not state.get("search_preference"):
            state["search_preference"] = "both"

        if not state.get("news_errors"):
            state["news_errors"] = []
        if not state.get("pub_errors"):
            state["pub_errors"] = []

        return state

    def search_news(self, state: SearchState) -> SearchState:
        """뉴스 검색 노드"""
        print(f"[DEBUG] search_news node called")
        print(f"[DEBUG] Search preference: {state['search_preference']}")
        print(f"[DEBUG] Query: {state['query']}")

        if state["search_preference"] in ["news", "both"]:
            if not self.news_searcher:
                print(f"[DEBUG] News searcher not available")
                state["news_errors"].append("News searcher not available")
                state["news_results"] = None
            else:
                try:
                    print(f"[DEBUG] Calling news searcher...")
                    results = self.news_searcher.search_query(
                        state["query"],
                        display=20,
                        sort="sim"
                    )
                    print(f"[DEBUG] News search completed successfully")
                    state["news_results"] = results
                except Exception as e:
                    error_msg = f"News search failed: {e}"
                    print(f"[DEBUG] {error_msg}")
                    state["news_errors"].append(error_msg)
                    state["news_results"] = None
        else:
            print(f"[DEBUG] Skipping news search due to preference")

        # 부분 state 반환 (reducer가 병합 처리)
        return {
            "news_results": state["news_results"],
            "news_errors": state["news_errors"]
        }

    def search_publications(self, state: SearchState) -> SearchState:
        """출판물 검색 노드"""
        print(f"[DEBUG] search_publications node called")
        print(f"[DEBUG] Search preference: {state['search_preference']}")
        print(f"[DEBUG] Query: {state['query']}")

        if state["search_preference"] in ["publications", "both"]:
            try:
                print(f"[DEBUG] Calling search_publications function...")
                results = search_publications(state["query"], "both")
                print(f"[DEBUG] Publication search results: {type(results)}")
                state["publication_results"] = results
            except Exception as e:
                error_msg = f"Publication search failed: {e}"
                print(f"[DEBUG] {error_msg}")
                state["pub_errors"].append(error_msg)
                state["publication_results"] = None
        else:
            print(f"[DEBUG] Skipping publication search due to preference")

        # 부분 state 반환 (reducer가 병합 처리)
        return {
            "publication_results": state["publication_results"],
            "pub_errors": state["pub_errors"]
        }



    def format_results(self, state: SearchState) -> SearchState:
        """검색 결과를 정리하여 searched_list 생성"""

        # 뉴스 리스트 생성
        news_list = []
        if state.get("news_results") and "items" in state["news_results"]:
            for item in state["news_results"]["items"]:
                news_list.append({
                    "title": item["title"],
                    "date": item["formatted_date"],
                    "link": item["link"],
                    "description": item["description"]
                })

        # 정기보고서 리스트 생성
        regular_list = []
        if state.get("publication_results") and "regular_results" in state["publication_results"]:
            regular_results = state["publication_results"]["regular_results"]
            if "available_reports" in regular_results:
                for report in regular_results["available_reports"]:
                    if "processed_data" in report:
                        # LLM 선택용 데이터 (메타데이터만)
                        llm_data = {
                            "year": report.get("year"),
                            "quarter": report.get("quarter"),
                            "company_name": report.get("company_name"),
                            "filename": report.get("filename"),
                            "metadata": report["processed_data"].get("metadata", {}),
                            "api_keys": list(report["processed_data"].get("api_data", {}).keys())
                        }

                        # 실제 API 데이터도 저장 (generate_response에서 사용)
                        full_data = llm_data.copy()
                        full_data["api_data"] = report["processed_data"].get("api_data", {})

                        regular_list.append(full_data)

        # 정정보고서 리스트 생성
        revision_list = []
        if state.get("publication_results") and "revision_results" in state["publication_results"]:
            revision_results = state["publication_results"]["revision_results"]
            if "revision_documents" in revision_results:
                for doc in revision_results["revision_documents"]:
                    revision_list.append({
                        "basic_info": doc.get("basic_info", {}),
                        "content_length": doc.get("content_length", 0),
                        "index": doc.get("index")
                    })

        # searched_list 생성
        state["searched_list"] = {
            "news": news_list,
            "regular": regular_list,
            "revision": revision_list
        }

        # 요약 정보 생성
        news_count = len(news_list)
        regular_count = len(regular_list)
        revision_count = len(revision_list)

        all_errors = state.get("news_errors", []) + state.get("pub_errors", [])

        output = f"=== 검색 결과 요약: '{state['query']}' ===\n"
        output += f"📰 뉴스: {news_count}건\n"
        output += f"   뉴스 제목:\n"
        for news in news_list:
            output += f"   - {news['title']} ({news['date']})\n"
        output += f"📊 정기보고서: {regular_count}건\n"
        output += f"   회사명:\n"
        for report in regular_list:
            output += f"   - {report['company_name']} ({report['year']}년 {report['quarter']}분기)\n"
        output += f"🔄 정정보고서: {revision_count}건\n"
        output += f"   문서 인덱스:\n"
        for doc in revision_list:
            output += f"   - {doc['basic_info']['date']} {doc['basic_info']['report_name']}\n"

        if all_errors:
            output += f"\n⚠️ 에러 {len(all_errors)}건:\n"
            for error in all_errors:
                output += f"- {error}\n"

        state["search_summary"] = output

        # 메모리 절약을 위해 원본 큰 데이터 삭제 (searched_list에 필요한 정보는 이미 저장됨)
        state["news_results"] = None
        state["publication_results"] = None

        print(f"[DEBUG] Final formatted output:\n{output}")
        return state


class DocumentNodes:
    """LLM을 사용하여 관련성 높은 문서들을 선택하는 클래스"""

    def __init__(self):
        # API 키 설명 매핑
        self.api_descriptions = {
            "api_01": "증자(감자) 현황",
            "api_02": "배당에 관한 사항",
            "api_03": "자기주식 소각, 취득 및 처분 현황, 주주환원",
            "api_04": "최대주주 현황",
            "api_05": "최대주주 변동현황",
            "api_06": "소액주주 현황",
            "api_07": "임원 현황",
            "api_08": "직원 현황",
            "api_09": "이사·감사의 개인별 보수현황(5억원 이상)",
            "api_10": "이사·감사 전체의 보수현황(보수지급금액 - 이사·감사 전체)",
            "api_11": "개인별 보수지급 금액(5억이상 상위5인)",
            "api_12": "타법인 출자현황",
            "api_13": "주식의 총수 현황",
            "api_14": "채무증권 발행실적",
            "api_15": "기업어음증권 미상환 잔액",
            "api_16": "단기사채 미상환 잔액",
            "api_17": "회사채 미상환 잔액",
            "api_18": "신종자본증권 미상환 잔액",
            "api_19": "조건부 자본증권 미상환 잔액",
            "api_20": "회계감사인의 명칭 및 감사의견",
            "api_21": "감사용역체결현황",
            "api_22": "회계감사인과의 비감사용역 계약체결 현황",
            "api_23": "사외이사 및 그 변동현황",
            "api_24": "미등기임원 보수현황",
            "api_25": "이사·감사 전체의 보수현황(주주총회 승인금액)",
            "api_26": "이사·감사 전체의 보수현황(보수지급금액 - 유형별)",
            "api_27": "공모자금의 사용내역",
            "api_28": "사모자금의 사용내역"
        }

    def select_documents(self, state: SearchState) -> SearchState:
        """LLM을 사용하여 관련성 높은 문서들을 선택"""

        try:
            # gemini LLM 초기화
            llm = ChatGoogleGenerativeAI(
                model="gemini-2.0-flash",
                temperature=0
            )

            # 시스템 프롬프트
            system_prompt = """당신은 검색된 문서들 중에서 사용자 쿼리에 가장 관련성이 높은 문서들을 선택하는 AI 어시스턴트입니다.

다음 기준으로 문서를 선택하세요:
1. 사용자 쿼리와의 직접적 관련성
2. 정보의 신뢰성 (정기보고서 > 정정보고서 > 뉴스)
3. 정보의 최신성(현재 날짜는 25년 10월 입니다.)
4. 정보의 구체성

각 문서 유형별로 최대 선택 개수:
- 뉴스: 최대 3개
- 정기보고서: 최대 5개
- 정정보고서: 최대 5개

반드시 유효한 JSON 형태로 응답하세요. 주석이나 설명을 포함하지 마세요."""

            # API 키 설명 텍스트 생성
            api_desc_text = "\n".join([f"- {key}: {desc}" for key, desc in self.api_descriptions.items()])

            # searched_list에서 API 데이터 제외한 버전 생성 (LLM 입력용)
            searched_list_for_llm = {}
            if "news" in state['searched_list']:
                searched_list_for_llm["news"] = state['searched_list']["news"]

            if "regular" in state['searched_list']:
                searched_list_for_llm["regular"] = []
                for report in state['searched_list']["regular"]:
                    llm_report = {k: v for k, v in report.items() if k != "api_data"}
                    searched_list_for_llm["regular"].append(llm_report)

            if "revision" in state['searched_list']:
                searched_list_for_llm["revision"] = state['searched_list']["revision"]

            # 사용자 프롬프트
            user_prompt = f"""사용자 쿼리: "{state['query']}"

검색된 문서 목록:
{json.dumps(searched_list_for_llm, ensure_ascii=False, indent=2)}

위 문서들 중에서 사용자 쿼리에 가장 관련성이 높은 문서들을 선택하고, 선택 이유와 우선순위를 포함하여 JSON 형태로 응답해주세요.

정기보고서의 경우 관련성이 높은 API 키들만 선별해서 포함해주세요.
API 키 설명:
{api_desc_text}

응답 형식:
{{
    "news": [
        {{
            "title": "선택된 뉴스 제목",
            "date": "2024-10-09",
            "link": "...",
            "reason": "선택 이유",
            "priority": 1
        }}
    ],
    "regular": [
        {{
            "company_name": "회사명",
            "year": 2025,
            "quarter": 2,
            "filename": "파일명",
            "api_keys_to_check": ["api_01", "api_05"],
            "reason": "선택 이유",
            "priority": 1
        }}
    ],
    "revision": [
        {{
            "basic_info": {{}},
            "reason": "선택 이유",
            "priority": 2
        }}
    ],
    "selection_summary": "선택 요약"
}}"""

            # LLM 호출
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]

            response = llm.invoke(messages)
            response_text = response.content

            # JSON 파싱 시도
            try:
                # JSON 추출 (```json 블록이 있을 경우)
                if "```json" in response_text:
                    start = response_text.find("```json") + 7
                    end = response_text.find("```", start)
                    response_text = response_text[start:end].strip()

                selected_documents = json.loads(response_text)
                state["selected_documents"] = selected_documents

                print(f"[DEBUG] Documents selected by LLM: {json.dumps(selected_documents, ensure_ascii=False, indent=2)}")

            except json.JSONDecodeError as e:
                print(f"[DEBUG] JSON parsing failed: {e}")
                print(f"[DEBUG] Raw response: {response_text}")
                # 실패 시 기본값 설정
                state["selected_documents"] = {
                    "news": [],
                    "regular": [],
                    "revision": [],
                    "selection_summary": "문서 선택 중 오류 발생"
                }

        except Exception as e:
            print(f"[DEBUG] Document selection failed: {e}")
            # 실패 시 기본값 설정
            state["selected_documents"] = {
                "news": [],
                "regular": [],
                "revision": [],
                "selection_summary": "문서 선택 중 오류 발생"
            }

        return state


class GenerationNodes:
    """선택된 문서들을 기반으로 최종 답변을 생성하는 클래스"""

    def __init__(self):
        self.llm = ChatClovaX(
            model="HCX-007",
            thinking={"effort": "medium"}
        )

    def generate_response(self, state: SearchState) -> SearchState:
        """선택된 문서들을 분석하여 최종 답변 생성"""

        try:
            selected_documents = state.get("selected_documents", {})
            query = state.get("query", "")

            if not selected_documents or not any(selected_documents.values()):
                state["generated_response"] = "선택된 문서가 없어 답변을 생성할 수 없습니다."
                return state

            # 선택된 문서들의 내용 로딩
            document_contents = self._load_document_contents(selected_documents, state)

            # LLM을 사용하여 최종 답변 생성
            response = self._generate_final_answer(query, document_contents, selected_documents)

            state["generated_response"] = response

        except Exception as e:
            print(f"[DEBUG] Response generation failed: {e}")
            state["generated_response"] = f"답변 생성 중 오류가 발생했습니다: {str(e)}"

        return state

    def _load_document_contents(self, selected_documents: dict, state: SearchState) -> dict:
        """선택된 문서들의 실제 내용을 searched_list에서 추출"""

        contents = {
            "news": [],
            "regular": [],
            "revision": []
        }

        searched_list = state.get("searched_list", {})

        # 뉴스 내용 로딩 (searched_list에서 실제 내용 추출)
        for news_doc in selected_documents.get("news", []):
            # searched_list에서 해당 뉴스 찾기
            for news_item in searched_list.get("news", []):
                if news_item["title"] == news_doc["title"]:
                    contents["news"].append({
                        "title": news_item["title"],
                        "date": news_item["date"],
                        "description": news_item["description"],  # 실제 뉴스 전체 내용
                        "link": news_item["link"],
                        "reason": news_doc.get("reason", ""),
                        "priority": news_doc.get("priority", 1)
                    })
                    break

        # 정기보고서 내용 로딩 (searched_list에서 실제 API 데이터 추출)
        for reg_doc in selected_documents.get("regular", []):
            # searched_list에서 해당 정기보고서 찾기
            for report_item in searched_list.get("regular", []):
                if (report_item["company_name"] == reg_doc["company_name"] and
                    report_item["year"] == reg_doc["year"] and
                    report_item["quarter"] == reg_doc["quarter"]):

                    # 선택된 API 키들에 해당하는 데이터만 추출
                    selected_api_data = {}
                    api_keys_to_check = reg_doc.get("api_keys_to_check", [])

                    # searched_list에 api_data가 있다면 사용
                    if "api_data" in report_item:
                        for api_key in api_keys_to_check:
                            if api_key in report_item["api_data"]:
                                selected_api_data[api_key] = report_item["api_data"][api_key]

                    contents["regular"].append({
                        "company_name": reg_doc["company_name"],
                        "year": reg_doc["year"],
                        "quarter": reg_doc["quarter"],
                        "filename": reg_doc["filename"],
                        "api_keys_to_check": api_keys_to_check,
                        "api_data": selected_api_data,  # 실제 API 데이터
                        "metadata": report_item.get("metadata", {}),
                        "reason": reg_doc.get("reason", ""),
                        "priority": reg_doc.get("priority", 1)
                    })
                    break

        # 정정보고서 내용 로딩 (searched_list에서 실제 내용 추출)
        for rev_doc in selected_documents.get("revision", []):
            # searched_list에서 해당 정정보고서 찾기
            for revision_item in searched_list.get("revision", []):
                if revision_item["basic_info"] == rev_doc["basic_info"]:
                    contents["revision"].append({
                        "basic_info": revision_item["basic_info"],
                        "content_length": revision_item.get("content_length", 0),
                        "index": revision_item.get("index"),
                        "reason": rev_doc.get("reason", ""),
                        "priority": rev_doc.get("priority", 1)
                    })
                    break

        return contents


    def _generate_final_answer(self, query: str, document_contents: dict, selected_documents: dict) -> str:
        """LLM을 사용하여 최종 답변 생성"""

        # 시스템 프롬프트
        system_prompt = """당신은 금융 및 기업 정보 분석 전문가입니다.
사용자의 질문에 대해 제공된 문서들(뉴스, 정기보고서, 정정보고서)을 종합적으로 분석하여 정확하고 유용한 답변을 제공하세요.

답변 작성 가이드라인:
1. 사용자 질문에 직접적으로 답변하세요
2. 제공된 문서들의 핵심 정보를 요약하세요
3. 출처를 명확히 표시하세요 (뉴스, 정기보고서, 정정보고서)
4. 정보의 신뢰도를 고려하여 답변하세요
5. 부족한 정보가 있다면 명시하세요

답변 구조:
1. 질문에 대한 직접적인 답변
2. 주요 발견사항
3. 상세 분석 (문서별)
4. 결론 및 시사점
"""

        # 문서 내용을 텍스트로 변환
        documents_text = self._format_documents_for_llm(document_contents)

        # 사용자 프롬프트
        user_prompt = f"""
사용자 질문: "{query}"

분석할 문서들:
{documents_text}

위 문서들을 바탕으로 사용자 질문에 대한 종합적이고 정확한 답변을 작성해주세요.
"""

        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]

            response = self.llm.invoke(messages)
            print(f"[DEBUG] LLM response: {response.content}")
            return response.content

        except Exception as e:
            print(f"[DEBUG] LLM response generation failed: {e}")
            return f"답변 생성 중 오류가 발생했습니다: {str(e)}"

    def _format_documents_for_llm(self, document_contents: dict) -> str:
        """문서 내용을 LLM이 이해할 수 있는 형태로 포맷팅"""

        formatted_text = ""

        # 뉴스 문서들
        if document_contents.get("news"):
            formatted_text += "=== 뉴스 문서들 ===\n"
            for i, news in enumerate(document_contents["news"], 1):
                formatted_text += f"""
뉴스 {i} (우선순위: {news['priority']}):
제목: {news['title']}
날짜: {news['date']}
내용: {news['description']}
선택 이유: {news['reason']}
링크: {news['link']}
"""

        # 정기보고서 문서들
        if document_contents.get("regular"):
            formatted_text += "\n=== 정기보고서 문서들 ===\n"
            for i, report in enumerate(document_contents["regular"], 1):
                    
                formatted_text += f"""
정기보고서 {i} (우선순위: {report['priority']}):
회사명: {report['company_name']}
연도/분기: {report['year']}년 {report['quarter']}분기
분석 API: {', '.join(report['api_keys_to_check'])}
선택 이유: {report['reason']}

API 데이터:
"""




                for api_key, data in report.get("api_data", {}).items():
                    if api_key == 'api_03':
                        data = data.replace('change_qy_incnr','change_qy_dcrnr')
                    formatted_text += f"  - {api_key}: {data}\n"

        # 정정보고서 문서들
        if document_contents.get("revision"):
            formatted_text += "\n=== 정정보고서 문서들 ===\n"
            for i, revision in enumerate(document_contents["revision"], 1):
                basic_info = revision['basic_info']
                formatted_text += f"""
정정보고서 {i} (우선순위: {revision['priority']}):
회사: {basic_info.get('company', '')}
보고서명: {basic_info.get('report_name', '')}
제출일: {basic_info.get('date', '')}
선택 이유: {revision['reason']}
문서 길이: {revision.get('content_length', 0)}자
문서 인덱스: {revision.get('index', '')}
문서 URL: {basic_info.get('url', '')}
"""

        return formatted_text