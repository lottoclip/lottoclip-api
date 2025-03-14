#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import requests
from bs4 import BeautifulSoup
import logging
import time
import re
from pathlib import Path

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger('store_updater')

# 상수 정의
DATA_DIR = Path("lotto")
STORES_DIR = Path("lotto/stores")
STORES_FILE = DATA_DIR / "lotto_stores.json"
BASE_URL = "https://dhlottery.co.kr"
STORE_DETAIL_URL = f"{BASE_URL}/store.do?method=topStoreLocation&gbn=lotto&rtlrId="

def update_store_files():
    """판매점 정보 파일에서 type 필드를 제거합니다."""
    # 개별 파일 업데이트
    for file_path in STORES_DIR.glob("*.json"):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # type 필드 제거
            if 'type' in data:
                del data['type']
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
            logger.info(f"파일 업데이트 완료: {file_path}")
        except Exception as e:
            logger.error(f"파일 업데이트 실패: {file_path} - {e}")
    
    # 통합 파일 업데이트
    if os.path.exists(STORES_FILE):
        try:
            with open(STORES_FILE, 'r', encoding='utf-8') as f:
                stores_data = json.load(f)
            
            # 각 판매점 정보에서 type 필드 제거
            for store_id, store_info in stores_data.items():
                if 'type' in store_info:
                    del store_info['type']
            
            with open(STORES_FILE, 'w', encoding='utf-8') as f:
                json.dump(stores_data, f, ensure_ascii=False, indent=2)
                
            logger.info(f"통합 파일 업데이트 완료: {STORES_FILE}")
        except Exception as e:
            logger.error(f"통합 파일 업데이트 실패: {STORES_FILE} - {e}")

def get_store_detail(store_id):
    """판매점 상세 정보 페이지에서 전화번호와 취급복권 정보를 크롤링합니다."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        url = f"{STORE_DETAIL_URL}{store_id}"
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        # EUC-KR 인코딩 처리
        content = response.content.decode('euc-kr', errors='replace')
        soup = BeautifulSoup(content, 'lxml')
        
        # 판매점 정보 추출
        store_info = {}
        
        # 전화번호 추출
        phone_elem = soup.select_one('th:contains("전화번호") + td')
        if phone_elem:
            store_info['phone'] = phone_elem.text.strip()
        
        # 취급복권 추출
        lottery_types = []
        lottery_elems = soup.select('td img[src*="ico_seller"]')
        
        for elem in lottery_elems:
            src = elem.get('src', '')
            if '645' in src:
                lottery_types.append('lotto645')
            elif '720' in src:
                lottery_types.append('pension720')
            elif 'speetto' in src:
                lottery_types.append('speetto')
        
        if lottery_types:
            store_info['lottery_types'] = lottery_types
        
        logger.info(f"판매점 {store_id} 상세 정보 크롤링 완료: {store_info}")
        return store_info
        
    except Exception as e:
        logger.error(f"판매점 {store_id} 상세 정보 크롤링 실패: {e}")
        return None

def update_store_with_details(store_id):
    """특정 판매점의 정보를 상세 정보로 업데이트합니다."""
    # 개별 파일 경로
    file_path = STORES_DIR / f"{store_id}.json"
    
    if not os.path.exists(file_path):
        logger.error(f"판매점 파일이 존재하지 않습니다: {file_path}")
        return False
    
    try:
        # 기존 정보 로드
        with open(file_path, 'r', encoding='utf-8') as f:
            store_data = json.load(f)
        
        # 상세 정보 가져오기
        detail_info = get_store_detail(store_id)
        if not detail_info:
            return False
        
        # 정보 업데이트
        store_data.update(detail_info)
        
        # 파일 저장
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(store_data, f, ensure_ascii=False, indent=2)
        
        # 통합 파일 업데이트
        update_integrated_store_file(store_id, store_data)
        
        logger.info(f"판매점 {store_id} 정보 업데이트 완료")
        return True
        
    except Exception as e:
        logger.error(f"판매점 {store_id} 정보 업데이트 실패: {e}")
        return False

def update_integrated_store_file(store_id, store_data):
    """통합 판매점 정보 파일을 업데이트합니다."""
    if os.path.exists(STORES_FILE):
        try:
            with open(STORES_FILE, 'r', encoding='utf-8') as f:
                stores_data = json.load(f)
            
            # 판매점 정보 업데이트
            stores_data[store_id] = store_data
            
            with open(STORES_FILE, 'w', encoding='utf-8') as f:
                json.dump(stores_data, f, ensure_ascii=False, indent=2)
                
            logger.info(f"통합 파일에 판매점 {store_id} 정보 업데이트 완료")
            return True
        except Exception as e:
            logger.error(f"통합 파일 업데이트 실패: {e}")
            return False
    else:
        logger.error(f"통합 파일이 존재하지 않습니다: {STORES_FILE}")
        return False

def update_all_stores_with_details(limit=None):
    """모든 판매점 정보를 상세 정보로 업데이트합니다."""
    # 모든 판매점 파일 목록 가져오기
    store_files = list(STORES_DIR.glob("*.json"))
    
    if limit:
        store_files = store_files[:limit]
    
    total = len(store_files)
    success = 0
    
    for i, file_path in enumerate(store_files):
        store_id = file_path.stem
        logger.info(f"[{i+1}/{total}] 판매점 {store_id} 정보 업데이트 중...")
        
        if update_store_with_details(store_id):
            success += 1
        
        # 서버 부하 방지를 위한 딜레이
        time.sleep(1)
    
    logger.info(f"판매점 정보 업데이트 완료: {success}/{total}개 성공")
    return success

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='판매점 정보 업데이트 도구')
    parser.add_argument('--remove-type', action='store_true', help='판매점 정보에서 type 필드 제거')
    parser.add_argument('--store-id', type=str, help='특정 판매점 ID의 상세 정보 업데이트')
    parser.add_argument('--update-all', action='store_true', help='모든 판매점의 상세 정보 업데이트')
    parser.add_argument('--limit', type=int, help='업데이트할 판매점 수 제한 (--update-all과 함께 사용)')
    
    args = parser.parse_args()
    
    if args.remove_type:
        update_store_files()
    elif args.store_id:
        update_store_with_details(args.store_id)
    elif args.update_all:
        update_all_stores_with_details(args.limit)
    else:
        parser.print_help() 