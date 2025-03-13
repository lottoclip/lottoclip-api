const fs = require('fs');

// 로또 파일 정렬
const lottoPath = 'lotto/index.json';
const lottoData = JSON.parse(fs.readFileSync(lottoPath, 'utf8'));

// 중복 제거 (draw_no 기준)
const uniqueDraws = [];
const drawNoSet = new Set();

for (const draw of lottoData.draws) {
  if (!drawNoSet.has(draw.draw_no)) {
    drawNoSet.add(draw.draw_no);
    uniqueDraws.push(draw);
  }
}

// draw_no 기준으로 내림차순 정렬
uniqueDraws.sort((a, b) => b.draw_no - a.draw_no);

// 중복 제거된 배열로 교체
lottoData.draws = uniqueDraws;

// 파일 저장
fs.writeFileSync(lottoPath, JSON.stringify(lottoData, null, 2), 'utf8');
console.log('로또 데이터가 중복 제거 후 내림차순으로 정렬되었습니다.');

// 연금복권 파일 정렬
const pensionPath = 'pension/index.json';
const pensionData = JSON.parse(fs.readFileSync(pensionPath, 'utf8'));

// 중복 제거 (draw_no 기준)
const uniquePensionDraws = [];
const pensionDrawNoSet = new Set();

for (const draw of pensionData.draws) {
  if (!pensionDrawNoSet.has(draw.draw_no)) {
    pensionDrawNoSet.add(draw.draw_no);
    uniquePensionDraws.push(draw);
  }
}

// draw_no 기준으로 내림차순 정렬
uniquePensionDraws.sort((a, b) => b.draw_no - a.draw_no);

// 중복 제거된 배열로 교체
pensionData.draws = uniquePensionDraws;

// 파일 저장
fs.writeFileSync(pensionPath, JSON.stringify(pensionData, null, 2), 'utf8');
console.log('연금복권 데이터가 중복 제거 후 내림차순으로 정렬되었습니다.'); 