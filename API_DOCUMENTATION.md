# 로또클립 API 문서

이 문서는 로또클립에서 제공하는 API 목록과 사용 예제를 설명합니다.

## 기본 정보

- 기본 URL: `https://api.lottoclip.com`
- 모든 응답은 JSON 형식으로 제공됩니다.
- 데이터는 매주 자동으로 업데이트됩니다.
- 모든 회차 목록은 회차 번호(`draw_no`) 기준으로 내림차순 정렬되어 제공됩니다.

## 로또 6/45 API

### 1. 전체 회차 목록

**엔드포인트:** `GET /lotto/index.json`

**설명:** 모든 로또 회차의 목록을 제공합니다. 회차 번호(`draw_no`) 기준으로 내림차순 정렬되어 있어 최신 회차가 항상 배열의 첫 번째 요소로 제공됩니다.

**응답 예시:**
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

### 2. 특정 회차 상세 정보

**엔드포인트:** `GET /lotto/draws/lotto_{회차번호}.json`

**설명:** 특정 회차의 당첨 번호 및 1등 판매점 정보를 제공합니다.

**응답 예시:**
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
    {
      "rank": "2등",
      "total_prize": "4,943,586,126원",
      "winner_count": "60",
      "prize_per_winner": "82,393,102원"
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

### 3. 통계 분석 데이터

**엔드포인트:** `GET /lotto/statistics.json`

**설명:** 번호별 출현 빈도, 패턴 분석, 판매점 통계 등 다양한 통계 정보를 제공합니다.

**응답 예시:**
```json
{
  "total_draws": 1162,
  "first_draw": 1,
  "last_draw": 1162,
  "frequency_stats": {
    "most_frequent_numbers": [
      {"number": 34, "count": 200, "percentage": 17.21},
      {"number": 18, "count": 198, "percentage": 17.04}
    ],
    "least_frequent_numbers": [
      {"number": 44, "count": 150, "percentage": 12.91},
      {"number": 11, "count": 152, "percentage": 13.08}
    ]
  },
  "pattern_stats": {
    "odd_even_distribution": [
      {"pattern": "3:3", "count": 450, "percentage": 38.73},
      {"pattern": "4:2", "count": 350, "percentage": 30.12}
    ]
  },
  "store_stats": {
    "region_stats": [
      {"region": "서울", "count": 250, "percentage": 21.51},
      {"region": "경기", "count": 220, "percentage": 18.93}
    ],
    "top_stores": [
      {"store_id": "23450789", "name": "행운복권방", "count": 5},
      {"store_id": "12345678", "name": "로또명당", "count": 4}
    ]
  },
  "updated_at": "2025-03-10T17:32:57.714575"
}
```

### 4. 판매점 정보

**엔드포인트:** `GET /lotto/stores/{판매점ID}.json`

**설명:** 특정 판매점의 상세 정보를 제공합니다.

**응답 예시:**
```json
{
  "store_id": "11110012",
  "name": "신일",
  "address": "서울 강서구 까치산로 177 1층 101호"
}
```

### 5. 통합 판매점 정보

**엔드포인트:** `GET /lotto/lotto_stores.json`

**설명:** 모든 판매점의 정보를 제공합니다.

**응답 예시:**
```json
{
  "11110012": {
    "store_id": "11110012",
    "name": "신일",
    "address": "서울 강서구 까치산로 177 1층 101호"
  },
  "22220034": {
    "store_id": "22220034",
    "name": "로또명당",
    "address": "경기도 수원시 영통구 매탄동 1234-5"
  }
}
```

## 연금복권 720+ API

### 1. 전체 회차 목록

**엔드포인트:** `GET /pension/index.json`

**설명:** 모든 연금복권 회차의 목록을 제공합니다. 회차 번호(`draw_no`) 기준으로 내림차순 정렬되어 있어 최신 회차가 항상 배열의 첫 번째 요소로 제공됩니다.

**응답 예시:**
```json
{
  "draws": [
    {
      "draw_no": 253,
      "draw_date": "2025-03-06",
      "file": "draws/pension_253.json"
    },
    {
      "draw_no": 252,
      "draw_date": "2025-02-27",
      "file": "draws/pension_252.json"
    }
  ],
  "last_updated": "2025-03-12T14:06:50.793067"
}
```

### 2. 특정 회차 상세 정보

**엔드포인트:** `GET /pension/draws/pension_{회차번호}.json`

**설명:** 특정 회차의 당첨 번호 정보를 제공합니다.

**응답 예시:**
```json
{
  "draw_no": 253,
  "draw_date": "2025-03-06",
  "group": "4",
  "numbers": [
    "4",
    "8",
    "4",
    "0",
    "1",
    "0"
  ],
  "bonus_group": "각",
  "bonus_numbers": [
    "9",
    "2",
    "1",
    "0",
    "6",
    "9"
  ],
  "prize_info": [
    {
      "rank": "1",
      "winner_count": "1"
    },
    {
      "rank": "2",
      "winner_count": "4"
    },
    {
      "rank": "3",
      "winner_count": "40"
    },
    {
      "rank": "4",
      "winner_count": "400"
    },
    {
      "rank": "5",
      "winner_count": "4000"
    },
    {
      "rank": "6",
      "winner_count": "40000"
    },
    {
      "rank": "7",
      "winner_count": "400000"
    },
    {
      "rank": "보너스",
      "winner_count": "40"
    }
  ],
  "updated_at": "2025-03-12T14:06:50.793067"
}
```

### 3. 판매점 정보

**엔드포인트:** `GET /pension/stores/stores_{회차번호}.json`

**설명:** 특정 회차의 1등, 2등, 보너스 당첨 판매점 정보를 제공합니다.

**응답 예시:**
```json
{
  "first_prize_store_info": [
    {
      "name": "행운의집로또",
      "address": "충남 아산시 배방읍 북수북길 7-4 1층 101,102호"
    }
  ],
  "second_prize_store_info": [
    {
      "name": "행운의집로또",
      "address": "충남 아산시 배방읍 북수북길 7-4 1층 101,102호"
    },
    {
      "name": "GS25 수원영통점",
      "address": "경기 수원시 영통구 영통로 195"
    }
  ],
  "bonus_prize_store_info": [
    {
      "name": "인생여섯컷",
      "address": "경기 수원시 권선구 정조로384번길 2 (세류동) 1층"
    }
  ]
}
```

### 4. 통계 분석 데이터

**엔드포인트:** `GET /pension/statistics.json`

**설명:** 번호별 출현 빈도, 등수별 당첨자 수, 판매점 통계 등 다양한 통계 정보를 제공합니다.

**응답 예시:**
```json
{
  "total_draws": 253,
  "first_draw": 1,
  "last_draw": 253,
  "frequency_stats": {
    "group_frequency": [
      {"group": "1", "count": 25, "percentage": 9.88},
      {"group": "2", "count": 26, "percentage": 10.28}
    ],
    "position_frequency": [
      {
        "position": 0,
        "numbers": [
          {"number": "0", "count": 25, "percentage": 9.88},
          {"number": "1", "count": 26, "percentage": 10.28}
        ]
      }
    ],
    "bonus_frequency": [
      {"group": "가", "count": 25, "percentage": 9.88},
      {"group": "나", "count": 26, "percentage": 10.28}
    ]
  },
  "prize_stats": {
    "rank_stats": [
      {
        "rank": "1",
        "total_winners": 253,
        "avg_winners_per_draw": 1.0
      },
      {
        "rank": "2",
        "total_winners": 1012,
        "avg_winners_per_draw": 4.0
      }
    ]
  },
  "store_stats": {
    "region_stats": [
      {"region": "서울", "count": 50, "percentage": 19.76},
      {"region": "경기", "count": 45, "percentage": 17.79}
    ],
    "top_stores": [
      {"name": "행운의집로또", "address": "충남 아산시 배방읍 북수북길 7-4 1층 101,102호", "count": 3},
      {"name": "GS25 수원영통점", "address": "경기 수원시 영통구 영통로 195", "count": 2}
    ]
  },
  "updated_at": "2025-03-12T14:06:50.793067"
}
```

## 사용 예제

### JavaScript 예제

```javascript
// 최신 로또 회차 정보 가져오기
async function getLatestLottoDraw() {
  try {
    // 1. 인덱스 파일 가져오기
    const indexResponse = await fetch('https://api.lottoclip.com/lotto/index.json');
    const indexData = await indexResponse.json();
    
    // 2. 최신 회차 정보 추출 (내림차순 정렬되어 있으므로 첫 번째 항목이 최신)
    const latestDraw = indexData.draws[0];
    console.log(`최신 회차: ${latestDraw.draw_no}, 날짜: ${latestDraw.draw_date}`);
    
    // 3. 최신 회차 상세 정보 가져오기
    const drawResponse = await fetch(`https://api.lottoclip.com/lotto/${latestDraw.file}`);
    const drawData = await drawResponse.json();
    
    // 4. 당첨 번호 출력
    console.log('당첨 번호:', drawData.numbers.join(', '), '+', drawData.bonus_number);
    
    return drawData;
  } catch (error) {
    console.error('데이터 로드 실패:', error);
  }
}

// 연금복권 통계 데이터 가져오기
async function getPensionStatistics() {
  try {
    const response = await fetch('https://api.lottoclip.com/pension/statistics.json');
    const data = await response.json();
    
    // 그룹별 빈도 출력
    console.log('그룹별 빈도:');
    data.frequency_stats.group_frequency.forEach(item => {
      console.log(`그룹 ${item.group}: ${item.count}회 (${item.percentage}%)`);
    });
    
    return data;
  } catch (error) {
    console.error('통계 데이터 로드 실패:', error);
  }
}

// 특정 판매점 정보 가져오기
async function getStoreInfo(storeId) {
  try {
    const response = await fetch(`https://api.lottoclip.com/lotto/stores/${storeId}.json`);
    const data = await response.json();
    
    console.log(`판매점명: ${data.name}`);
    console.log(`주소: ${data.address}`);
    
    return data;
  } catch (error) {
    console.error('판매점 정보 로드 실패:', error);
  }
}
```

### React 컴포넌트 예제

```jsx
import React, { useState, useEffect } from 'react';

function LatestLottoNumbers() {
  const [latestDraw, setLatestDraw] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function fetchLatestDraw() {
      try {
        // 인덱스 파일 가져오기
        const indexResponse = await fetch('https://api.lottoclip.com/lotto/index.json');
        const indexData = await indexResponse.json();
        
        // 최신 회차 정보 가져오기 (내림차순 정렬되어 있으므로 첫 번째 항목이 최신)
        const latestDrawInfo = indexData.draws[0];
        const drawResponse = await fetch(`https://api.lottoclip.com/lotto/${latestDrawInfo.file}`);
        const drawData = await drawResponse.json();
        
        setLatestDraw(drawData);
        setLoading(false);
      } catch (err) {
        setError('데이터를 불러오는데 실패했습니다.');
        setLoading(false);
      }
    }

    fetchLatestDraw();
  }, []);

  if (loading) return <div>로딩 중...</div>;
  if (error) return <div>{error}</div>;
  if (!latestDraw) return <div>데이터가 없습니다.</div>;

  return (
    <div className="latest-lotto">
      <h2>{latestDraw.draw_no}회 당첨결과 ({latestDraw.draw_date})</h2>
      <div className="numbers">
        {latestDraw.numbers.map((num, index) => (
          <span key={index} className={`ball ball-${Math.ceil((num) / 10)}`}>
            {num}
          </span>
        ))}
        <span className="bonus">
          {latestDraw.bonus_number}
        </span>
      </div>
      <div className="prize-info">
        <p>1등 당첨금: {latestDraw.prize_info[0].prize_per_winner}</p>
        <p>1등 당첨자 수: {latestDraw.prize_info[0].winner_count}명</p>
      </div>
    </div>
  );
}

export default LatestLottoNumbers;
```

## 주의사항

1. API 호출 시 CORS 정책을 고려하여 적절한 설정이 필요할 수 있습니다.
2. 데이터는 매주 자동으로 업데이트되며, 업데이트 시간은 로또 추첨 후 약 1-2시간 이내입니다.
3. 대량의 API 호출은 서비스에 부하를 줄 수 있으므로, 적절한 캐싱 전략을 사용하는 것이 좋습니다.
4. 모든 회차 목록은 회차 번호(`draw_no`) 기준으로 내림차순 정렬되어 있어 최신 회차가 항상 배열의 첫 번째 요소로 제공됩니다. 