#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
scripts/add_province_city.py
────────────────────────────
lotto/stores/ 아래 모든 개별 판매점 JSON 파일에
province(시도), city(시군구) 필드를 일괄 추가합니다.

크롤러를 다시 실행하지 않고 기존 address 값을 파싱해
두 필드를 삽입한 뒤, 순서를 맞춰 파일을 덮어씁니다.

사용:
    python scripts/add_province_city.py            # 전체 실행
    python scripts/add_province_city.py --dry-run  # 변경 없이 미리보기만
"""

import sys
import os
import json
import argparse
import logging
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가 (src 패키지 임포트 가능)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.crawler import parse_address_parts  # 주소 파싱 유틸 재사용

# ── 설정 ──────────────────────────────────────────────────────────────────────
STORES_DIR = Path("lotto/stores")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("add_province_city")


def process_store_file(file_path: Path, dry_run: bool = False) -> bool:
    """단일 판매점 JSON 파일에 province/city 필드를 추가합니다.

    - index.json / index.csv 파일은 건너뜁니다.
    - 이미 province 필드가 있어도 최신 파싱 결과로 업데이트합니다.

    Returns:
        True  : 파일이 수정(또는 수정 예정)됐을 때
        False : 스킵하거나 오류가 발생했을 때
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        address = data.get("address", "") or ""
        province, city = parse_address_parts(address)

        # 변경이 없으면 파일 I/O 생략
        if data.get("province") == province and data.get("city") == city:
            return False

        if dry_run:
            # 미리보기 모드: 파일은 건드리지 않음
            logger.info(
                f"[DRY-RUN] {file_path.name}: province={province!r}, city={city!r}"
            )
            return True

        # ── 필드 순서를 보기 좋게 재구성 ───────────────────────────────────
        # address 바로 다음에 province, city 삽입
        ordered_data = {}
        for key, value in data.items():
            ordered_data[key] = value
            if key == "address":
                ordered_data["province"] = province
                ordered_data["city"] = city

        # address 키가 없는 엣지 케이스 처리 (마지막에라도 추가)
        if "province" not in ordered_data:
            ordered_data["province"] = province
        if "city" not in ordered_data:
            ordered_data["city"] = city

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(ordered_data, f, ensure_ascii=False, indent=2)

        return True

    except Exception as e:
        logger.error(f"처리 실패: {file_path} — {e}")
        return False


def run(dry_run: bool = False):
    """STORES_DIR 내 모든 개별 판매점 파일을 일괄 처리합니다."""
    # index.json / index.csv 는 개별 판매점 파일이 아니므로 제외
    store_files = [
        p for p in STORES_DIR.glob("*.json")
        if p.name not in ("index.json",)
    ]

    total = len(store_files)
    updated = 0
    skipped = 0

    logger.info(f"처리 대상: {total}개 파일 (dry_run={dry_run})")

    for i, file_path in enumerate(store_files, 1):
        changed = process_store_file(file_path, dry_run=dry_run)
        if changed:
            updated += 1
        else:
            skipped += 1

        # 1,000개마다 진행 상황 로그
        if i % 1000 == 0:
            logger.info(f"  진행: {i}/{total} (갱신={updated}, 스킵={skipped})")

    logger.info(
        f"완료: 전체={total}, 갱신={updated}, 스킵(변경없음/오류)={skipped}"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="개별 판매점 JSON에 province/city 필드를 일괄 추가합니다."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="실제 파일을 변경하지 않고 결과만 출력합니다.",
    )
    args = parser.parse_args()
    run(dry_run=args.dry_run)
