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
logger = logging.getLogger('pension_crawler')

# 상수 정의
BASE_URL = "https://dhlottery.co.kr"
PENSION_DRAW_URL = f"{BASE_URL}/gameResult.do?method=win720&Round="
PENSION_STORE_URL = f"{BASE_URL}/store.do?method=topStore&pageGubun=L720&drwNo="
DATA_DIR = Path("pension")
DRAWS_DIR = DATA_DIR / "draws"  # 회차별 데이터 디렉토리 추가
STORES_DIR = DATA_DIR / "stores"
STORES_FILE = DATA_DIR / "pension_stores.json"

class PensionCrawler:
    def __init__(self):
        """연금복권 크롤러 초기화"""
        self.session = requests.Session()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # 데이터 디렉토리 생성
        os.makedirs(DATA_DIR, exist_ok=True)
        os.makedirs(DRAWS_DIR, exist_ok=True)  # 회차별 데이터 디렉토리 생성
        os.makedirs(STORES_DIR, exist_ok=True)
    
    def get_latest_draw_number(self):
        """최신 연금복권 회차 번호를 가져옵니다."""
        try:
            response = self.session.get(f"{BASE_URL}/gameResult.do?method=win720", headers=self.headers)
            response.raise_for_status()
            
            # EUC-KR 인코딩 처리
            content = response.content.decode('euc-kr', errors='replace')
            soup = BeautifulSoup(content, 'lxml')
            
            # 회차 정보는 select 태그에서 첫 번째 option 값
            draw_select = soup.select_one('select#Round')
            if not draw_select:
                logger.error("최신 회차 정보를 찾을 수 없습니다.")
                return None
                
            # 첫 번째 option 값이 최신 회차
            latest_option = draw_select.select_one('option[selected]')
            if not latest_option:
                latest_option = draw_select.select_one('option')
                
            draw_no = int(latest_option.text.strip())
            logger.info(f"최신 회차: {draw_no}")
            return draw_no
            
        except Exception as e:
            logger.error(f"최신 회차 정보 가져오기 실패: {e}")
            return None
    
    def parse_draw_date(self, date_text):
        """회차 날짜 문자열을 파싱합니다."""
        # 예: "(2025년 03월 06일 추첨)" -> "2025-03-06"
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
            table = soup.select_one('table.tbl_data.tbl_data_col')
            if not table:
                logger.warning("당첨 정보 테이블을 찾을 수 없습니다.")
                return prize_info
                
            rows = table.select('tbody tr')
            for row in rows:
                cols = row.select('td')
                if len(cols) >= 2:  # 최소 2개 열이 있어야 함
                    rank = cols[0].text.strip()
                    # 마지막 열이 당첨자 수
                    winner_count = cols[-1].text.strip().replace(',', '')
                    
                    # 보너스 번호 처리
                    if rank == "보너스":
                        rank = "보너스"
                    
                    prize_info.append({
                        'rank': rank,
                        'winner_count': winner_count
                    })
                    
                    logger.info(f"당첨 정보 추출: {rank} - {winner_count}명")
            
            if not prize_info:
                logger.warning("추출된 당첨 정보가 없습니다.")
            else:
                logger.info(f"총 {len(prize_info)}개 등수의 당첨 정보 추출 완료")
                
        except Exception as e:
            logger.error(f"당첨 금액 정보 추출 실패: {e}")
            import traceback
            logger.error(traceback.format_exc())  # 상세 오류 스택 트레이스 출력
            
        return prize_info
    
    def get_store_info(self, draw_no):
        """1등, 2등, 보너스 판매점 정보를 가져옵니다."""
        first_prize_store_info = []
        second_prize_store_info = []
        bonus_prize_store_info = []
        
        try:
            url = f"{PENSION_STORE_URL}{draw_no}"
            response = self.session.get(url, headers=self.headers)
            response.raise_for_status()
            
            # EUC-KR 인코딩 처리
            content = response.content.decode('euc-kr', errors='replace')
            soup = BeautifulSoup(content, 'lxml')
            
            # 1등, 2등, 보너스 배출점 테이블 찾기
            store_tables = soup.select('.group_content table.tbl_data.tbl_data_col')
            
            # 1등 배출점
            if len(store_tables) >= 1:
                rows = store_tables[0].select('tbody tr')
                for row in rows:
                    cols = row.select('td')
                    if len(cols) >= 3:
                        store_name = cols[1].text.strip()
                        store_address = cols[2].text.strip()
                        first_prize_store_info.append({
                            "name": store_name,
                            "address": store_address
                        })
            
            # 2등 배출점
            if len(store_tables) >= 2:
                rows = store_tables[1].select('tbody tr')
                for row in rows:
                    cols = row.select('td')
                    if len(cols) >= 3:
                        store_name = cols[1].text.strip()
                        store_address = cols[2].text.strip()
                        second_prize_store_info.append({
                            "name": store_name,
                            "address": store_address
                        })
            
            # 보너스 배출점
            if len(store_tables) >= 3:
                rows = store_tables[2].select('tbody tr')
                for row in rows:
                    cols = row.select('td')
                    if len(cols) >= 3:
                        store_name = cols[1].text.strip()
                        store_address = cols[2].text.strip()
                        bonus_prize_store_info.append({
                            "name": store_name,
                            "address": store_address
                        })
            
            logger.info(f"회차 {draw_no}의 판매점 정보 추출 완료: 1등 {len(first_prize_store_info)}개, 2등 {len(second_prize_store_info)}개, 보너스 {len(bonus_prize_store_info)}개")
            
            # 판매점 정보를 파일로 저장
            store_data = {
                "first_prize_store_info": first_prize_store_info,
                "second_prize_store_info": second_prize_store_info,
                "bonus_prize_store_info": bonus_prize_store_info
            }
            
            store_file = STORES_DIR / f"stores_{draw_no}.json"
            with open(store_file, 'w', encoding='utf-8') as f:
                json.dump(store_data, f, ensure_ascii=False, indent=2)
            logger.info(f"회차 {draw_no}의 판매점 정보 저장 완료")
            
        except Exception as e:
            logger.error(f"판매점 정보 추출 실패: {e}")
            
        return {
            "first_prize_store_info": first_prize_store_info,
            "second_prize_store_info": second_prize_store_info,
            "bonus_prize_store_info": bonus_prize_store_info
        }
    
    def crawl_draw(self, draw_no):
        """특정 회차의 연금복권 당첨 정보를 크롤링합니다."""
        logger.info(f"회차 {draw_no} 크롤링 시작")
        
        try:
            url = f"{PENSION_DRAW_URL}{draw_no}"
            response = self.session.get(url, headers=self.headers)
            response.raise_for_status()
            
            # EUC-KR 인코딩 처리
            content = response.content.decode('euc-kr', errors='replace')
            soup = BeautifulSoup(content, 'lxml')
            
            # 회차 정보 및 날짜
            draw_date_elem = soup.select_one('p.desc')
            if not draw_date_elem:
                logger.error(f"회차 {draw_no}의 날짜 정보를 찾을 수 없습니다.")
                return None
                
            draw_date = self.parse_draw_date(draw_date_elem.text)
            
            # 1등 당첨번호 (조 + 6자리 번호)
            win_numbers = []
            group_elem = soup.select_one('.win720_num .group span.num')
            group = group_elem.text.strip() if group_elem else ""
            
            number_elems = soup.select('.win720_num span.num.large')
            if len(number_elems) < 6:
                logger.error(f"회차 {draw_no}의 당첨 번호를 찾을 수 없습니다.")
                return None
            
            # 앞의 1개는 조, 나머지 6개는 당첨 번호
            for elem in number_elems[1:7]:
                win_numbers.append(elem.text.strip())
            
            # 보너스 번호 (조 + 6자리 번호)
            bonus_group_elem = soup.select('.win720_num')[1].select_one('.group.bonus span.num')
            bonus_group = bonus_group_elem.text.strip() if bonus_group_elem else ""
            
            bonus_numbers = []
            bonus_number_elems = soup.select('.win720_num')[1].select('span.num.large')
            for elem in bonus_number_elems:
                bonus_numbers.append(elem.text.strip())
            
            # 당첨 금액 정보
            prize_info = self.get_prize_info(soup)
            
            # 결과 데이터 구성
            result = {
                'draw_no': draw_no,
                'draw_date': draw_date,
                'group': group,
                'numbers': win_numbers,
                'bonus_group': bonus_group,
                'bonus_numbers': bonus_numbers,
                'prize_info': prize_info,
                'updated_at': datetime.datetime.now().isoformat()
            }
            
            logger.info(f"회차 {draw_no} 크롤링 완료: {group}조 {'-'.join(win_numbers)}")
            return result
            
        except Exception as e:
            logger.error(f"회차 {draw_no} 크롤링 실패: {e}")
            return None
    
    def save_draw_data(self, draw_data):
        """크롤링한 회차 데이터를 파일로 저장합니다."""
        if not draw_data:
            return False
            
        draw_no = draw_data['draw_no']
        file_path = DRAWS_DIR / f"pension_{draw_no}.json"
        
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
        
        # 모든 연금복권 데이터 파일 검색
        for file_path in sorted(DRAWS_DIR.glob("pension_*.json"), reverse=True):
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
            
            # 판매점 정보 크롤링
            self.get_store_info(latest_draw_no)
            
        return success
    
    def crawl_range(self, start_draw, end_draw):
        """지정된 범위의 회차 정보를 크롤링합니다."""
        success_count = 0
        
        for draw_no in range(start_draw, end_draw + 1):
            draw_data = self.crawl_draw(draw_no)
            if draw_data and self.save_draw_data(draw_data):
                success_count += 1
                
                # 판매점 정보 크롤링
                self.get_store_info(draw_no)
        
        if success_count > 0:
            self.update_index_file()
            
        logger.info(f"범위 크롤링 완료: {success_count}/{end_draw - start_draw + 1}개 성공")
        return success_count

def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='연금복권 당첨 정보 크롤러')
    parser.add_argument('--latest', action='store_true', help='최신 회차만 크롤링')
    parser.add_argument('--draw', type=int, help='특정 회차 크롤링')
    parser.add_argument('--range', type=str, help='회차 범위 크롤링 (시작-끝)')
    parser.add_argument('--all', action='store_true', help='모든 회차 크롤링 (1회부터 최신까지)')
    
    args = parser.parse_args()
    crawler = PensionCrawler()
    
    if args.latest:
        crawler.crawl_latest()
    elif args.draw:
        draw_data = crawler.crawl_draw(args.draw)
        if draw_data:
            crawler.save_draw_data(draw_data)
            crawler.update_index_file()
            crawler.get_store_info(args.draw)
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