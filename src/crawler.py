#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import requests
from bs4 import BeautifulSoup
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
LOTTO_DRAW_URL = f"{BASE_URL}/gameResult.do?method=byWin&drwNo="
LOTTO_STORE_URL = f"{BASE_URL}/store.do?method=topStore&pageGubun=L645&drwNo="
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
            response = self.session.get(f"{BASE_URL}/gameResult.do?method=byWin", headers=self.headers)
            response.raise_for_status()
            
            # EUC-KR 인코딩 처리
            content = response.content.decode('euc-kr', errors='replace')
            soup = BeautifulSoup(content, 'lxml')
            
            # 회차 정보는 페이지 상단의 제목에 있음
            draw_text = soup.select_one('h4')
            
            if not draw_text:
                logger.error("최신 회차 정보를 찾을 수 없습니다.")
                return None
                
            # 회차 번호 추출 (예: "1161회 당첨결과" -> 1161)
            draw_no = int(re.search(r'\d+', draw_text.text).group())
            logger.info(f"최신 회차: {draw_no}")
            return draw_no
            
        except Exception as e:
            logger.error(f"최신 회차 정보 가져오기 실패: {e}")
            return None
    
    def parse_draw_date(self, date_text):
        """회차 날짜 문자열을 파싱합니다."""
        # 예: "(2025년 03월 01일 추첨)" -> "2025-03-01"
        match = re.search(r'(\d{4})년\s(\d{2})월\s(\d{2})일', date_text)
        if match:
            year = match.group(1)
            month = match.group(2)
            day = match.group(3)
            return f"{year}-{month}-{day}"
        return date_text.strip()
    
    def get_prize_info(self, soup):
        """당첨 금액 정보를 가져옵니다."""
        prize_info = []
        
        try:
            # 당첨 정보 테이블에서 데이터 추출
            table = soup.select_one('table.tbl_data')
            if not table:
                return prize_info
                
            rows = table.select('tbody tr')
            for row in rows:
                cols = row.select('td')
                if len(cols) >= 5:  # 최소 5개 열이 있어야 함
                    rank = cols[0].text.strip()
                    total_prize = cols[1].text.strip()
                    winner_count = cols[2].text.strip()
                    prize_per_winner = cols[3].text.strip()
                    
                    prize_info.append({
                        'rank': rank,
                        'total_prize': total_prize,
                        'winner_count': winner_count,
                        'prize_per_winner': prize_per_winner
                    })
            
        except Exception as e:
            logger.error(f"당첨 금액 정보 추출 실패: {e}")
            
        return prize_info
    
    def get_total_sales_amount(self, soup):
        """총판매금액 정보를 가져옵니다."""
        try:
            # 총판매금액 정보 추출
            sales_amount_elem = soup.select_one('.list_text_common li strong')
            if sales_amount_elem:
                return sales_amount_elem.text.strip()
            
            # 다른 형태로 시도
            sales_info = soup.select('.list_text_common li')
            for info in sales_info:
                text = info.text.strip()
                if '총판매금액' in text:
                    # 정규식으로 금액 추출
                    match = re.search(r'([0-9,]+원)', text)
                    if match:
                        return match.group(1)
        except Exception as e:
            logger.error(f"총판매금액 정보 추출 실패: {e}")
        
        return None
    
    def extract_store_id(self, onclick):
        """판매점 ID를 추출합니다."""
        try:
            match = re.search(r"'([^']*)'", onclick)
            if match:
                return match.group(1)
        except Exception as e:
            logger.error(f"판매점 ID 추출 실패: {e}")
        
        return None
    
    def get_store_info(self, draw_no):
        """1등 판매점 정보를 가져옵니다."""
        store_info = []
        
        try:
            url = f"{LOTTO_STORE_URL}{draw_no}"
            response = self.session.get(url, headers=self.headers)
            response.raise_for_status()
            
            # EUC-KR 인코딩 처리
            content = response.content.decode('euc-kr', errors='replace')
            soup = BeautifulSoup(content, 'lxml')
            
            # 1등 배출점 테이블 찾기
            store_table = soup.select('.tbl_data.tbl_data_col')
            if not store_table or len(store_table) == 0:
                logger.error(f"회차 {draw_no}의 1등 판매점 테이블을 찾을 수 없습니다.")
                return store_info
            
            # 첫 번째 테이블의 행 추출
            rows = store_table[0].select('tbody tr')
            
            for row in rows:
                cols = row.select('td')
                if len(cols) >= 5:  # 번호, 상호명, 구분, 소재지, 위치보기
                    # 지도보기 링크에서 판매점 ID 추출
                    map_link = cols[4].select_one('a.btn_search[onclick*="showMapPage"]')
                    if map_link:
                        onclick = map_link.get('onclick', '')
                        store_id = self.extract_store_id(onclick)
                        if store_id:
                            store_name = cols[1].text.strip()
                            store_type = cols[2].text.strip()
                            store_address = cols[3].text.strip()
                            
                            # 판매점 정보 저장
                            self.save_store_info(store_id, store_name, store_address, store_type)
                            
                            # store_id와 type 정보를 함께 저장
                            store_info.append({
                                "store_id": store_id,
                                "type": store_type
                            })
            
            logger.info(f"회차 {draw_no}의 1등 판매점 정보 {len(store_info)}개 추출 완료")
            
        except Exception as e:
            logger.error(f"1등 판매점 정보 추출 실패: {e}")
            
        return store_info
    
    def save_store_info(self, store_id, name, address, store_type):
        """판매점 정보를 저장합니다."""
        try:
            # 개별 파일로 저장
            store_file = STORES_DIR / f"{store_id}.json"
            
            store_data = {
                "store_id": store_id,
                "name": name,
                "address": address
                # type 정보 제거
            }
            
            # 이미 존재하는 파일이 아닐 경우에만 저장
            if not os.path.exists(store_file):
                with open(store_file, 'w', encoding='utf-8') as f:
                    json.dump(store_data, f, ensure_ascii=False, indent=2)
                logger.info(f"판매점 정보 저장 완료: {store_id}")
            
            # 통합 파일에 추가
            self.stores_data[store_id] = store_data
            
        except Exception as e:
            logger.error(f"판매점 정보 저장 실패: {store_id} - {e}")
    
    def crawl_draw(self, draw_no):
        """특정 회차의 로또 당첨 정보를 크롤링합니다."""
        logger.info(f"회차 {draw_no} 크롤링 시작")
        
        try:
            url = f"{LOTTO_DRAW_URL}{draw_no}"
            response = self.session.get(url, headers=self.headers)
            response.raise_for_status()
            
            # EUC-KR 인코딩 처리
            content = response.content.decode('euc-kr', errors='replace')
            soup = BeautifulSoup(content, 'lxml')
            
            # 회차 정보 및 날짜
            draw_date_elem = soup.select_one('p:contains("추첨")')
            if not draw_date_elem:
                logger.error(f"회차 {draw_no}의 날짜 정보를 찾을 수 없습니다.")
                return None
                
            draw_date = self.parse_draw_date(draw_date_elem.text)
            
            # 당첨 번호 (ball_645 클래스를 가진 span 요소)
            win_numbers = []
            ball_elements = soup.select('.ball_645.lrg')
            
            if not ball_elements or len(ball_elements) < 7:
                logger.error(f"회차 {draw_no}의 당첨 번호를 찾을 수 없습니다.")
                return None
            
            # 앞의 6개는 당첨 번호, 마지막 1개는 보너스 번호
            for i, elem in enumerate(ball_elements[:6]):
                win_numbers.append(int(elem.text.strip()))
                
            bonus_number = int(ball_elements[6].text.strip())
            
            # 당첨 금액 정보
            prize_info = self.get_prize_info(soup)
            
            # 총판매금액 정보
            total_sales_amount = self.get_total_sales_amount(soup)
            
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
        
        # 모든 로또 데이터 파일 검색
        for file_path in DRAWS_DIR.glob("lotto_*.json"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    draws.append({
                        'draw_no': data['draw_no'],
                        'draw_date': data['draw_date'],
                        'file': f"draws/{file_path.name}"  # 상대 경로 포함
                    })
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