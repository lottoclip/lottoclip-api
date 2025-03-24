# 로또클립 API (LottoClip API)

로또클립 API는 대한민국의 로또 6/45와 연금복권720+ 당첨 데이터를 자동으로 수집하고, 이를 분석하여 JSON 형식의 API로 제공하는 서비스입니다.

## 주요 기능

- 로또 6/45 및 연금복권720+ 당첨번호 자동 수집
- 판매점 정보(상호명, 주소, 전화번호, 취급복권 유형) 수집
- 번호별 출현 빈도, 홀짝 비율, 구간별 분포 등 다양한 통계 데이터 제공
- 연속번호, 번호 간 간격, 휴면기간 분석
- 자동/수동 당첨 비율, 지역별 당첨 통계
- GitHub Actions를 통한 주기적 자동 데이터 업데이트 (로또: 매주 토요일, 연금복권: 매주 목요일)
- 모든 데이터는 회차 번호(`draw_no`) 기준 내림차순 정렬

## 데이터 API 엔드포인트

### 로또 6/45

- **전체 회차 목록**: `/lotto/index.json`
- **특정 회차 상세 정보**: `/lotto/draws/lotto_{회차번호}.json`
- **통계 분석 데이터**: `/lotto/statistics.json`
- **판매점 상세 정보**: `/lotto/stores/{판매점ID}.json`
- **통합 판매점 정보**: `/lotto/lotto_stores.json`

### 연금복권720+

- **전체 회차 목록**: `/pension/index.json`
- **특정 회차 상세 정보**: `/pension/draws/pension_{회차번호}.json`
- **특정 회차 판매점 정보**: `/pension/stores/stores_{회차번호}.json`
- **통계 분석 데이터**: `/pension/statistics.json`

## 데이터 구조

### 로또 회차 정보 (`/lotto/draws/lotto_{회차번호}.json`)

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
    },
    ...
  ],
  "total_sales_amount": "123,230,590,000원",
  "first_prize_store_info": [
    {
      "store_id": "11110012",
      "type": "자동"
    },
    ...
  ],
  "updated_at": "2025-03-10T17:32:57.381106"
}
```

### 로또 판매점 정보 (`/lotto/stores/{판매점ID}.json`)

```json
{
  "store_id": "11110012",
  "name": "신일",
  "address": "서울 강서구 까치산로 177 1층 101호",
  "phone": "02-2618-3257",
  "lottery_types": [
    "lotto645"
  ]
}
```

### 로또 인덱스 파일 (`/lotto/index.json`)

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
    },
    ...
  ],
  "last_updated": "2025-03-10T17:32:57.390631"
}
```

### 연금복권 회차 정보 (`/pension/draws/pension_{회차번호}.json`)

```json
{
  "draw_no": 253,
  "draw_date": "2025-03-06",
  "group": "4",
  "numbers": ["4", "8", "4", "0", "1", "0"],
  "bonus_group": "각",
  "bonus_numbers": ["9", "2", "1", "0", "6", "9"],
  "prize_info": [
    {
      "rank": "1",
      "winner_count": "1"
    },
    ...
  ],
  "updated_at": "2025-03-12T14:06:50.793067"
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

# 로또 데이터 수집
python src/crawler.py --latest  # 최신 회차만 수집
python src/crawler.py --draw 1162  # 특정 회차 수집
python src/crawler.py --range 1150-1162  # 범위 수집
python src/crawler.py --all  # 전체 회차 수집

# 연금복권 데이터 수집
python src/pension_crawler.py --latest  # 최신 회차만 수집
python src/pension_crawler.py --draw 253  # 특정 회차 수집
python src/pension_crawler.py --range 245-253  # 범위 수집
python src/pension_crawler.py --all  # 전체 회차 수집

# 통계 분석 실행
python src/analyze_statistics.py

# 판매점 정보 업데이트
python src/update_stores.py --store-id 11110012  # 특정 판매점 정보 업데이트
python src/update_stores.py --update-all  # 모든 판매점 정보 업데이트
python src/update_stores.py --limit 100  # 일부 판매점 정보 업데이트
```

## 데이터 정렬 방식

모든 회차 목록은 회차 번호(`draw_no`) 기준으로 내림차순 정렬되어 있어 최신 회차가 항상 배열의 첫 번째 요소로 제공됩니다. 이를 통해 클라이언트에서 최신 데이터에 쉽게 접근할 수 있습니다.

```javascript
// 최신 회차 정보 가져오기 예시
fetch('lotto/index.json')
  .then(response => response.json())
  .then(data => {
    // 항상 첫 번째 요소가 최신 회차
    const latestDraw = data.draws[0];
    console.log(`최신 회차: ${latestDraw.draw_no}, 날짜: ${latestDraw.draw_date}`);
  });
```

## 데이터 업데이트 주기

- **로또 6/45**: 매주 토요일 추첨 후 22:00, 23:00에 자동으로 업데이트 (GitHub Actions)
- **연금복권720+**: 매주 목요일 추첨 후 22:00, 23:00에 자동으로 업데이트 (GitHub Actions)

## 판매점 상세 정보 제공

판매점 정보는 다음과 같은 상세 정보를 포함합니다:
- 판매점 ID
- 판매점명
- 주소
- 전화번호
- 취급복권 유형 (lotto645, pension720, speetto 등)

## 로컬 개발 환경에서 API 서버 실행

간단한 HTTP 서버를 통해 로컬에서 API를 테스트할 수 있습니다:

```bash
# Python 내장 HTTP 서버 실행
python -m http.server

# 또는 Node.js를 사용하는 경우
npx http-server -p 8000
```

서버 실행 후 `http://localhost:8000`에서 API에 접근할 수 있습니다.

## 업데이트 내역

- **2025-03-20**: 판매점 정보에 전화번호 및 취급복권 유형 추가
- **2025-03-15**: 데이터 정렬 방식 변경 (모든 회차 목록을 draw_no 기준 내림차순 정렬)
- **2025-03-10**: 데이터 구조 변경 (날짜 형식 변경, 판매점 정보에 구매 방식 추가)
- **2025-03-01**: 프로젝트 초기 버전 릴리스

## 라이센스

이 프로젝트는 MIT 라이센스 하에 배포됩니다.

## 문의 및 기여

프로젝트에 대한 문의나 기여는 GitHub 이슈를 통해 진행해주세요. 