#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
from pathlib import Path

# 상수 정의
DATA_DIR = Path("data")
STORES_DIR = Path("data/stores")
STORES_FILE = DATA_DIR / "lotto_stores.json"

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
                
            print(f"파일 업데이트 완료: {file_path}")
        except Exception as e:
            print(f"파일 업데이트 실패: {file_path} - {e}")
    
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
                
            print(f"통합 파일 업데이트 완료: {STORES_FILE}")
        except Exception as e:
            print(f"통합 파일 업데이트 실패: {STORES_FILE} - {e}")

if __name__ == "__main__":
    update_store_files() 