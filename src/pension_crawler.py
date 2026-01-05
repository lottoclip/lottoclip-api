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
logger = logging.getLogger('pension_crawler')

# 상수 정의
BASE_URL = "https://dhlottery.co.kr"
PENSION_DRAW_URL = f"{BASE_URL}/pt720/selectPt720Intro.do" # 최신 회차 및 당첨번호 (pstEpsd 리스트)
PENSION_STORE_URL = f"{BASE_URL}/wnprchsplcsrch/selectPtWnShp.do"
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
            # Intro API 호출
            response = self.session.get(PENSION_DRAW_URL, headers=self.headers)
            response.raise_for_status()
            
            data = response.json()
            if not data.get('data') or not data['data'].get('pstEpsd'):
                logger.error("최신 회차 정보를 찾을 수 없습니다.")
                return None
                
            # pstEpsd 리스트의 첫 번째 항목의 psltEpsd가 최신 회차 (혹은 thsEpsd는 다음 회차일 수 있음 - pstEpsd가 Past Episode?)
            # User provided JSON: "pstEpsd": [ { "psltEpsd": 296, ... } ]
            # And "thsEpsd": { "ltEpsd": 297 ... } -> This is This episode (Next draw)
            # So pstEpsd[0] is likely the latest RESULT.
            
            latest_draw_info = data['data']['pstEpsd'][0]
            draw_no = int(latest_draw_info.get('psltEpsd', 0))
            
            logger.info(f"최신 회차: {draw_no}")
            return draw_no
            
        except Exception as e:
            logger.error(f"최신 회차 정보 가져오기 실패: {e}")
            return None
    
    def format_date(self, ymd_str):
        """YYYY.MM.DD 문자열을 YYYY-MM-DD 형식으로 변환"""
        # API returns "2026.01.01"
        return ymd_str.replace('.', '-')

    def get_store_info(self, draw_no):
        """1등, 2등, 보너스 판매점 정보를 가져옵니다 (API 사용)."""
        first_prize_store_info = []
        second_prize_store_info = []
        bonus_prize_store_info = []
        
        try:
            params = {
                'srchWnShpRnk': 'all',
                'srchLtEpsd': draw_no
            }
            
            response = self.session.get(PENSION_STORE_URL, params=params, headers=self.headers)
            response.raise_for_status()
            
            data = response.json()
            if not data.get('data') or not data['data'].get('list'):
                logger.info(f"회차 {draw_no}의 판매점 정보가 없습니다.")
                # 빈 리스트 반환 (기존 로직 유지)
            else:
                stores_list = data['data']['list']
                
                for store in stores_list:
                    rank_val = str(store.get('wnShpRnk', ''))
                    
                    store_info = {
                        "name": store.get('shpNm', ''),
                        "address": store.get('shpAddr', ''),
                        "store_id": str(store.get('ltShpId', '')), # ID 추가
                        "type": store.get('atmtPsvYnTxt', '') # 자동/수동 정보가 있다면
                    }
                    
                    if rank_val == "1":
                        first_prize_store_info.append(store_info)
                    elif rank_val == "2":
                        second_prize_store_info.append(store_info)
                    elif rank_val == "21": # 보너스로 추정
                        bonus_prize_store_info.append(store_info)
            
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
            # Intro API 사용 (최신 회차 정보만 제공될 가능성이 높음)
            # 과거 회차를 위해 param을 던져볼 수 있지만, 일단 없으면 최신만 될 수 있음.
            # 하지만 Lotto API처럼 연금복권도 selectPt720Intro.do가 params를 받을 수도 있고, 
            # 혹은 selectPstPt720WnInfo.do (통계)를 써야할 수도 있는데 통계 API엔 번호가 없음.
            # 여기서는 Intro API를 사용하여 '최신' 혹은 파라미터가 동작한다고 가정/시도.
            # User provided a URL with NO params returning list of past episodes in `pstEpsd`. 
            # So parsing `pstEpsd` list might find the specific draw_no if it's recent. 
            
            # API 호출
            response = self.session.get(PENSION_DRAW_URL, headers=self.headers)
            response.raise_for_status()
            
            data = response.json()
            if not data.get('data') or not data['data'].get('pstEpsd'):
                logger.error(f"회차 {draw_no}의 데이터를 찾을 수 없습니다 (API 응답 없음).")
                return None
            
            pst_epsd_list = data['data']['pstEpsd']
            
            # 해당 회차 데이터 찾기
            target_draw_items = [item for item in pst_epsd_list if int(item.get('psltEpsd', 0)) == draw_no]
            
            if not target_draw_items:
                logger.warning(f"API 응답에서 회차 {draw_no} 정보를 찾을 수 없습니다. (최신 회차 리스트에 없을 수 있음)")
                # TODO: 과거 회차 전용 검색 API가 있다면 교체 필요. 현재는 Intro API 기반.
                return None
            
            # 날짜 (첫번째 아이템에서)
            draw_date = self.format_date(target_draw_items[0].get('psltRflYmd', ''))
            
            # 당첨 번호 추출
            # wnSqNo 1: 1등 (조+번호)
            # wnSqNo 2: 2등 (번호 - 조 다름)
            # wnSqNo 3: 3등 (번호 - 1등과 끝자리 다름 등등)
            # ...
            # wnSqNo 21: 보너스?
            
            group = ""
            win_numbers = [] # 연금복권은 번호가 하나임 (조 + 6자리) but structure expects list?
            # Existing code: win_numbers = ["1", "2", "3", "4", "5", "6"] (split chars)
            # New API returns full string e.g. "667975"
            
            rank1_item = next((item for item in target_draw_items if item.get('wnSqNo') == 1), None)
            if rank1_item:
                group = rank1_item.get('wnBndNo', '')
                full_num = rank1_item.get('wnRnkVl', '')
                # 기존 포맷 유지: win_numbers 리스트에 숫자를 하나씩? 아니면 통째로?
                # 기존 코드: for elem in number_elems[1:7]: win_numbers.append(elem.text.strip()) -> ["1", "2", "3", "4", "5", "6"]
                # 문자열을 리스트로 변환
                win_numbers = list(full_num)
            
            # 보너스 (wnSqNo = 21)
            bonus_item = next((item for item in target_draw_items if item.get('wnSqNo') == 21), None)
            bonus_group = "각" # 보너스는 조 없음 (모든 조)
            bonus_numbers = []
            
            if bonus_item:
                full_bonus = bonus_item.get('wnRnkVl', '')
                bonus_numbers = list(full_bonus)
            
            # 당첨 금액 정보 (Intro API에는 상세 등수별 금액/당첨자수는 없고 rnk1Expc, rnk1Jck 등 1등 정보만 있음)
            # 상세 통계는 `selectPstPt720WnInfo.do` (User provided: 연금복권 회차별 세부정보)
            # 필요하다면 추가 호출
            prize_info = self.get_prize_detail(draw_no)
            
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
            
            logger.info(f"회차 {draw_no} 크롤링 완료: {group}조 {''.join(win_numbers)}")
            return result
            
        except Exception as e:
            logger.error(f"회차 {draw_no} 크롤링 실패: {e}")
            return None

    def get_prize_detail(self, draw_no):
        """회차별 등수/당첨금 상세 정보 (별도 API)"""
        # API: selectPstPt720WnInfo.do?srchPsltEpsd=296
        prize_info = []
        try:
            url = f"{BASE_URL}/pt720/selectPstPt720WnInfo.do"
            params = {'srchPsltEpsd': draw_no}
            
            response = self.session.get(url, params=params, headers=self.headers)
            response.raise_for_status()
            
            data = response.json()
            if not data.get('data') or not data['data'].get('result'):
                return prize_info
            
            results = data['data']['result']
            # wnRnk: 등수
            # wnTotalCnt: 전체 당첨자 수
            # wnAmt: 개인별 당첨금? (User sample: wnAmt=27000000 for Rank 3. Rank 1 wnAmt=0?)
            # 1등은 월지급식이라 wnAmt가 0일 수 있음. 
            
            for item in results:
                rank = item.get('wnRnk')
                winner_count = str(item.get('wnTotalCnt', 0))
                
                # 라벨링
                if rank == 1: rank_name = "1등"
                elif rank == 2: rank_name = "2등"
                elif rank == 3: rank_name = "3등"
                elif rank == 4: rank_name = "4등"
                elif rank == 5: rank_name = "5등"
                elif rank == 6: rank_name = "6등"
                elif rank == 7: rank_name = "7등"
                elif rank == 8: rank_name = "보너스" # Sample says rank 8? Check user sample logic.
                # User sample: wnRnk 8 exists. Pension has 7 ranks + Bonus.
                # Usually Bonus is treated separately. But if API returns 8, maybe 8 is Bonus?
                # Sample: wnRnk 8, wnTotalCnt 5. Bonus winners are 5?
                # Usually Bonus draws 1 number (6 digits), matched by 5 people (since there are 5 groups, actually 'All Groups').
                # Wait, Bonus is 1 number, matched against last 6 digits of all groups. Total 5 groups * 1 = 5 winners max?
                # Or 10 winners?
                # Anyway, let's map it.
                else: rank_name = f"{rank}등"
                
                if rank == 8: rank_name = "보너스"

                prize_info.append({
                    'rank': rank_name,
                    'winner_count': winner_count
                })
                
        except Exception as e:
            logger.error(f"당첨금 상세 정보 조회 실패: {e}")
            
        return prize_info
    
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
    
    def update_store_info(self, draw_no):
        """특정 회차의 판매점 정보만 업데이트합니다."""
        # 해당 회차 파일이 존재하는지 확인
        file_path = DRAWS_DIR / f"pension_{draw_no}.json"
        if not file_path.exists():
            logger.error(f"회차 {draw_no}의 데이터 파일이 존재하지 않습니다.")
            return False
            
        # 판매점 정보 크롤링
        store_info = self.get_store_info(draw_no)
        
        # 1등 당첨 판매점 정보가 있는지 확인
        if len(store_info["first_prize_store_info"]) > 0:
            logger.info(f"회차 {draw_no}의 1등 당첨 판매점 정보 업데이트 완료: {len(store_info['first_prize_store_info'])}개")
            return True
        else:
            logger.warning(f"회차 {draw_no}의 1등 당첨 판매점 정보가 아직 없습니다.")
            return False
    
    def update_latest_store_info(self):
        """최신 회차의 판매점 정보만 업데이트합니다."""
        # 인덱스 파일에서 최신 회차 번호 가져오기
        index_path = DATA_DIR / "index.json"
        if not index_path.exists():
            logger.error("인덱스 파일이 존재하지 않습니다.")
            return False
            
        try:
            with open(index_path, 'r', encoding='utf-8') as f:
                index_data = json.load(f)
                
            if not index_data.get('draws'):
                logger.error("인덱스 파일에 회차 정보가 없습니다.")
                return False
                
            # 회차 번호 기준 내림차순 정렬
            draws = sorted(index_data['draws'], key=lambda x: x['draw_no'], reverse=True)
            latest_draw_no = draws[0]['draw_no']
            
            logger.info(f"최신 회차 번호: {latest_draw_no}")
            return self.update_store_info(latest_draw_no)
            
        except Exception as e:
            logger.error(f"최신 회차 판매점 정보 업데이트 실패: {e}")
            return False

def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='연금복권 당첨 정보 크롤러')
    parser.add_argument('--latest', action='store_true', help='최신 회차만 크롤링')
    parser.add_argument('--draw', type=int, help='특정 회차 크롤링')
    parser.add_argument('--range', type=str, help='회차 범위 크롤링 (시작-끝)')
    parser.add_argument('--all', action='store_true', help='모든 회차 크롤링 (1회부터 최신까지)')
    parser.add_argument('--update-store', type=int, help='특정 회차의 판매점 정보만 업데이트')
    parser.add_argument('--update-latest-store', action='store_true', help='최신 회차의 판매점 정보만 업데이트')
    
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
    elif args.update_store:
        crawler.update_store_info(args.update_store)
    elif args.update_latest_store:
        crawler.update_latest_store_info()
    else:
        # 기본값: 최신 회차 크롤링
        crawler.crawl_latest()

if __name__ == "__main__":
    main() 