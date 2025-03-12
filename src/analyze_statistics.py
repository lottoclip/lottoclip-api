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
logger = logging.getLogger('lotto_statistics')

# 상수 정의
DATA_DIR = Path("lotto")
DRAWS_DIR = DATA_DIR / "draws"  # 회차별 데이터 디렉토리 추가
STATISTICS_FILE = DATA_DIR / "statistics.json"

class LottoStatistics:
    def __init__(self):
        """로또 통계 분석기 초기화"""
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
        lotto/draws 디렉토리에서 모든 로또 추첨 데이터를 로드합니다.
        """
        all_data = []
        for file_path in glob.glob(os.path.join(self.draws_dir, "lotto_*.json")):
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
                        
                    if 'bonus_number' not in data:
                        filename = os.path.basename(file_path)
                        logger.warning(f"파일에 bonus_number 필드가 없습니다: {filename}")
                        data['bonus_number'] = 0
                    
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
        # 일반 번호 카운터
        regular_counter = Counter()
        # 보너스 번호 카운터
        bonus_counter = Counter()
        
        # 모든 데이터에서 번호 카운트
        for draw_data in draw_data_list:
            # 일반 번호 카운트
            for num in draw_data['numbers']:
                regular_counter[num] += 1
            
            # 보너스 번호 카운트
            bonus_counter[draw_data['bonus_number']] += 1
        
        # 전체 회차 수
        total_draws = len(draw_data_list)
        
        # 모든 번호(1-45)에 대한 빈도 계산
        all_numbers_frequency = []
        for num in range(1, 46):
            regular_freq = regular_counter.get(num, 0)
            bonus_freq = bonus_counter.get(num, 0)
            total_freq = regular_freq + bonus_freq
            
            # 백분율 계산 (일반 번호는 6개씩 뽑으므로 전체 회차 수의 6배 중 비율)
            regular_percentage = (regular_freq / (total_draws * 6)) * 100 if total_draws > 0 else 0
            bonus_percentage = (bonus_freq / total_draws) * 100 if total_draws > 0 else 0
            total_percentage = (total_freq / (total_draws * 7)) * 100 if total_draws > 0 else 0
            
            all_numbers_frequency.append({
                'number': num,
                'frequency': total_freq,
                'regular_frequency': regular_freq,
                'bonus_frequency': bonus_freq,
                'percentage': round(total_percentage, 2),
                'regular_percentage': round(regular_percentage, 2),
                'bonus_percentage': round(bonus_percentage, 2)
            })
        
        # 전체 빈도 기준 정렬
        all_numbers_frequency.sort(key=lambda x: x['frequency'], reverse=True)
        
        # 일반 번호 빈도 기준 정렬
        regular_frequency = sorted(
            [x for x in all_numbers_frequency],
            key=lambda x: x['regular_frequency'],
            reverse=True
        )
        
        # 보너스 번호 빈도 기준 정렬
        bonus_frequency = sorted(
            [x for x in all_numbers_frequency],
            key=lambda x: x['bonus_frequency'],
            reverse=True
        )
        
        return {
            'all_numbers_frequency': all_numbers_frequency,
            'regular_frequency': regular_frequency,
            'bonus_frequency': bonus_frequency,
            'most_frequent_numbers': all_numbers_frequency[:5],
            'least_frequent_numbers': all_numbers_frequency[-5:]
        }
    
    def analyze_number_patterns(self, draw_data_list):
        """번호 패턴을 분석합니다."""
        # 홀짝 비율 분석
        odd_even_ratios = []
        
        # 구간별 분포 분석 (1-9, 10-19, 20-29, 30-39, 40-45)
        range_distributions = []
        
        # 연속 번호 패턴 분석
        consecutive_patterns = []
        
        # 각 회차별 분석
        for draw_data in draw_data_list:
            numbers = draw_data['numbers']
            
            # 홀짝 비율
            odd_count = sum(1 for num in numbers if num % 2 == 1)
            even_count = 6 - odd_count
            
            odd_even_ratios.append({
                'draw_no': draw_data['draw_no'],
                'odd_count': odd_count,
                'even_count': even_count,
                'ratio': f"{odd_count}:{even_count}"
            })
            
            # 구간별 분포
            ranges = [0, 0, 0, 0, 0]  # 1-9, 10-19, 20-29, 30-39, 40-45
            
            for num in numbers:
                if 1 <= num <= 9:
                    ranges[0] += 1
                elif 10 <= num <= 19:
                    ranges[1] += 1
                elif 20 <= num <= 29:
                    ranges[2] += 1
                elif 30 <= num <= 39:
                    ranges[3] += 1
                elif 40 <= num <= 45:
                    ranges[4] += 1
            
            range_distributions.append({
                'draw_no': draw_data['draw_no'],
                'ranges': ranges,
                'distribution': f"{ranges[0]}-{ranges[1]}-{ranges[2]}-{ranges[3]}-{ranges[4]}"
            })
            
            # 연속 번호 패턴
            sorted_numbers = sorted(numbers)
            consecutive_count = 0
            
            for i in range(1, len(sorted_numbers)):
                if sorted_numbers[i] == sorted_numbers[i-1] + 1:
                    consecutive_count += 1
            
            consecutive_patterns.append({
                'draw_no': draw_data['draw_no'],
                'consecutive_count': consecutive_count
            })
        
        # 홀짝 비율 통계
        odd_even_stats = self._calculate_pattern_stats(odd_even_ratios, 'ratio')
        
        # 구간별 분포 통계
        range_stats = self._calculate_pattern_stats(range_distributions, 'distribution')
        
        # 연속 번호 통계
        consecutive_stats = {
            'patterns': consecutive_patterns,
            'average': sum(p['consecutive_count'] for p in consecutive_patterns) / len(consecutive_patterns) if consecutive_patterns else 0,
            'max': max(consecutive_patterns, key=lambda x: x['consecutive_count'])['consecutive_count'] if consecutive_patterns else 0,
            'min': min(consecutive_patterns, key=lambda x: x['consecutive_count'])['consecutive_count'] if consecutive_patterns else 0
        }
        
        return {
            'odd_even_stats': odd_even_stats,
            'range_stats': range_stats,
            'consecutive_stats': consecutive_stats
        }
    
    def _calculate_pattern_stats(self, pattern_data, key_field):
        """패턴 데이터의 통계를 계산합니다."""
        counter = Counter(item[key_field] for item in pattern_data)
        total = len(pattern_data)
        
        stats = [
            {
                'pattern': pattern,
                'count': count,
                'percentage': round((count / total) * 100, 2) if total > 0 else 0
            }
            for pattern, count in counter.most_common()
        ]
        
        return {
            'total': total,
            'stats': stats
        }
    
    def analyze_store_statistics(self, draw_data_list):
        """판매점 통계를 분석합니다."""
        # 지역별 1등 당첨 횟수
        region_counter = Counter()
        
        # 판매점별 1등 당첨 횟수
        store_counter = defaultdict(int)
        
        # 판매점 유형별 당첨 횟수
        type_counter = Counter()
        
        # 판매점 정보 로드
        stores_data = {}
        try:
            stores_file = self.data_dir / "lotto_stores.json"
            with open(stores_file, 'r', encoding='utf-8') as f:
                stores_data = json.load(f)
        except Exception as e:
            logger.error(f"판매점 정보 로드 실패: {e}")
        
        for draw_data in draw_data_list:
            # first_prize_store_info 또는 first_prize_store_ids 필드가 있는지 확인
            store_ids = []
            store_types = {}
            
            if 'first_prize_store_info' in draw_data:
                for store_info in draw_data['first_prize_store_info']:
                    store_ids.append(store_info['store_id'])
                    store_types[store_info['store_id']] = store_info.get('type', '알 수 없음')
            elif 'first_prize_store_ids' in draw_data:
                store_ids = draw_data['first_prize_store_ids']
            
            for store_id in store_ids:
                # 판매점 정보 확인
                if store_id in stores_data:
                    store = stores_data[store_id]
                    # 지역 추출 (주소에서 첫 번째 공백 이전까지)
                    address = store.get('address', '')
                    region = address.split(' ')[0] if address else '알 수 없음'
                    
                    region_counter[region] += 1
                    store_counter[store.get('name', '알 수 없음')] += 1
                    
                    # 유형 정보는 first_prize_store_info에서 가져오거나 기본값 사용
                    store_type = store_types.get(store_id, '알 수 없음')
                    type_counter[store_type] += 1
        
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
        
        # 판매점 유형별 통계
        type_stats = [
            {
                'type': type_name,
                'count': count,
                'percentage': round((count / sum(type_counter.values())) * 100, 2) if type_counter else 0
            }
            for type_name, count in type_counter.most_common()
        ]
        
        return {
            'region_stats': region_stats,
            'top_stores': top_stores,
            'type_stats': type_stats
        }
    
    def analyze_consecutive_numbers(self, draw_data_list):
        """연속 번호 출현 패턴을 분석합니다."""
        consecutive_pairs = {}  # 연속된 번호 쌍의 출현 횟수
        draws_with_consecutive = 0  # 연속 번호가 있는 회차 수
        draws_with_multiple_consecutive = 0  # 2쌍 이상의 연속 번호가 있는 회차 수
        
        for draw_data in draw_data_list:
            numbers = sorted(draw_data['numbers'])
            consecutive_count = 0
            consecutive_pairs_in_draw = []
            
            # 연속된 번호 쌍 찾기
            for i in range(len(numbers) - 1):
                if numbers[i + 1] == numbers[i] + 1:
                    consecutive_count += 1
                    pair = (numbers[i], numbers[i + 1])
                    consecutive_pairs_in_draw.append(pair)
                    
                    # 연속된 번호 쌍 카운트
                    if pair in consecutive_pairs:
                        consecutive_pairs[pair] += 1
                    else:
                        consecutive_pairs[pair] = 1
            
            # 연속 번호가 있는 회차 카운트
            if consecutive_count > 0:
                draws_with_consecutive += 1
                
            # 2쌍 이상의 연속 번호가 있는 회차 카운트
            if consecutive_count >= 2:
                draws_with_multiple_consecutive += 1
        
        # 결과 정리
        total_draws = len(draw_data_list)
        consecutive_pairs_sorted = sorted(consecutive_pairs.items(), key=lambda x: x[1], reverse=True)
        
        top_consecutive_pairs = [
            {
                "pair": f"{pair[0]}-{pair[1]}",
                "count": count,
                "percentage": round((count / total_draws) * 100, 2)
            }
            for pair, count in consecutive_pairs_sorted[:10]  # 상위 10개만
        ]
        
        return {
            "total_draws": total_draws,
            "draws_with_consecutive": draws_with_consecutive,
            "draws_with_consecutive_percentage": round((draws_with_consecutive / total_draws) * 100, 2) if total_draws > 0 else 0,
            "draws_with_multiple_consecutive": draws_with_multiple_consecutive,
            "draws_with_multiple_consecutive_percentage": round((draws_with_multiple_consecutive / total_draws) * 100, 2) if total_draws > 0 else 0,
            "top_consecutive_pairs": top_consecutive_pairs
        }
    
    def analyze_number_gaps(self, draw_data_list):
        """당첨 번호 간의 간격을 분석합니다."""
        gap_frequencies = {}  # 간격별 빈도
        avg_gaps_per_draw = []  # 회차별 평균 간격
        
        for draw_data in draw_data_list:
            numbers = sorted(draw_data['numbers'])
            gaps = []
            
            # 번호 간 간격 계산
            for i in range(len(numbers) - 1):
                gap = numbers[i + 1] - numbers[i]
                gaps.append(gap)
                
                # 간격 빈도 카운트
                if gap in gap_frequencies:
                    gap_frequencies[gap] += 1
                else:
                    gap_frequencies[gap] = 1
            
            # 회차별 평균 간격 계산
            avg_gap = sum(gaps) / len(gaps) if gaps else 0
            avg_gaps_per_draw.append({
                "draw_no": draw_data['draw_no'],
                "avg_gap": round(avg_gap, 2)
            })
        
        # 결과 정리
        total_gap_count = sum(gap_frequencies.values())
        gap_frequencies_sorted = sorted(gap_frequencies.items(), key=lambda x: x[0])
        
        gap_distribution = [
            {
                "gap": gap,
                "count": count,
                "percentage": round((count / total_gap_count) * 100, 2) if total_gap_count > 0 else 0
            }
            for gap, count in gap_frequencies_sorted
        ]
        
        # 가장 빈번한 간격
        most_common_gaps = sorted(gap_frequencies.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # 전체 평균 간격
        overall_avg_gap = sum(item["avg_gap"] for item in avg_gaps_per_draw) / len(avg_gaps_per_draw) if avg_gaps_per_draw else 0
        
        return {
            "gap_distribution": gap_distribution,
            "most_common_gaps": [
                {
                    "gap": gap,
                    "count": count,
                    "percentage": round((count / total_gap_count) * 100, 2) if total_gap_count > 0 else 0
                }
                for gap, count in most_common_gaps
            ],
            "overall_avg_gap": round(overall_avg_gap, 2),
            "recent_avg_gaps": avg_gaps_per_draw[-10:] if len(avg_gaps_per_draw) >= 10 else avg_gaps_per_draw
        }
    
    def analyze_sum_and_average(self, draw_data_list):
        """당첨 번호의 합계 및 평균을 분석합니다."""
        sum_frequencies = {}  # 합계별 빈도
        avg_frequencies = {}  # 평균별 빈도 (소수점 첫째 자리까지)
        
        # 합계 범위 구간 정의
        sum_ranges = {
            "70-90": 0,
            "91-110": 0,
            "111-130": 0,
            "131-150": 0,
            "151-170": 0,
            "171-190": 0,
            "191-210": 0,
            "211-230": 0,
            "기타": 0
        }
        
        for draw_data in draw_data_list:
            numbers = draw_data['numbers']
            
            # 합계 계산
            numbers_sum = sum(numbers)
            if numbers_sum in sum_frequencies:
                sum_frequencies[numbers_sum] += 1
            else:
                sum_frequencies[numbers_sum] = 1
            
            # 평균 계산 (소수점 첫째 자리까지)
            numbers_avg = round(numbers_sum / len(numbers), 1)
            if numbers_avg in avg_frequencies:
                avg_frequencies[numbers_avg] += 1
            else:
                avg_frequencies[numbers_avg] = 1
            
            # 합계 범위 카운트
            if 70 <= numbers_sum <= 90:
                sum_ranges["70-90"] += 1
            elif 91 <= numbers_sum <= 110:
                sum_ranges["91-110"] += 1
            elif 111 <= numbers_sum <= 130:
                sum_ranges["111-130"] += 1
            elif 131 <= numbers_sum <= 150:
                sum_ranges["131-150"] += 1
            elif 151 <= numbers_sum <= 170:
                sum_ranges["151-170"] += 1
            elif 171 <= numbers_sum <= 190:
                sum_ranges["171-190"] += 1
            elif 191 <= numbers_sum <= 210:
                sum_ranges["191-210"] += 1
            elif 211 <= numbers_sum <= 230:
                sum_ranges["211-230"] += 1
            else:
                sum_ranges["기타"] += 1
        
        # 결과 정리
        total_draws = len(draw_data_list)
        
        # 합계 분포
        sum_distribution = [
            {
                "range": range_name,
                "count": count,
                "percentage": round((count / total_draws) * 100, 2) if total_draws > 0 else 0
            }
            for range_name, count in sum_ranges.items() if count > 0
        ]
        
        # 가장 빈번한 합계
        most_common_sums = sorted(sum_frequencies.items(), key=lambda x: x[1], reverse=True)[:10]
        
        # 가장 빈번한 평균
        most_common_avgs = sorted(avg_frequencies.items(), key=lambda x: x[1], reverse=True)[:10]
        
        # 전체 평균 합계
        all_sums = [sum(draw_data['numbers']) for draw_data in draw_data_list]
        overall_avg_sum = sum(all_sums) / len(all_sums) if all_sums else 0
        
        return {
            "sum_distribution": sum_distribution,
            "most_common_sums": [
                {
                    "sum": sum_val,
                    "count": count,
                    "percentage": round((count / total_draws) * 100, 2) if total_draws > 0 else 0
                }
                for sum_val, count in most_common_sums
            ],
            "most_common_avgs": [
                {
                    "avg": avg_val,
                    "count": count,
                    "percentage": round((count / total_draws) * 100, 2) if total_draws > 0 else 0
                }
                for avg_val, count in most_common_avgs
            ],
            "overall_avg_sum": round(overall_avg_sum, 2),
            "min_sum": min(all_sums) if all_sums else 0,
            "max_sum": max(all_sums) if all_sums else 0
        }
    
    def analyze_dormant_periods(self, draw_data_list):
        """각 번호의 휴면기간을 분석합니다."""
        # 로또 번호 범위 (1-45)
        all_numbers = list(range(1, 46))
        
        # 각 번호별 마지막 출현 회차
        last_appearance = {num: 0 for num in all_numbers}
        
        # 각 번호별 휴면기간 목록
        dormant_periods = {num: [] for num in all_numbers}
        
        # 정렬된 회차 데이터
        sorted_draws = sorted(draw_data_list, key=lambda x: x['draw_no'])
        latest_draw_no = sorted_draws[-1]['draw_no'] if sorted_draws else 0
        
        # 각 회차별로 번호 출현 여부 확인
        for draw_data in sorted_draws:
            draw_no = draw_data['draw_no']
            numbers = draw_data['numbers']
            
            for num in all_numbers:
                if num in numbers:
                    # 이전 출현 이후 휴면기간 계산
                    if last_appearance[num] > 0:
                        dormant_period = draw_no - last_appearance[num] - 1
                        dormant_periods[num].append(dormant_period)
                    
                    # 마지막 출현 회차 업데이트
                    last_appearance[num] = draw_no
        
        # 현재 휴면기간 계산 (마지막 출현 이후 지금까지)
        current_dormant = {
            num: latest_draw_no - last_appearance[num] if last_appearance[num] > 0 else latest_draw_no
            for num in all_numbers
        }
        
        # 평균 휴면기간 계산
        avg_dormant_periods = {
            num: sum(periods) / len(periods) if periods else 0
            for num, periods in dormant_periods.items()
        }
        
        # 결과 정리
        dormant_stats = []
        for num in all_numbers:
            dormant_stats.append({
                "number": num,
                "current_dormant": current_dormant[num],
                "avg_dormant": round(avg_dormant_periods[num], 2),
                "max_dormant": max(dormant_periods[num]) if dormant_periods[num] else 0,
                "appearance_count": len(dormant_periods[num]) + (1 if last_appearance[num] > 0 else 0)
            })
        
        # 현재 휴면기간 기준 정렬
        dormant_stats_by_current = sorted(dormant_stats, key=lambda x: x['current_dormant'], reverse=True)
        
        # 평균 휴면기간 기준 정렬
        dormant_stats_by_avg = sorted(dormant_stats, key=lambda x: x['avg_dormant'], reverse=True)
        
        # 최근 10회차 동안 나오지 않은 번호
        recent_draws = sorted_draws[-10:] if len(sorted_draws) >= 10 else sorted_draws
        recent_numbers = set()
        for draw in recent_draws:
            recent_numbers.update(draw['numbers'])
        
        not_in_recent = [num for num in all_numbers if num not in recent_numbers]
        
        return {
            "top_dormant_current": dormant_stats_by_current[:10],  # 현재 가장 오래 나오지 않은 번호 10개
            "top_dormant_avg": dormant_stats_by_avg[:10],  # 평균적으로 가장 오래 나오지 않는 번호 10개
            "not_in_recent_10": sorted(not_in_recent),  # 최근 10회차 동안 나오지 않은 번호
            "overall_stats": dormant_stats  # 전체 번호별 통계
        }
    
    def analyze_auto_manual_ratio(self, draw_data_list):
        """자동/수동 당첨 비율을 분석합니다."""
        auto_count = 0
        manual_count = 0
        draws_with_type_info = 0
        
        # 회차별 자동/수동 비율
        draw_ratios = []
        
        for draw_data in draw_data_list:
            # first_prize_store_info 필드가 있는지 확인
            if 'first_prize_store_info' in draw_data:
                draws_with_type_info += 1
                
                # 회차별 자동/수동 카운트
                draw_auto_count = 0
                draw_manual_count = 0
                
                for store_info in draw_data['first_prize_store_info']:
                    if 'type' in store_info:
                        if store_info['type'] == '자동':
                            auto_count += 1
                            draw_auto_count += 1
                        elif store_info['type'] == '수동':
                            manual_count += 1
                            draw_manual_count += 1
                
                # 회차별 비율 계산
                total_winners = draw_auto_count + draw_manual_count
                if total_winners > 0:
                    draw_ratios.append({
                        "draw_no": draw_data['draw_no'],
                        "draw_date": draw_data['draw_date'],
                        "auto_count": draw_auto_count,
                        "manual_count": draw_manual_count,
                        "auto_percentage": round((draw_auto_count / total_winners) * 100, 2),
                        "manual_percentage": round((draw_manual_count / total_winners) * 100, 2)
                    })
        
        # 전체 비율 계산
        total_winners = auto_count + manual_count
        auto_percentage = round((auto_count / total_winners) * 100, 2) if total_winners > 0 else 0
        manual_percentage = round((manual_count / total_winners) * 100, 2) if total_winners > 0 else 0
        
        # 최근 10회차 추이
        recent_ratios = sorted(draw_ratios, key=lambda x: x['draw_no'], reverse=True)[:10]
        
        # 자동 비율이 가장 높았던 회차
        highest_auto_ratio = sorted(draw_ratios, key=lambda x: x['auto_percentage'], reverse=True)[:5] if draw_ratios else []
        
        # 수동 비율이 가장 높았던 회차
        highest_manual_ratio = sorted(draw_ratios, key=lambda x: x['manual_percentage'], reverse=True)[:5] if draw_ratios else []
        
        return {
            "total_stats": {
                "auto_count": auto_count,
                "manual_count": manual_count,
                "auto_percentage": auto_percentage,
                "manual_percentage": manual_percentage,
                "total_winners": total_winners
            },
            "draws_with_type_info": draws_with_type_info,
            "recent_ratios": recent_ratios,
            "highest_auto_ratio": highest_auto_ratio,
            "highest_manual_ratio": highest_manual_ratio
        }
    
    def analyze_regional_stats(self, draw_data_list):
        """지역별 당첨 통계를 분석합니다."""
        # 지역 구분 (주소 앞부분 기준)
        regions = {
            "서울": 0,
            "경기": 0,
            "인천": 0,
            "강원": 0,
            "충북": 0,
            "충남": 0,
            "대전": 0,
            "세종": 0,
            "경북": 0,
            "경남": 0,
            "대구": 0,
            "울산": 0,
            "부산": 0,
            "전북": 0,
            "전남": 0,
            "광주": 0,
            "제주": 0,
            "기타": 0
        }
        
        # 지역별 당첨 횟수
        region_counts = dict(regions)
        
        # 지역별 당첨 판매점 목록
        region_stores = {region: [] for region in regions.keys()}
        
        # 판매점 정보 로드
        stores_data = {}
        try:
            stores_file = self.data_dir / "lotto_stores.json"
            with open(stores_file, 'r', encoding='utf-8') as f:
                stores_data = json.load(f)
        except Exception as e:
            logger.error(f"판매점 정보 로드 실패: {e}")
        
        # 각 회차별 당첨 판매점 분석
        total_wins = 0
        for draw_data in draw_data_list:
            # first_prize_store_info 또는 first_prize_store_ids 필드가 있는지 확인
            store_ids = []
            
            if 'first_prize_store_info' in draw_data:
                store_ids = [store['store_id'] for store in draw_data['first_prize_store_info']]
            elif 'first_prize_store_ids' in draw_data:
                store_ids = draw_data['first_prize_store_ids']
            
            for store_id in store_ids:
                total_wins += 1
                
                # 판매점 정보 확인
                if store_id in stores_data:
                    store = stores_data[store_id]
                    address = store.get('address', '')
                    
                    # 지역 추출
                    region = '기타'
                    for r in regions.keys():
                        if address.startswith(r):
                            region = r
                            break
                    
                    # 지역별 카운트 증가
                    region_counts[region] += 1
                    
                    # 지역별 판매점 목록에 추가
                    store_info = {
                        'store_id': store_id,
                        'name': store.get('name', '알 수 없음'),
                        'address': address,
                        'draw_no': draw_data.get('draw_no', 0)
                    }
                    
                    if store_info not in region_stores[region]:
                        region_stores[region].append(store_info)
        
        # 지역별 통계 정렬 (당첨 횟수 기준)
        region_stats_sorted = [
            {
                'region': region,
                'wins': count,
                'percentage': round((count / total_wins) * 100, 2) if total_wins > 0 else 0
            }
            for region, count in sorted(region_counts.items(), key=lambda x: x[1], reverse=True)
            if count > 0
        ]
        
        # 지역별 상위 판매점
        top_stores_by_region = {}
        for region, stores in region_stores.items():
            if stores:
                # 판매점별 당첨 횟수 계산
                store_counts = defaultdict(int)
                for store in stores:
                    key = (store['store_id'], store['name'])
                    store_counts[key] += 1
                
                # 상위 5개 판매점 추출
                top_stores_by_region[region] = [
                    {
                        'store_id': store_id,
                        'name': name,
                        'wins': count
                    }
                    for (store_id, name), count in sorted(store_counts.items(), key=lambda x: x[1], reverse=True)[:5]
                ]
        
        return {
            "total_wins": total_wins,
            "region_stats": region_stats_sorted,
            "top_regions": region_stats_sorted[:5],  # 상위 5개 지역
            "top_stores_by_region": top_stores_by_region
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
        
        # 번호 패턴 분석
        pattern_stats = self.analyze_number_patterns(draw_data_list)
        
        # 판매점 통계 분석
        store_stats = self.analyze_store_statistics(draw_data_list)
        
        # 연속 번호 패턴 분석
        consecutive_stats = self.analyze_consecutive_numbers(draw_data_list)
        
        # 번호 간격 분석
        gap_stats = self.analyze_number_gaps(draw_data_list)
        
        # 합계 및 평균 분석
        sum_and_avg_stats = self.analyze_sum_and_average(draw_data_list)
        
        # 휴면기간 분석
        dormant_stats = self.analyze_dormant_periods(draw_data_list)
        
        # 자동/수동 당첨 비율 분석
        auto_manual_ratio_stats = self.analyze_auto_manual_ratio(draw_data_list)
        
        # 지역별 당첨 통계 분석
        regional_stats = self.analyze_regional_stats(draw_data_list)
        
        # 전체 통계 데이터 구성
        statistics = {
            'total_draws': len(draw_data_list),
            'first_draw': draw_data_list[0]['draw_no'] if draw_data_list else None,
            'last_draw': draw_data_list[-1]['draw_no'] if draw_data_list else None,
            'frequency_stats': frequency_stats,
            'pattern_stats': pattern_stats,
            'store_stats': store_stats,
            'consecutive_stats': consecutive_stats,
            'gap_stats': gap_stats,
            'sum_and_avg_stats': sum_and_avg_stats,
            'dormant_stats': dormant_stats,
            'auto_manual_ratio_stats': auto_manual_ratio_stats,
            'regional_stats': regional_stats,
            'updated_at': draw_data_list[-1]['updated_at'] if draw_data_list else None
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
        except Exception as e:
            import traceback
            logger.error(f"통계 분석 실패: {e}")
            logger.error(traceback.format_exc())  # 상세 오류 스택 트레이스 출력

def main():
    """메인 함수"""
    try:
        analyzer = LottoStatistics()
        success = analyzer.run()
        return 0 if success else 1
    except Exception as e:
        logger.error(f"통계 분석 실패: {e}")
        return 1

if __name__ == "__main__":
    main() 