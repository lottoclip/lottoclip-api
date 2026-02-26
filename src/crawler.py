#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import csv
import requests
import datetime
import re
import logging
from pathlib import Path
from itertools import combinations
import time
import math

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

def parse_address_parts(address: str) -> tuple[str, str]:
    """주소 문자열에서 시도(province)와 시군구(city)를 추출합니다.
    
    주소 형식: "서울 강서구  까치산로 177 1층 101호"
    → province: "서울", city: "강서구"
    
    두 번째 토큰이 없으면 빈 문자열을 반환합니다.
    """
    # 연속된 공백 제거 후 분리
    tokens = address.strip().split() if address else []
    province = tokens[0] if len(tokens) >= 1 else ""
    city = tokens[1] if len(tokens) >= 2 else ""
    return province, city


class LottoCrawler:
    def __init__(self):
        """로또 크롤러 초기화"""
        self.session = requests.Session()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36'
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
            
            # 판매점 인덱스 파일 업데이트
            self.update_store_index_file()
            
            return True
        except Exception as e:
            logger.error(f"통합 판매점 정보 파일 저장 실패: {e}")
            return False

    def update_store_index_file(self):
        """판매점 목록 인덱스 파일을 업데이트합니다 (lotto/stores/index.json + index.csv).
        
        - index.json: 기존 필드 + province(시도), city(시군구) 추가
        - index.csv : 동일 데이터를 CSV 형식으로 함께 저장
        """
        try:
            index_path = STORES_DIR / "index.json"
            csv_path = STORES_DIR / "index.csv"
            stores_list = []

            for store_id, data in self.stores_data.items():
                address = data.get("address", "") or ""
                # 주소에서 시도(province)와 시군구(city) 추출
                province, city = parse_address_parts(address)

                stores_list.append({
                    "id": store_id,
                    "name": data.get("name"),
                    "province": province,
                    "city": city,
                    "address": address,
                    "types": data.get("lottery_types", []),
                    "1st": data.get("first_prize_count", 0),
                    "2nd": data.get("second_prize_count", 0)
                })

            # ── JSON 저장 ─────────────────────────────────────────────────
            with open(index_path, 'w', encoding='utf-8') as f:
                json.dump(stores_list, f, ensure_ascii=False)  # Compact format for index

            # ── CSV 저장 ──────────────────────────────────────────────────
            CSV_FIELDS = ["id", "name", "province", "city", "address", "types", "1st", "2nd"]
            with open(csv_path, 'w', encoding='utf-8-sig', newline='') as f:
                # utf-8-sig: BOM 포함 → 엑셀 등에서 한글 깨짐 없이 열 수 있음
                writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
                writer.writeheader()
                for store in stores_list:
                    row = {**store}
                    # types 리스트를 파이프(|) 구분 문자열로 변환 ("lotto645|pension720")
                    row["types"] = "|".join(store.get("types", []))
                    writer.writerow(row)

            logger.info(
                f"판매점 인덱스 파일 업데이트 완료: {len(stores_list)}개 "
                f"(index.json + index.csv)"
            )

        except Exception as e:
            logger.error(f"판매점 인덱스 파일 업데이트 실패: {e}")

        
    def _fetch_with_retry(self, url, params=None, max_retries=3):
        """재시도 로직이 포함된 GET 요청"""
        for attempt in range(max_retries):
            try:
                response = self.session.get(url, params=params, headers=self.headers, timeout=10)
                response.raise_for_status()
                return response
            except requests.exceptions.RequestException as e:
                if attempt == max_retries - 1:
                    logger.error(f"요청 실패 (최대 재시도 초과): {e}")
                    raise
                
                logger.warning(f"요청 실패, 5초 후 재시도 ({attempt + 1}/{max_retries}): {e}")
                time.sleep(5)
                
    def get_latest_draw_number(self):
        """최신 로또 회차 번호를 가져옵니다."""
        try:
            # 파라미터 없이 호출하면 최신 회차 정보 반환
            response = self._fetch_with_retry(LOTTO_DRAW_URL)
            
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
            
            response = self._fetch_with_retry(LOTTO_STORE_URL, params=params)
            
            data = response.json()
            if not data.get('data') or not data['data'].get('list'):
                logger.info(f"회차 {draw_no}의 판매점 데이터가 없습니다.")
                return store_info
                
            stores_list = data['data']['list']
            logger.info(f"API에서 수신된 전체 판매점 수: {len(stores_list)}")
            
            for store in stores_list:
                # wnShpRnk: 등수 (1, 2)
                rank = store.get('wnShpRnk')
                
                # 타입 변환을 통한 안전한 비교
                # 1등과 2등 모두 수집하지만, 함수 반환값(draw info)에는 1등만 포함
                if str(rank) != '1' and str(rank) != '2':
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

                # 판매점 정보 저장 및 업데이트 (회차 및 등수 정보 포함)
                self.save_single_store_info(store_id, store_name, store_address, store_phone, lottery_types, lat, lon, draw_no=draw_no, rank=rank)
                
                # 1등인 경우에만 반환 리스트에 추가
                if str(rank) == '1':
                    store_info.append({
                        "store_id": store_id,
                        "type": store.get('atmtPsvYnTxt', '') # 자동/수동/반자동 등
                    })
            
            logger.info(f"회차 {draw_no}의 판매점 정보 처리 완료 (1등: {len(store_info)}개)")
            
        except Exception as e:
            logger.error(f"판매점 정보 추출 실패: {e}")
            
        return store_info
    
    def save_single_store_info(self, store_id, name, address, phone, lottery_types, lat, lon, draw_no=None, rank=None):
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
            
            # 기존 데이터가 있으면 유지할 필드가 있는지 확인
            if os.path.exists(store_file):
                with open(store_file, 'r', encoding='utf-8') as f:
                    old_data = json.load(f)
                    # 기존 데이터 병합 (history 필드 등 보존)
                    store_data = {**old_data, **store_data}
            
            # 당첨 이력 업데이트
            if draw_no and rank:
                # 초기화
                if 'first_prize_draws' not in store_data: store_data['first_prize_draws'] = []
                if 'second_prize_draws' not in store_data: store_data['second_prize_draws'] = []
                
                rank_str = str(rank)
                draw_val = int(draw_no)
                
                if rank_str == '1':
                    if draw_val not in store_data['first_prize_draws']:
                        store_data['first_prize_draws'].append(draw_val)
                        # 회차 내림차순 정렬
                        store_data['first_prize_draws'].sort(reverse=True)
                elif rank_str == '2':
                    if draw_val not in store_data['second_prize_draws']:
                        store_data['second_prize_draws'].append(draw_val)
                        # 회차 내림차순 정렬
                        store_data['second_prize_draws'].sort(reverse=True)
                
                # 카운트 업데이트
                store_data['first_prize_count'] = len(store_data['first_prize_draws'])
                store_data['second_prize_count'] = len(store_data['second_prize_draws'])
            
            with open(store_file, 'w', encoding='utf-8') as f:
                json.dump(store_data, f, ensure_ascii=False, indent=2)
            
            # 통합 데이터 업데이트
            self.stores_data[store_id] = store_data
            
        except Exception as e:
            logger.error(f"판매점 정보 저장 실패: {store_id} - {e} (Draw: {draw_no}, Rank: {rank})")

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
            response = self._fetch_with_retry(LOTTO_DRAW_URL, params=params)
            
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

            # 통계 분석 데이터 생성
            analysis_stats = self.get_analysis_stats(win_numbers, first_prize_store_info, prize_info, total_sales_amount)
            
            # 결과 데이터 구성
            result = {
                'draw_no': draw_no,
                'draw_date': draw_date,
                'numbers': win_numbers,
                'bonus_number': bonus_number,
                'prize_info': prize_info,
                'total_sales_amount': total_sales_amount,
                'first_prize_store_info': first_prize_store_info,
                'analysis_stats': analysis_stats,
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
                    if 'numbers' in data:
                        new_draw['numbers'] = data['numbers']
                    if 'bonus_number' in data:
                        new_draw['bonus_number'] = data['bonus_number']
                    
                    # 기존 정보가 있으면 기존 것에 데이터를 병합하여 유지, 없으면 새로 추가
                    if draw_no in existing_draws:
                        existing_draw = existing_draws[draw_no]
                        if 'numbers' in new_draw and 'numbers' not in existing_draw:
                            existing_draw['numbers'] = new_draw['numbers']
                        if 'bonus_number' in new_draw and 'bonus_number' not in existing_draw:
                            existing_draw['bonus_number'] = new_draw['bonus_number']
                        draws.append(existing_draw)
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
            
            # 과도한 요청 방지를 위한 대기 (2초)
            time.sleep(2)
        
        if success_count > 0:
            self.update_index_file()
            
        logger.info(f"범위 크롤링 완료: {success_count}/{end_draw - start_draw + 1}개 성공")
        return success_count
    
    def get_analysis_stats(self, numbers, store_info, prize_info, total_sales):
        """회차별 상세 통계 정보를 계산합니다."""
        
        # 1. 번호 속성 분석
        number_properties = self._analyze_number_properties(numbers)
        
        # 2. 구간 및 연번 분석
        range_and_sequence = self._analyze_range_and_sequence(numbers)
        
        # 3. 끝수 분석
        last_digit_stats = self._analyze_last_digits(numbers)
        
        # 4. 당첨 및 구매 성향
        winner_insight = self._analyze_winner_insight(store_info, prize_info, total_sales)
        
        return {
            "number_properties": number_properties,
            "range_and_sequence": range_and_sequence,
            "last_digit_stats": last_digit_stats,
            "winner_insight": winner_insight
        }

    def _analyze_number_properties(self, numbers):
        """번호 속성 분석: 총합, 홀짝, 고저, AC값, 소수"""
        # 총합
        sum_total = sum(numbers)
        
        # 홀짝 패턴
        odd_count = sum(1 for n in numbers if n % 2 != 0)
        even_count = 6 - odd_count
        odd_even_pattern = f"{odd_count}:{even_count}"
        
        # 고저 패턴 (저: 1~22, 고: 23~45)
        low_count = sum(1 for n in numbers if 1 <= n <= 22)
        high_count = 6 - low_count
        high_low_pattern = f"{low_count}:{high_count}"
        
        # AC 값
        # 1단계: 가능한 모든 두 수의 차이(절댓값) 구하기
        diffs = set()
        for a, b in combinations(numbers, 2):
            diffs.add(abs(a - b))
        # 2단계: 고유한 차이값 개수 - (6 - 1)
        ac_value = len(diffs) - (6 - 1)
        
        # 소수 개수
        primes = {2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43}
        prime_count = sum(1 for n in numbers if n in primes)
        
        return {
            "sum_total": sum_total,
            "odd_even_pattern": odd_even_pattern,
            "high_low_pattern": high_low_pattern,
            "ac_value": ac_value,
            "prime_count": prime_count
        }

    def _analyze_range_and_sequence(self, numbers):
        """구간 및 연번 분석"""
        # 번대별 개수
        section_counts = {
            "unit": 0,    # 1~10
            "ten": 0,     # 11~20
            "twenty": 0,  # 21~30
            "thirty": 0,  # 31~40
            "forty": 0    # 41~45
        }
        
        for n in numbers:
            if 1 <= n <= 10: section_counts["unit"] += 1
            elif 11 <= n <= 20: section_counts["ten"] += 1
            elif 21 <= n <= 30: section_counts["twenty"] += 1
            elif 31 <= n <= 40: section_counts["thirty"] += 1
            elif 41 <= n <= 45: section_counts["forty"] += 1
            
        # 멸 구간 (개수가 0인 구간)
        missing_sections = []
        section_map = {
            "unit": "단번대", "ten": "10번대", "twenty": "20번대", 
            "thirty": "30번대", "forty": "40번대"
        }
        # JSON 키 이름으로 저장하는 것이 데이터 활용에 더 좋음 (예: ["unit", "thirty"]) 
        # 하지만 요청 예시는 ["10번대"] 형태이므로 기획 의도에 맞게 값 변환하거나 키를 반환.
        # 예시: ["30"] 으로 됨. User requested: ["30번대"] in description but ["30"] in json example.
        # Let's stick to the JSON example: ["30"] meaning the 30s section.
        # Actually user example: "missing_sections": ["30"]. Let's use simple identifiers.
        
        if section_counts["unit"] == 0: missing_sections.append("1") # 1~10
        if section_counts["ten"] == 0: missing_sections.append("10")
        if section_counts["twenty"] == 0: missing_sections.append("20")
        if section_counts["thirty"] == 0: missing_sections.append("30")
        if section_counts["forty"] == 0: missing_sections.append("40")

        # 연번 쌍 개수
        sorted_nums = sorted(numbers)
        consecutive_sets = 0
        for i in range(len(sorted_nums) - 1):
            if sorted_nums[i+1] - sorted_nums[i] == 1:
                consecutive_sets += 1
                
        return {
            "section_counts": section_counts,
            "consecutive_sets": consecutive_sets,
            "missing_sections": missing_sections
        }

    def _analyze_last_digits(self, numbers):
        """끝수 분석"""
        last_digits = [n % 10 for n in numbers]
        
        # 끝수 합
        last_digit_sum = sum(last_digits)
        
        # 동형 끝수 (빈도수가 2 이상인 숫자들)
        counts = {}
        for d in last_digits:
            counts[d] = counts.get(d, 0) + 1
            
        duplicate_last_digits = [k for k, v in counts.items() if v >= 2]
        duplicate_last_digits.sort()
        
        return {
            "last_digit_sum": last_digit_sum,
            "duplicate_last_digits": duplicate_last_digits
        }

    def _analyze_winner_insight(self, store_info, prize_info, total_sales):
        """당첨 및 구매 성향 분석"""
        # 총 판매액 대비 당첨금 지급률
        total_payout_rate = 0.0
        try:
            sales = int(total_sales)
            if sales > 0:
                # 총 당첨금 합계 (1~5등)
                total_prize_sum = 0
                for rank_info in prize_info:
                    # 'total_prize' 필드가 있으면 사용, 없으면 winner_count * prize_per_winner 계산
                    if 'total_prize' in rank_info:
                        total_prize_sum += int(rank_info['total_prize'])
                    else:
                        cnt = int(rank_info.get('winner_count', 0))
                        amt = int(rank_info.get('prize_per_winner', 0))
                        total_prize_sum += cnt * amt
                
                total_payout_rate = round((total_prize_sum / sales) * 100, 2)
        except (ValueError, TypeError):
            pass

        # 1등 구매 방식 비율
        winner_method_rate = {
            "auto": 0.0,
            "manual": 0.0,
            "semi": 0.0
        }
        
        total_winners = len(store_info)
        if total_winners > 0:
            auto_count = sum(1 for s in store_info if '자동' in s.get('type', ''))
            # '반자동'은 '자동'에 포함되지 않게 주의 (보통 type이 '자동', '수동', '반자동'으로 옴)
            # 정확한 매칭 필요
            auto_count = sum(1 for s in store_info if s.get('type') == '자동')
            semi_count = sum(1 for s in store_info if s.get('type') == '반자동')
            manual_count = sum(1 for s in store_info if s.get('type') == '수동')
            
            # 비율 계산
            winner_method_rate["auto"] = round((auto_count / total_winners) * 100, 1)
            winner_method_rate["manual"] = round((manual_count / total_winners) * 100, 1)
            winner_method_rate["semi"] = round((semi_count / total_winners) * 100, 1)

        # 1등 실수령 예상액 계산
        tax_adjusted_prize = 0
        try:
            # 1등 당첨금 (1인당)
            first_prize_amt = 0
            for p in prize_info:
                if '1등' in p.get('rank', ''):
                    first_prize_amt = int(p.get('prize_per_winner', 0))
                    break
            
            if first_prize_amt > 0:
                cost_of_ticket = 1000 # 로또 1게임 구입 비용
                
                # 과세 대상 금액 계산 (당첨금 - 구입비용)
                taxable_amt = first_prize_amt - cost_of_ticket
                
                tax = 0
                if taxable_amt <= 300000000:
                    # 3억 이하: 22%
                    tax = taxable_amt * 0.22
                else:
                    # 3억 초과분만 33% 적용 (3억까지는 22%)
                    tax = (300000000 * 0.22) + ((taxable_amt - 300000000) * 0.33)
                
                # 원단위 절사 (보통 세금 계산 시 원단위는 버림 처리합니다)
                tax = math.floor(tax / 10) * 10
                
                tax_adjusted_prize = int(first_prize_amt - tax)
                
        except (ValueError, TypeError):
            pass

        return {
            "total_payout_rate": total_payout_rate,
            "winner_method_rate": winner_method_rate,
            "tax_adjusted_prize": tax_adjusted_prize
        }

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
 