import unittest
from unittest.mock import MagicMock
import json
import logging
from src.pension_crawler import PensionCrawler

# Test data driven by user artifacts
MOCK_INTRO_RESPONSE = {
  "resultCode": None,
  "resultMessage": None,
  "data": {
    "pstEpsd": [
      {
        "psltEpsd": 296,
        "psltRflYmd": "2026.01.01",
        "wnRnkVl": "667975",
        "wnBndNo": "1",
        "wnSqNo": 1
      },
      {
        "psltEpsd": 296,
        "psltRflYmd": "2026.01.01",
        "wnRnkVl": "988431",
        "wnBndNo": None,
        "wnSqNo": 21
      }
    ],
    "thsEpsd": {
      "ltEpsd": 297,
      "epsdRflDt": "2026-01-08T17:00:00"
    }
  }
}

MOCK_STATS_RESPONSE = {
    "resultCode": None,
    "resultMessage": None,
    "data": {
        "result": [
            {
                "ltEpsd": 296,
                "wnRnk": 1,
                "wnTotalCnt": 1,
                "wnAmt": 0
            },
            {
                "ltEpsd": 296,
                "wnRnk": 8,
                "wnTotalCnt": 5,
                "wnAmt": 0
            }
        ]
    }
}

MOCK_STORE_RESPONSE = {
    "resultCode": None,
    "resultMessage": None,
    "data": {
        "list": [
            {
                "ltShpId": "74561503",
                "shpNm": "해바라기 복권",
                "shpAddr": "전북 군산시  축동안길 42-1 (수송동, 신협)  1층104호(수송동)",
                "wnShpRnk": "1",
                "atmtPsvYnTxt": "자동"
            },
            {
                "ltShpId": "72761684",
                "shpNm": "현풍로또명당",
                "shpAddr": "대구 달성군 현풍읍",
                "wnShpRnk": "21"
            }
        ]
    }
}

class TestPensionCrawler(unittest.TestCase):
    def setUp(self):
        self.crawler = PensionCrawler()
        self.crawler.session = MagicMock()
        logging.disable(logging.CRITICAL)

    def test_get_latest_draw_number(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = MOCK_INTRO_RESPONSE
        self.crawler.session.get.return_value = mock_resp

        draw_no = self.crawler.get_latest_draw_number()
        # pstEpsd[0].psltEpsd = 296
        self.assertEqual(draw_no, 296)

    def test_crawl_draw(self):
        def side_effect(url, params=None, headers=None, data=None):
            mock_resp = MagicMock()
            if "selectPt720Intro.do" in url:
                mock_resp.json.return_value = MOCK_INTRO_RESPONSE
            elif "selectPstPt720WnInfo.do" in url:
                mock_resp.json.return_value = MOCK_STATS_RESPONSE
            return mock_resp

        self.crawler.session.get.side_effect = side_effect
        
        result = self.crawler.crawl_draw(296)
        
        self.assertIsNotNone(result)
        self.assertEqual(result['draw_no'], 296)
        self.assertEqual(result['draw_date'], "2026-01-01")
        # Rank 1: Group 1, Num 667975
        self.assertEqual(result['group'], "1")
        self.assertEqual(result['numbers'], ['6', '6', '7', '9', '7', '5'])
        
        # Bonus: Num 988431
        self.assertEqual(result['bonus_numbers'], ['9', '8', '8', '4', '3', '1'])
        
        # Prize Info
        # Rank 1, Rank 8 (Bonus)
        prize_info = result['prize_info']
        self.assertEqual(len(prize_info), 2)
        self.assertEqual(prize_info[0]['rank'], "1등")
        self.assertEqual(prize_info[1]['rank'], "보너스")

    def test_get_store_info(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = MOCK_STORE_RESPONSE
        self.crawler.session.get.return_value = mock_resp
        
        stores = self.crawler.get_store_info(296)
        
        # 1st Prize
        self.assertEqual(len(stores['first_prize_store_info']), 1)
        self.assertEqual(stores['first_prize_store_info'][0]['name'], "해바라기 복권")
        self.assertEqual(stores['first_prize_store_info'][0]['type'], "자동") # Check mapping
        
        # Bonus (Rank 21)
        self.assertEqual(len(stores['bonus_prize_store_info']), 1)
        self.assertEqual(stores['bonus_prize_store_info'][0]['name'], "현풍로또명당")

if __name__ == '__main__':
    unittest.main()
