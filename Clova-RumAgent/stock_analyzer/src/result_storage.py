"""
결과 저장 모듈
"""

import json
import uuid
from datetime import datetime
from typing import Dict, List, Any
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class ResultStorage:
    """루머 검증 결과 저장 클래스"""

    def __init__(self, storage_dir: str = "verification_results"):
        """초기화"""
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)

        # 날짜별 폴더 생성
        today = datetime.now().strftime("%Y-%m-%d")
        self.daily_dir = self.storage_dir / today
        self.daily_dir.mkdir(exist_ok=True)

        logger.info(f"결과 저장 디렉토리: {self.daily_dir}")

    def save_verification_result(
        self,
        rumor_text: str,
        company_name: str,
        news_count: int,
        news_data: List[Dict[str, Any]],
        analysis_details: str,
        final_result: str,
        status: str
    ) -> str:
        """루머 검증 결과 저장"""
        try:
            # 고유 ID 생성
            verification_id = str(uuid.uuid4())[:8]
            timestamp = datetime.now().isoformat()

            # 저장할 데이터 구조
            result_data = {
                "id": verification_id,
                "timestamp": timestamp,
                "request": {
                    "rumor_text": rumor_text,
                    "company_name": company_name,
                    "news_count": news_count
                },
                "news_data": news_data,
                "analysis_details": analysis_details,
                "final_result": final_result,
                "status": status,
                "metadata": {
                    "total_news_found": len(news_data),
                    "processing_time": timestamp
                }
            }

            # 파일명 생성 (회사명_시간_ID.json)
            safe_company_name = "".join(c for c in company_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
            time_str = datetime.now().strftime("%H%M%S")
            filename = f"{safe_company_name}_{time_str}_{verification_id}.json"

            # 파일 저장
            file_path = self.daily_dir / filename
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(result_data, f, ensure_ascii=False, indent=2)

            # 인덱스 파일 업데이트
            self._update_index(verification_id, rumor_text, company_name, timestamp, filename)

            logger.info(f"결과 저장 완료: {file_path}")
            return str(file_path)

        except Exception as e:
            logger.error(f"결과 저장 중 오류: {e}")
            return ""

    def _update_index(self, verification_id: str, rumor_text: str, company_name: str, timestamp: str, filename: str):
        """인덱스 파일 업데이트 (검색용)"""
        try:
            index_file = self.storage_dir / "index.json"

            # 기존 인덱스 로드
            if index_file.exists():
                with open(index_file, 'r', encoding='utf-8') as f:
                    index_data = json.load(f)
            else:
                index_data = {"verifications": []}

            # 새 항목 추가
            index_entry = {
                "id": verification_id,
                "timestamp": timestamp,
                "rumor_text": rumor_text[:100] + "..." if len(rumor_text) > 100 else rumor_text,
                "company_name": company_name,
                "filename": filename,
                "date": datetime.now().strftime("%Y-%m-%d")
            }

            index_data["verifications"].append(index_entry)

            # 최근 100개만 유지
            index_data["verifications"] = index_data["verifications"][-100:]

            # 인덱스 파일 저장
            with open(index_file, 'w', encoding='utf-8') as f:
                json.dump(index_data, f, ensure_ascii=False, indent=2)

        except Exception as e:
            logger.error(f"인덱스 업데이트 중 오류: {e}")

    def get_recent_verifications(self, limit: int = 10) -> List[Dict[str, Any]]:
        """최근 검증 결과 목록 조회"""
        try:
            index_file = self.storage_dir / "index.json"

            if not index_file.exists():
                return []

            with open(index_file, 'r', encoding='utf-8') as f:
                index_data = json.load(f)

            # 최근 순으로 정렬하여 반환
            recent = sorted(
                index_data.get("verifications", []),
                key=lambda x: x["timestamp"],
                reverse=True
            )

            return recent[:limit]

        except Exception as e:
            logger.error(f"최근 검증 결과 조회 중 오류: {e}")
            return []

    def get_verification_by_id(self, verification_id: str) -> Dict[str, Any]:
        """ID로 특정 검증 결과 조회"""
        try:
            # 인덱스에서 파일명 찾기
            index_file = self.storage_dir / "index.json"

            if not index_file.exists():
                return {}

            with open(index_file, 'r', encoding='utf-8') as f:
                index_data = json.load(f)

            for verification in index_data.get("verifications", []):
                if verification["id"] == verification_id:
                    # 해당 날짜 폴더에서 파일 로드
                    date_dir = self.storage_dir / verification["date"]
                    file_path = date_dir / verification["filename"]

                    if file_path.exists():
                        with open(file_path, 'r', encoding='utf-8') as f:
                            return json.load(f)

            return {}

        except Exception as e:
            logger.error(f"검증 결과 조회 중 오류: {e}")
            return {}

    def search_verifications(self, company_name: str = None, keyword: str = None) -> List[Dict[str, Any]]:
        """회사명이나 키워드로 검색"""
        try:
            index_file = self.storage_dir / "index.json"

            if not index_file.exists():
                return []

            with open(index_file, 'r', encoding='utf-8') as f:
                index_data = json.load(f)

            results = []
            for verification in index_data.get("verifications", []):
                match = True

                if company_name and company_name.lower() not in verification["company_name"].lower():
                    match = False

                if keyword and keyword.lower() not in verification["rumor_text"].lower():
                    match = False

                if match:
                    results.append(verification)

            # 최근 순으로 정렬
            return sorted(results, key=lambda x: x["timestamp"], reverse=True)

        except Exception as e:
            logger.error(f"검증 결과 검색 중 오류: {e}")
            return []