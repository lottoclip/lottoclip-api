# 로또 당첨 데이터 수집 및 분석 서비스

이 프로젝트는 동행복권 웹사이트에서 로또 6/45 당첨 데이터를 자동으로 수집하고, 이를 분석하여 유용한 통계 정보를 제공하는 시스템입니다.

## 주요 기능

- 로또 당첨번호 및 판매점 정보 자동 수집
- 번호별 출현 빈도 등 통계 데이터 제공
- GitHub Actions를 통한 자동화된 데이터 수집
- GitHub Pages를 통한 API 서비스 제공
- 회차 번호(`draw_no`) 기준 내림차순 정렬된 데이터 제공

## 데이터 API

- 전체 회차 목록: `/lotto/index.json`
- 특정 회차 상세 정보: `/lotto/draws/lotto_{회차번호}.json`
- 통계 분석 데이터: `/lotto/statistics.json`
- 판매점 정보: `/lotto/stores/{판매점ID}.json`
- 통합 판매점 정보: `/lotto/lotto_stores.json`

## 데이터 구조

### 회차 정보 (draws/lotto_{회차번호}.json)
```json
{
  "draw_no": 1162,
  "draw_date": "2025-03-08",
  "numbers": [20, 21, 22, 25, 28, 29],
  "bonus_number": 6,
  "prize_info": [
    {
      "rank": "1등",
      "total_prize": "29,661,516,756원",
      "winner_count": "36",
      "prize_per_winner": "823,931,021원"
    }
  ],
  "total_sales_amount": "123,230,590,000원",
  "first_prize_store_info": [
    {
      "store_id": "11110012",
      "type": "자동"
    }
  ],
  "updated_at": "2025-03-10T17:32:57.381106"
}
```

### 판매점 정보 (stores/{판매점ID}.json)
```json
{
  "store_id": "11110012",
  "name": "신일",
  "address": "서울 강서구 까치산로 177 1층 101호"
}
```

### 인덱스 파일 (index.json)
```json
{
  "draws": [
    {
      "draw_no": 1162,
      "draw_date": "2025-03-08",
      "file": "draws/lotto_1162.json"
    },
    {
      "draw_no": 1161,
      "draw_date": "2025-03-01",
      "file": "draws/lotto_1161.json"
    }
  ],
  "last_updated": "2025-03-10T17:32:57.390631"
}
```

## 기술 스택

- **언어**: Python 3.9+
- **데이터 저장 형식**: JSON
- **웹 크롤링**: BeautifulSoup4, Requests
- **자동화**: GitHub Actions
- **배포 및 호스팅**: GitHub Pages
- **프론트엔드**: HTML, CSS, JavaScript, Bootstrap 5, Chart.js, Highcharts

## 설치 및 실행 방법

```bash
# 저장소 클론
git clone https://github.com/lottoclip/lottoclip-api.git
cd lottoclip-api

# 필요한 패키지 설치
pip install -r requirements.txt

# 최신 로또 데이터 수집
python src/crawler.py

# 연금복권 데이터 수집
python src/pension_crawler.py

# 통계 분석 실행
python src/analyze_statistics.py

# 판매점 정보 업데이트 (필요시)
python src/update_stores.py
```

## 데이터 정렬 방식

모든 회차 목록은 회차 번호(`draw_no`) 기준으로 내림차순 정렬되어 있어 최신 회차가 항상 배열의 첫 번째 요소로 제공됩니다. 이를 통해 클라이언트에서 최신 데이터에 쉽게 접근할 수 있습니다.

## 업데이트 내역

- 2025-03-15: 데이터 정렬 방식 변경 (모든 회차 목록을 draw_no 기준 내림차순 정렬)
- 2025-03-10: 데이터 구조 변경 (날짜 형식 변경, 판매점 정보에 구매 방식 추가)
- 2025-03-01: 프로젝트 초기 버전 릴리스

## 라이센스

이 프로젝트는 MIT 라이센스 하에 배포됩니다. 