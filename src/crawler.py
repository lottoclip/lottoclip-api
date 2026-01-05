#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import requests
import datetime
import re
import logging
from pathlib import Path

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger('lotto_crawler')

# 상수 정의
BASE_URL = "https://dhlottery.co.kr"
LOTTO_DRAW_URL = f"{BASE_URL}/lt645/selectPstLt645Info.do"
LOTTO_STORE_URL = f"{BASE_URL}/wnprchsplcsrch/selectLtWnShp.do"
DATA_DIR = Path("lotto")
DRAWS_DIR = DATA_DIR / "draws"  # 회차별 데이터 디렉토리 추가
STORES_DIR = Path("lotto/stores")
STORES_FILE = DATA_DIR / "lotto_stores.json"

class LottoCrawler:
    def __init__(self):
        """로또 크롤러 초기화"""
        self.session = requests.Session()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # 데이터 디렉토리 생성
        os.makedirs(DATA_DIR, exist_ok=True)
        os.makedirs(DRAWS_DIR, exist_ok=True)  # 회차별 데이터 디렉토리 생성
        os.makedirs(STORES_DIR, exist_ok=True)
        
        # 통합 판매점 정보 파일 로드
        self.stores_data = self.load_stores_data()
        
    def load_stores_data(self):
        """통합 판매점 정보 파일을 로드합니다."""
        if os.path.exists(STORES_FILE):
            try:
                with open(STORES_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"통합 판매점 정보 파일 로드 실패: {e}")
        
        # 파일이 없거나 로드 실패 시 빈 객체 반환
        return {}
    
    def save_stores_data(self):
        """통합 판매점 정보 파일을 저장합니다."""
        try:
            with open(STORES_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.stores_data, f, ensure_ascii=False, indent=2)
            logger.info(f"통합 판매점 정보 파일 저장 완료: {len(self.stores_data)}개 판매점")
            return True
        except Exception as e:
            logger.error(f"통합 판매점 정보 파일 저장 실패: {e}")
            return False
        
    def get_latest_draw_number(self):
        """최신 로또 회차 번호를 가져옵니다."""
        try:
            # 파라미터 없이 호출하면 최신 회차 정보 반환
            response = self.session.get(
                LOTTO_DRAW_URL,
                headers=self.headers
            )
            response.raise_for_status()
            
            data = response.json()
            if not data.get('data') or not data['data'].get('list'):
                logger.error("최신 회차 정보를 찾을 수 없습니다 (데이터 없음).")
                return None
            
            # 리스트의 첫 번째 항목(최신 회차) 사용
            latest_draw = data['data']['list'][0]
            latest_draw_no = int(latest_draw.get('ltEpsd', 0))
            
            logger.info(f"최신 회차: {latest_draw_no}")
            return latest_draw_no
            
        except Exception as e:
            logger.error(f"최신 회차 정보 가져오기 실패: {e}")
            return None

    def get_store_info(self, draw_no):
        """1등 판매점 정보를 가져옵니다 (API 사용)."""
        store_info = []
        
        try:
            # 1등 배출점 조회 (srchWnShpRnk=1) - User asked for all but typically we need rank 1 for "first_prize_store_info"
            # User provided example: https://dhlottery.co.kr/wnprchsplcsrch/selectLtWnShp.do?srchWnShpRnk=all&srchLtEpsd=1200
            # Let's use 'all' and filter, or just request 1. The code previously filtered for rank 1.
            params = {
                'srchWnShpRnk': 'all', # 전체 조회 후 필터링이 안전함
                'srchLtEpsd': draw_no
            }
            
            response = self.session.get(LOTTO_STORE_URL, params=params, headers=self.headers)
            response.raise_for_status()
            
            data = response.json()
            if not data.get('data') or not data['data'].get('list'):
                logger.info(f"회차 {draw_no}의 판매점 데이터가 없습니다.")
                return store_info
                
            stores_list = data['data']['list']
            
            for store in stores_list:
                # wnShpRnk: 등수 (1, 2)
                rank = store.get('wnShpRnk')
                if rank != 1:
                    continue
                    
                store_id = str(store.get('ltShpId'))
                store_name = store.get('shpNm')
                store_address = store.get('shpAddr')
                store_phone = store.get('shpTelno')
                
                # 복권 유형 확인
                lottery_types = []
                if store.get('l645LtNtslYn') == 'Y': lottery_types.append('lotto645')
                if store.get('pt720NtslYn') == 'Y': lottery_types.append('pension720')
                if store.get('st5LtNtslYn') == 'Y': lottery_types.append('speetto') # 스피또500
                if store.get('st10LtNtslYn') == 'Y': lottery_types.append('speetto1000')
                if store.get('st20LtNtslYn') == 'Y': lottery_types.append('speetto2000')
                
                # 중복 제거 (스피또)
                if 'speetto' in lottery_types or 'speetto1000' in lottery_types or 'speetto2000' in lottery_types:
                    lottery_types = [t for t in lottery_types if not t.startswith('speetto')]
                    lottery_types.append('speetto')
                
                # 좌표
                try:
                    lat = float(store.get('shpLat', 0))
                    lon = float(store.get('shpLot', 0))
                except (ValueError, TypeError):
                    lat, lon = 0.0, 0.0

                # 판매점 정보 저장 및 업데이트
                self.save_single_store_info(store_id, store_name, store_address, store_phone, lottery_types, lat, lon)
                
                store_info.append({
                    "store_id": store_id,
                    "type": store.get('atmtPsvYnTxt', '') # 자동/수동/반자동 등
                })
            
            logger.info(f"회차 {draw_no}의 1등 판매점 정보 {len(store_info)}개 추출 완료")
            
        except Exception as e:
            logger.error(f"1등 판매점 정보 추출 실패: {e}")
            
        return store_info
    
    def save_single_store_info(self, store_id, name, address, phone, lottery_types, lat, lon):
        """판매점 정보를 개별 파일 및 메모리에 저장합니다."""
        try:
            store_data = {
                "store_id": store_id,
                "name": name,
                "address": address,
                "phone": phone,
                "lottery_types": lottery_types,
                "latitude": lat,
                "longitude": lon,
                "updated_at": datetime.datetime.now().isoformat()
            }
            
            # 개별 파일로 저장
            store_file = STORES_DIR / f"{store_id}.json"
            
            # 기존 데이터가 있으면 유지할 필드가 있는지 확인 (현재는 덮어쓰기 위주)
            if os.path.exists(store_file):
                with open(store_file, 'r', encoding='utf-8') as f:
                    old_data = json.load(f)
                    # 필요한 경우 병합 로직 추가
                    store_data = {**old_data, **store_data}
            
            with open(store_file, 'w', encoding='utf-8') as f:
                json.dump(store_data, f, ensure_ascii=False, indent=2)
            
            # 통합 데이터 업데이트
            self.stores_data[store_id] = store_data
            
        except Exception as e:
            logger.error(f"판매점 정보 저장 실패: {store_id} - {e}")

    def format_date(self, ymd_str):
        """YYYYMMDD 문자열을 YYYY-MM-DD 형식으로 변환"""
        if not ymd_str or len(ymd_str) != 8:
            return ymd_str
        return f"{ymd_str[:4]}-{ymd_str[4:6]}-{ymd_str[6:]}"

    def crawl_draw(self, draw_no):
        """특정 회차의 로또 당첨 정보를 크롤링합니다 (API 사용)."""
        logger.info(f"회차 {draw_no} 크롤링 시작")
        
        try:
            params = {'srchLtEpsd': draw_no}
            response = self.session.get(LOTTO_DRAW_URL, params=params, headers=self.headers)
            response.raise_for_status()
            
            data = response.json()
            if not data.get('data') or not data['data'].get('list'):
                logger.error(f"회차 {draw_no}의 데이터를 찾을 수 없습니다.")
                return None
            
            draw_info = data['data']['list'][0]
            
            # 데이터 매핑
            draw_date = self.format_date(draw_info.get('ltRflYmd', ''))
            
            win_numbers = [
                int(draw_info.get('tm1WnNo', 0)),
                int(draw_info.get('tm2WnNo', 0)),
                int(draw_info.get('tm3WnNo', 0)),
                int(draw_info.get('tm4WnNo', 0)),
                int(draw_info.get('tm5WnNo', 0)),
                int(draw_info.get('tm6WnNo', 0))
            ]
            bonus_number = int(draw_info.get('bnsWnNo', 0))
            
            # 당첨금 정보 구성
            prize_info = []
            for rank in range(1, 6):
                prize_info.append({
                    'rank': f"{rank}등",
                    'total_prize': str(draw_info.get(f'rnk{rank}SumWnAmt', 0)), # 총 당첨금 (API 필드 확인 필요, rnkXsumWnAmt가 없어보이면 rnkXWnAmt * rnkXWnNope 사용?)
                                                                                # User provided: rnk1SumWnAmt exists.
                    'winner_count': str(draw_info.get(f'rnk{rank}WnNope', 0)),
                    'prize_per_winner': str(draw_info.get(f'rnk{rank}WnAmt', 0))
                })
            
            total_sales_amount = str(draw_info.get('wholEpsdSumNtslAmt', 0))
            
            # 1등 판매점 정보
            first_prize_store_info = self.get_store_info(draw_no)
            
            # 통합 판매점 정보 파일 저장
            self.save_stores_data()
            
            # 결과 데이터 구성
            result = {
                'draw_no': draw_no,
                'draw_date': draw_date,
                'numbers': win_numbers,
                'bonus_number': bonus_number,
                'prize_info': prize_info,
                'total_sales_amount': total_sales_amount,
                'first_prize_store_info': first_prize_store_info,
                'updated_at': datetime.datetime.now().isoformat()
            }
            
            logger.info(f"회차 {draw_no} 크롤링 완료: {win_numbers} + {bonus_number}")
            return result
            
        except Exception as e:
            logger.error(f"회차 {draw_no} 크롤링 실패: {e}")
            return None
    
    def save_draw_data(self, draw_data):
        """크롤링한 회차 데이터를 파일로 저장합니다."""
        if not draw_data:
            return False
            
        draw_no = draw_data['draw_no']
        file_path = DRAWS_DIR / f"lotto_{draw_no}.json"  # 회차별 데이터 디렉토리에 저장
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(draw_data, f, ensure_ascii=False, indent=2)
            logger.info(f"회차 {draw_no} 데이터 저장 완료: {file_path}")
            return True
        except Exception as e:
            logger.error(f"회차 {draw_no} 데이터 저장 실패: {e}")
            return False
    
    def update_index_file(self):
        """전체 회차 목록 인덱스 파일을 업데이트합니다."""
        index_path = DATA_DIR / "index.json"
        draws = []
        
        # 기존 인덱스 파일이 있으면 로드
        existing_draws = {}
        if os.path.exists(index_path):
            try:
                with open(index_path, 'r', encoding='utf-8') as f:
                    index_data = json.load(f)
                    # 기존 회차 정보를 딕셔너리로 변환 (draw_no를 키로 사용)
                    existing_draws = {draw['draw_no']: draw for draw in index_data.get('draws', [])}
            except Exception as e:
                logger.error(f"기존 인덱스 파일 로드 실패: {e}")
        
        # 모든 로또 데이터 파일 검색
        for file_path in DRAWS_DIR.glob("lotto_*.json"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    draw_no = data['draw_no']
                    
                    # 새로운 회차 정보
                    new_draw = {
                        'draw_no': draw_no,
                        'draw_date': data['draw_date'],
                        'file': f"draws/{file_path.name}"  # 상대 경로 포함
                    }
                    
                    # 기존 정보가 있으면 유지, 없으면 새로 추가
                    if draw_no in existing_draws:
                        draws.append(existing_draws[draw_no])
                    else:
                        draws.append(new_draw)
                        
            except Exception as e:
                logger.error(f"파일 읽기 실패: {file_path} - {e}")
        
        # 회차 번호(draw_no)를 기준으로 내림차순 정렬
        draws = sorted(draws, key=lambda x: x['draw_no'], reverse=True)
        
        # 인덱스 파일 저장
        try:
            index_data = {
                'draws': draws,
                'last_updated': datetime.datetime.now().isoformat()
            }
            
            with open(index_path, 'w', encoding='utf-8') as f:
                json.dump(index_data, f, ensure_ascii=False, indent=2)
            logger.info(f"인덱스 파일 업데이트 완료: {len(draws)}개 회차")
            return True
        except Exception as e:
            logger.error(f"인덱스 파일 업데이트 실패: {e}")
            return False
    
    def crawl_latest(self):
        """최신 회차 정보를 크롤링합니다."""
        latest_draw_no = self.get_latest_draw_number()
        if not latest_draw_no:
            return False
            
        draw_data = self.crawl_draw(latest_draw_no)
        if not draw_data:
            return False
            
        success = self.save_draw_data(draw_data)
        if success:
            self.update_index_file()
        return success
    
    def crawl_range(self, start_draw, end_draw):
        """지정된 범위의 회차 정보를 크롤링합니다."""
        success_count = 0
        
        for draw_no in range(start_draw, end_draw + 1):
            draw_data = self.crawl_draw(draw_no)
            if draw_data and self.save_draw_data(draw_data):
                success_count += 1
        
        if success_count > 0:
            self.update_index_file()
            
        logger.info(f"범위 크롤링 완료: {success_count}/{end_draw - start_draw + 1}개 성공")
        return success_count

def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='로또 당첨 정보 크롤러')
    parser.add_argument('--latest', action='store_true', help='최신 회차만 크롤링')
    parser.add_argument('--draw', type=int, help='특정 회차 크롤링')
    parser.add_argument('--range', type=str, help='회차 범위 크롤링 (시작-끝)')
    parser.add_argument('--all', action='store_true', help='모든 회차 크롤링 (1회부터 최신까지)')
    
    args = parser.parse_args()
    crawler = LottoCrawler()
    
    if args.latest:
        crawler.crawl_latest()
    elif args.draw:
        draw_data = crawler.crawl_draw(args.draw)
        if draw_data:
            crawler.save_draw_data(draw_data)
            crawler.update_index_file()
    elif args.range:
        try:
            start, end = map(int, args.range.split('-'))
            crawler.crawl_range(start, end)
        except ValueError:
            logger.error("범위 형식이 잘못되었습니다. 예: --range 1-10")
    elif args.all:
        latest = crawler.get_latest_draw_number()
        if latest:
            crawler.crawl_range(1, latest)
    else:
        # 기본값: 최신 회차 크롤링
        crawler.crawl_latest()

if __name__ == "__main__":
    main()
 