#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import logging
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime
import glob

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger('pension_statistics')

# 상수 정의
DATA_DIR = Path("pension")
DRAWS_DIR = DATA_DIR / "draws"  # 회차별 데이터 디렉토리 추가
STATISTICS_FILE = DATA_DIR / "statistics.json"

class PensionStatistics:
    def __init__(self):
        """연금복권 통계 분석기 초기화"""
        if not os.path.exists(DATA_DIR):
            raise FileNotFoundError(f"데이터 디렉토리가 존재하지 않습니다: {DATA_DIR}")
        if not os.path.exists(DRAWS_DIR):
            raise FileNotFoundError(f"회차별 데이터 디렉토리가 존재하지 않습니다: {DRAWS_DIR}")
        
        # 데이터 디렉토리 설정
        self.data_dir = DATA_DIR
        self.draws_dir = DRAWS_DIR
        self.stores_dir = DATA_DIR / "stores"
    
    def load_all_draw_data(self):
        """
        pension/draws 디렉토리에서 모든 연금복권 추첨 데이터를 로드합니다.
        """
        all_data = []
        for file_path in glob.glob(os.path.join(self.draws_dir, "pension_*.json")):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    # 필수 필드 확인 및 기본값 설정
                    if 'draw_no' not in data:
                        filename = os.path.basename(file_path)
                        logger.warning(f"파일에 draw_no 필드가 없습니다: {filename}")
                        data['draw_no'] = 0
                        
                    if 'numbers' not in data:
                        filename = os.path.basename(file_path)
                        logger.warning(f"파일에 numbers 필드가 없습니다: {filename}")
                        data['numbers'] = []
                    
                    all_data.append(data)
                    logger.info(f"파일 로드 성공: {os.path.basename(file_path)}, 회차: {data.get('draw_no', '알 수 없음')}")
            except Exception as e:
                logger.error(f"파일 로드 실패: {file_path}, 오류: {str(e)}")
        
        # draw_no 필드가 있는 데이터만 정렬
        try:
            all_data.sort(key=lambda x: x['draw_no'])
        except Exception as e:
            logger.warning(f"일부 데이터에 draw_no 필드가 없어 정렬을 건너뜁니다.")
        
        logger.info(f"총 {len(all_data)}개 회차 데이터 로드 완료")
        return all_data
    
    def analyze_number_frequency(self, draw_data_list):
        """번호별 출현 빈도를 분석합니다."""
        # 조별 카운터
        group_counter = Counter()
        
        # 각 자리별 번호 카운터 (6자리)
        position_counters = [Counter() for _ in range(6)]
        
        # 보너스 번호 카운터
        bonus_counters = [Counter() for _ in range(6)]
        
        # 모든 데이터에서 번호 카운트
        for draw_data in draw_data_list:
            # 조 카운트
            if 'group' in draw_data:
                group_counter[draw_data['group']] += 1
            
            # 각 자리별 번호 카운트
            if 'numbers' in draw_data and len(draw_data['numbers']) == 6:
                for i, num in enumerate(draw_data['numbers']):
                    position_counters[i][num] += 1
            
            # 보너스 번호 카운트
            if 'bonus_numbers' in draw_data and len(draw_data['bonus_numbers']) == 6:
                for i, num in enumerate(draw_data['bonus_numbers']):
                    bonus_counters[i][num] += 1
        
        # 전체 회차 수
        total_draws = len(draw_data_list)
        
        # 조별 빈도 분석
        group_frequency = []
        for group, count in group_counter.most_common():
            percentage = (count / total_draws) * 100 if total_draws > 0 else 0
            group_frequency.append({
                'group': group,
                'count': count,
                'percentage': round(percentage, 2)
            })
        
        # 각 자리별 번호 빈도 분석
        position_frequency = []
        for i, counter in enumerate(position_counters):
            position_stats = []
            for num, count in counter.most_common():
                percentage = (count / total_draws) * 100 if total_draws > 0 else 0
                position_stats.append({
                    'number': num,
                    'count': count,
                    'percentage': round(percentage, 2)
                })
            position_frequency.append({
                'position': i + 1,  # 1-indexed position
                'stats': position_stats
            })
        
        # 보너스 번호 빈도 분석
        bonus_frequency = []
        for i, counter in enumerate(bonus_counters):
            position_stats = []
            for num, count in counter.most_common():
                percentage = (count / total_draws) * 100 if total_draws > 0 else 0
                position_stats.append({
                    'number': num,
                    'count': count,
                    'percentage': round(percentage, 2)
                })
            bonus_frequency.append({
                'position': i + 1,  # 1-indexed position
                'stats': position_stats
            })
        
        return {
            'group_frequency': group_frequency,
            'position_frequency': position_frequency,
            'bonus_frequency': bonus_frequency,
            'total_draws': total_draws
        }
    
    def analyze_prize_distribution(self, draw_data_list):
        """등수별 당첨자 수 분포를 분석합니다."""
        # 등수별 당첨자 수 카운터
        rank_counters = defaultdict(list)
        
        for draw_data in draw_data_list:
            if 'prize_info' in draw_data:
                for prize in draw_data['prize_info']:
                    if 'rank' in prize and 'winner_count' in prize:
                        # 쉼표 제거 후 숫자로 변환
                        try:
                            winner_count = int(prize['winner_count'].replace(',', ''))
                        except ValueError:
                            winner_count = 0
                        
                        rank_counters[prize['rank']].append(winner_count)
        
        # 등수별 통계 계산
        rank_stats = []
        for rank, counts in sorted(rank_counters.items()):
            if counts:
                avg_count = sum(counts) / len(counts)
                max_count = max(counts)
                min_count = min(counts)
                
                rank_stats.append({
                    'rank': rank,
                    'average_winners': round(avg_count, 2),
                    'max_winners': max_count,
                    'min_winners': min_count,
                    'total_winners': sum(counts)
                })
        
        return {
            'rank_stats': rank_stats
        }
    
    def analyze_store_statistics(self, draw_data_list):
        """판매점 통계를 분석합니다."""
        # 지역별 당첨 횟수
        region_counter = Counter()
        
        # 판매점별 당첨 횟수
        store_counter = defaultdict(int)
        
        # 모든 회차의 판매점 정보 로드
        for draw_data in draw_data_list:
            draw_no = draw_data.get('draw_no')
            if not draw_no:
                continue
                
            store_file = self.stores_dir / f"stores_{draw_no}.json"
            if not os.path.exists(store_file):
                continue
                
            try:
                with open(store_file, 'r', encoding='utf-8') as f:
                    store_data = json.load(f)
                    
                    # 1등 판매점 분석
                    for store in store_data.get('first_prize_store_info', []):
                        if 'name' in store and 'address' in store:
                            # 지역 추출 (주소에서 첫 번째 공백 이전까지)
                            address = store['address']
                            region = address.split(' ')[0] if address else '알 수 없음'
                            
                            region_counter[region] += 1
                            store_counter[store['name']] += 1
                    
                    # 2등 판매점 분석
                    for store in store_data.get('second_prize_store_info', []):
                        if 'name' in store and 'address' in store:
                            # 지역 추출 (주소에서 첫 번째 공백 이전까지)
                            address = store['address']
                            region = address.split(' ')[0] if address else '알 수 없음'
                            
                            region_counter[region] += 1
                            store_counter[store['name']] += 1
                    
                    # 보너스 판매점 분석
                    for store in store_data.get('bonus_prize_store_info', []):
                        if 'name' in store and 'address' in store:
                            # 지역 추출 (주소에서 첫 번째 공백 이전까지)
                            address = store['address']
                            region = address.split(' ')[0] if address else '알 수 없음'
                            
                            region_counter[region] += 1
                            store_counter[store['name']] += 1
            except Exception as e:
                logger.error(f"판매점 정보 로드 실패: {store_file} - {e}")
        
        # 지역별 통계
        region_stats = [
            {
                'region': region,
                'count': count,
                'percentage': round((count / sum(region_counter.values())) * 100, 2) if region_counter else 0
            }
            for region, count in region_counter.most_common()
        ]
        
        # 가장 많이 당첨된 판매점
        top_stores = [
            {
                'name': store,
                'count': count
            }
            for store, count in sorted(store_counter.items(), key=lambda x: x[1], reverse=True)[:10]
        ]
        
        return {
            'region_stats': region_stats,
            'top_stores': top_stores
        }
    
    def generate_statistics(self):
        """모든 통계 데이터를 생성합니다."""
        # 모든 당첨 데이터 로드
        draw_data_list = self.load_all_draw_data()
        
        if not draw_data_list:
            logger.error("분석할 데이터가 없습니다.")
            return None
        
        # 번호 빈도 분석
        frequency_stats = self.analyze_number_frequency(draw_data_list)
        
        # 등수별 당첨자 수 분포 분석
        prize_stats = self.analyze_prize_distribution(draw_data_list)
        
        # 판매점 통계 분석
        store_stats = self.analyze_store_statistics(draw_data_list)
        
        # 전체 통계 데이터 구성
        statistics = {
            'total_draws': len(draw_data_list),
            'first_draw': draw_data_list[0]['draw_no'] if draw_data_list else None,
            'last_draw': draw_data_list[-1]['draw_no'] if draw_data_list else None,
            'frequency_stats': frequency_stats,
            'prize_stats': prize_stats,
            'store_stats': store_stats,
            'updated_at': datetime.now().isoformat()
        }
        
        return statistics
    
    def save_statistics(self, statistics):
        """통계 데이터를 파일로 저장합니다."""
        if not statistics:
            return False
        
        try:
            with open(STATISTICS_FILE, 'w', encoding='utf-8') as f:
                json.dump(statistics, f, ensure_ascii=False, indent=2)
            logger.info(f"통계 데이터 저장 완료: {STATISTICS_FILE}")
            return True
        except Exception as e:
            logger.error(f"통계 데이터 저장 실패: {e}")
            return False
    
    def run(self):
        """통계 분석을 실행합니다."""
        try:
            statistics = self.generate_statistics()
            self.save_statistics(statistics)
            logger.info("통계 분석 완료")
            return True
        except Exception as e:
            import traceback
            logger.error(f"통계 분석 실패: {e}")
            logger.error(traceback.format_exc())  # 상세 오류 스택 트레이스 출력
            return False

def main():
    """메인 함수"""
    try:
        analyzer = PensionStatistics()
        success = analyzer.run()
        return 0 if success else 1
    except Exception as e:
        logger.error(f"통계 분석 실패: {e}")
        return 1

if __name__ == "__main__":
    main() 