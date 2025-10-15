"""
주식 뉴스 분석 시스템 메인 파일
"""

import logging
from datetime import datetime
from typing import Dict, List

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

from src.news_searcher import NewsSearcher
from src.ai_analyzer import AIAnalyzer
from src.result_storage import ResultStorage
from src.company_extractor import CompanyExtractor
from config.settings import SERVER_HOST, SERVER_PORT


# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI 앱 생성
app = FastAPI(
    title="🔍 Rumor Verification API",
    description="기업 루머 및 뉴스 팩트체킹 API",
    version="1.0.0"
)

# 전역 인스턴스
news_searcher = NewsSearcher()
ai_analyzer = AIAnalyzer()
result_storage = ResultStorage()
company_extractor = CompanyExtractor()


# 요청/응답 모델
class RumorVerificationRequest(BaseModel):
    rumor_text: str
    company_name: str
    news_count: int = 10


class AutoVerificationRequest(BaseModel):
    rumor_text: str
    news_count: int = 10


class RumorVerificationResponse(BaseModel):
    rumor_text: str
    company_name: str
    verification_result: str
    news_count: int
    status: str
    timestamp: str
    saved_file_path: str = ""


@app.get("/")
async def root():
    """API 상태 확인"""
    return {
        "message": "🔍 Rumor Verification API",
        "status": "running",
        "endpoints": {
            "auto-verify": "/auto-verify - 회사명 자동 추출 루머 검증",
            "verify": "/verify - 기업 루머 검증 (회사명 직접 입력)",
            "recent": "/recent - 최근 검증 결과 조회",
            "search": "/search - 검증 결과 검색",
            "health": "/health - 헬스 체크"
        }
    }


@app.get("/health")
async def health_check():
    """헬스 체크"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.post("/auto-verify", response_model=RumorVerificationResponse)
async def auto_verify_rumor(request: AutoVerificationRequest):
    """
    회사명 자동 추출 기능이 있는 루머 검증

    사용 예시:
    curl -X POST "http://localhost:8000/auto-verify" \
         -H "Content-Type: application/json" \
         -d '{"rumor_text": "삼성전자 이재용이 자사주 매입했다는 거 사실이야?", "news_count": 10}'
    """
    try:
        rumor_text = request.rumor_text.strip()

        if not rumor_text:
            raise HTTPException(status_code=400, detail="루머 내용을 입력해주세요.")

        # 1. AI로 회사명 추출
        logger.info(f"🤖 회사명 추출 중: {rumor_text}")
        extracted_company = company_extractor.extract_company_from_query(rumor_text)

        if not extracted_company:
            return RumorVerificationResponse(
                rumor_text=rumor_text,
                company_name="추출실패",
                verification_result="❌ 텍스트에서 회사명을 찾을 수 없습니다. 명확한 회사명을 포함해주세요.",
                news_count=0,
                status="no_company",
                timestamp=datetime.now().isoformat()
            )

        logger.info(f"✅ 추출된 회사명: {extracted_company}")

        # 2. 뉴스 검색
        news_results = news_searcher.search_stock_news(
            extracted_company,
            display=request.news_count,
            sort="date"
        )

        if not news_results or 'items' not in news_results or len(news_results['items']) == 0:
            return RumorVerificationResponse(
                rumor_text=rumor_text,
                company_name=extracted_company,
                verification_result="❌ 관련 뉴스를 찾을 수 없습니다. 회사명을 확인해주세요.",
                news_count=0,
                status="no_news",
                timestamp=datetime.now().isoformat()
            )

        # 3. 뉴스 목록 정리 및 데이터 구조화
        news_list = ""
        news_data = []
        for i, item in enumerate(news_results['items'], 1):
            formatted_item = news_searcher.format_news_item(item)
            news_list += f"{i}. 제목: {formatted_item['title']}\n"
            news_list += f"   내용: {formatted_item['description']}\n"
            news_list += f"   날짜: {formatted_item['formatted_date']}\n\n"

            news_data.append({
                "title": formatted_item['title'],
                "description": formatted_item['description'],
                "link": formatted_item.get('link', ''),
                "pub_date": formatted_item.get('pub_date', ''),
                "formatted_date": formatted_item['formatted_date']
            })

        # 4. AI 루머 검증 실행
        verification_result = ai_analyzer.verify_rumor(rumor_text, extracted_company, news_list)

        # 5. 결과 저장
        saved_file_path = result_storage.save_verification_result(
            rumor_text=rumor_text,
            company_name=extracted_company,
            news_count=request.news_count,
            news_data=news_data,
            analysis_details="",
            final_result=verification_result,
            status="success"
        )

        logger.info(f"✅ {extracted_company} 루머 검증 완료, 결과 저장: {saved_file_path}")

        return RumorVerificationResponse(
            rumor_text=rumor_text,
            company_name=extracted_company,
            verification_result=verification_result,
            news_count=len(news_results['items']),
            status="success",
            timestamp=datetime.now().isoformat(),
            saved_file_path=saved_file_path
        )

    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"분석 중 오류 발생: {str(e)}"
        logger.error(f"❌ {error_msg}")

        return RumorVerificationResponse(
            rumor_text=request.rumor_text,
            company_name="오류",
            verification_result=f"❌ {error_msg}",
            news_count=0,
            status="error",
            timestamp=datetime.now().isoformat()
        )


@app.post("/verify", response_model=RumorVerificationResponse)
async def verify_rumor(request: RumorVerificationRequest):
    """
    기업 루머 및 정보 팩트체킹

    사용 예시:
    curl -X POST "http://localhost:8000/verify" \
         -H "Content-Type: application/json" \
         -d '{"rumor_text": "삼성전자 이재용이 자사주 매입했다는 거 사실이야?", "company_name": "삼성전자", "news_count": 10}'
    """
    try:
        rumor_text = request.rumor_text.strip()
        company_name = request.company_name.strip()

        if not rumor_text:
            raise HTTPException(status_code=400, detail="루머 내용을 입력해주세요.")
        if not company_name:
            raise HTTPException(status_code=400, detail="회사명을 입력해주세요.")

        logger.info(f"🔍 {company_name} 루머 검증 시작: {rumor_text}")
        
        # 1. 뉴스 검색
        news_results = news_searcher.search_stock_news(
            company_name,
            display=request.news_count,
            sort="date"
        )

        if not news_results or 'items' not in news_results or len(news_results['items']) == 0:
            return RumorVerificationResponse(
                rumor_text=rumor_text,
                company_name=company_name,
                verification_result="❌ 관련 뉴스를 찾을 수 없습니다. 회사명을 확인해주세요.",
                news_count=0,
                status="no_news",
                timestamp=datetime.now().isoformat()
            )
        
        # 2. 뉴스 목록 정리 및 데이터 구조화
        news_list = ""
        news_data = []
        for i, item in enumerate(news_results['items'], 1):
            formatted_item = news_searcher.format_news_item(item)
            news_list += f"{i}. 제목: {formatted_item['title']}\n"
            news_list += f"   내용: {formatted_item['description']}\n"
            news_list += f"   날짜: {formatted_item['formatted_date']}\n\n"

            # 저장용 뉴스 데이터
            news_data.append({
                "title": formatted_item['title'],
                "description": formatted_item['description'],
                "link": formatted_item.get('link', ''),
                "pub_date": formatted_item.get('pub_date', ''),
                "formatted_date": formatted_item['formatted_date']
            })

        # 3. AI 루머 검증 실행
        verification_result = ai_analyzer.verify_rumor(rumor_text, company_name, news_list)

        # 4. 결과 저장
        saved_file_path = result_storage.save_verification_result(
            rumor_text=rumor_text,
            company_name=company_name,
            news_count=request.news_count,
            news_data=news_data,
            analysis_details="",  # 필요시 개별 뉴스 분석 결과 추가
            final_result=verification_result,
            status="success"
        )

        logger.info(f"✅ {company_name} 루머 검증 완료, 결과 저장: {saved_file_path}")

        return RumorVerificationResponse(
            rumor_text=rumor_text,
            company_name=company_name,
            verification_result=verification_result,
            news_count=len(news_results['items']),
            status="success",
            timestamp=datetime.now().isoformat(),
            saved_file_path=saved_file_path
        )
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"분석 중 오류 발생: {str(e)}"
        logger.error(f"❌ {error_msg}")
        
        return RumorVerificationResponse(
            rumor_text=request.rumor_text,
            company_name=request.company_name,
            verification_result=f"❌ {error_msg}",
            news_count=0,
            status="error",
            timestamp=datetime.now().isoformat()
        )


@app.get("/recent")
async def get_recent_verifications(limit: int = 10):
    """최근 검증 결과 조회"""
    try:
        recent_results = result_storage.get_recent_verifications(limit)
        return {
            "status": "success",
            "count": len(recent_results),
            "results": recent_results
        }
    except Exception as e:
        logger.error(f"최근 결과 조회 중 오류: {e}")
        raise HTTPException(status_code=500, detail=f"조회 중 오류 발생: {str(e)}")


@app.get("/search")
async def search_verifications(company_name: str = None, keyword: str = None):
    """검증 결과 검색"""
    try:
        if not company_name and not keyword:
            raise HTTPException(status_code=400, detail="company_name 또는 keyword 중 하나는 필수입니다.")

        search_results = result_storage.search_verifications(company_name, keyword)
        return {
            "status": "success",
            "count": len(search_results),
            "results": search_results
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"검색 중 오류: {e}")
        raise HTTPException(status_code=500, detail=f"검색 중 오류 발생: {str(e)}")


@app.get("/verification/{verification_id}")
async def get_verification_detail(verification_id: str):
    """특정 검증 결과 상세 조회"""
    try:
        result = result_storage.get_verification_by_id(verification_id)
        if not result:
            raise HTTPException(status_code=404, detail="검증 결과를 찾을 수 없습니다.")

        return {
            "status": "success",
            "result": result
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"상세 조회 중 오류: {e}")
        raise HTTPException(status_code=500, detail=f"조회 중 오류 발생: {str(e)}")


def verify_rumor_cli(rumor_text: str, company_name: str, news_count: int = 10):
    """CLI용 루머 검증 함수"""
    try:
        print(f"🔍 {company_name} 루머 검증 중: {rumor_text}")

        # 뉴스 검색
        news_results = news_searcher.search_stock_news(company_name, display=news_count, sort="date")
        
        if not news_results or 'items' not in news_results or len(news_results['items']) == 0:
            print("❌ 관련 뉴스를 찾을 수 없습니다.")
            return
        
        print(f"📰 {len(news_results['items'])}개 뉴스 발견")
        
        # 뉴스 목록 정리
        news_list = ""
        for i, item in enumerate(news_results['items'], 1):
            formatted_item = news_searcher.format_news_item(item)
            news_list += f"{i}. 제목: {formatted_item['title']}\n"
            news_list += f"   내용: {formatted_item['description']}\n"
            news_list += f"   날짜: {formatted_item['formatted_date']}\n\n"
        
        # AI 루머 검증
        print("🤖 AI 루머 검증 중...")
        verification_result = ai_analyzer.verify_rumor(rumor_text, company_name, news_list)

        print("\n" + "="*60)
        print(verification_result)
        print("="*60)
        
    except Exception as e:
        print(f"❌ 루머 검증 중 오류 발생: {str(e)}")


def run_server(host: str = SERVER_HOST, port: int = SERVER_PORT):
    """서버 실행"""
    print(f"🚀 서버 시작: http://{host}:{port}")
    print("📝 사용법:")
    print(f"   curl -X POST 'http://{host}:{port}/verify' \\")
    print("        -H 'Content-Type: application/json' \\")
    print("        -d '{\"rumor_text\": \"삼성전자 이재용이 자사주 매입했다는 거 사실이야?\", \"company_name\": \"삼성전자\"}'")
    
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # CLI 모드
        if len(sys.argv) < 3:
            print("사용법: python main.py \"<루머 내용>\" \"<회사명>\" [<뉴스 개수>]")
            print("예시: python main.py \"삼성전자 이재용이 자사주 매입했다는 거 사실이야?\" \"삼성전자\"")
            exit(1)
        rumor_text = sys.argv[1]
        company_name = sys.argv[2]
        news_count = int(sys.argv[3]) if len(sys.argv) > 3 else 10
        verify_rumor_cli(rumor_text, company_name, news_count)
    else:
        # 서버 모드
        run_server()