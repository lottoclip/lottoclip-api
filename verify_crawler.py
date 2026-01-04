
import unittest
from unittest.mock import MagicMock
import json
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.getcwd(), 'src'))

from crawler import LottoCrawler

class TestLottoCrawler(unittest.TestCase):
    def setUp(self):
        self.crawler = LottoCrawler()
        self.crawler.session = MagicMock()
        
        # Mock Data
        self.latest_draw_response = {
            "resultCode": None,
            "resultMessage": None,
            "data": {
                "list": [
                     {
                        "ltEpsd": 1200,
                        "ltRflYmd": "20251129"
                     }
                ]
            }
        }
        
        self.draw_detail_response = {
            "resultCode": None,
            "resultMessage": None,
            "data": {
                "list": [
                  {
                    "winType0": 0,
                    "winType1": 10,
                    "winType2": 2,
                    "winType3": 0,
                    "gmSqNo": 5133,
                    "ltEpsd": 1200,
                    "tm1WnNo": 1,
                    "tm2WnNo": 2,
                    "tm3WnNo": 4,
                    "tm4WnNo": 16,
                    "tm5WnNo": 20,
                    "tm6WnNo": 32,
                    "bnsWnNo": 45,
                    "ltRflYmd": "20251129",
                    "rnk1WnNope": 12,
                    "rnk1WnAmt": 2357299875,
                    "rnk1SumWnAmt": 28287598500,
                    "rnk2WnNope": 80,
                    "rnk2WnAmt": 58932497,
                    "rnk2SumWnAmt": 4714599760,
                    "rnk3WnNope": 3584,
                    "rnk3WnAmt": 1315458,
                    "rnk3SumWnAmt": 4714601472,
                    "rnk4WnNope": 161754,
                    "rnk4WnAmt": 50000,
                    "rnk4SumWnAmt": 8087700000,
                    "rnk5WnNope": 2673060,
                    "rnk5WnAmt": 5000,
                    "rnk5SumWnAmt": 13365300000,
                    "sumWnNope": 2838490,
                    "rlvtEpsdSumNtslAmt": 59169798000,
                    "wholEpsdSumNtslAmt": 118339596000,
                    "excelRnk": "1등"
                  }
                ]
            }
        }
        
        self.store_response = {
            "resultCode": None,
            "resultMessage": None,
            "data": {
                "total": 92,
                "list": [
                  {
                    "rnum": 92,
                    "shpNm": "천하명당복권방독산점",
                    "shpTelno": "02-863-8121",
                    "region": "서울",
                    "shpAddr": "서울 금천구 독산로85길 16 독산로85길 16",
                    "ltShpId": "11100247",
                    "l645LtNtslYn": "Y",
                    "st5LtNtslYn": "Y",
                    "st10LtNtslYn": "Y",
                    "st20LtNtslYn": "Y",
                    "pt720NtslYn": "Y",
                    "wnShpRnk": 2, # 2등이라 무시되어야 함 in 1st prize logic? No, wait. logic filters wnShpRnk == 1
                    "shpLat": 37.472535,
                    "shpLot": 126.902207
                  },
                  {
                    "rnum": 90,
                    "shpNm": "살맛나는 세상",
                    "shpTelno": "02-2214-3463",
                    "region": "서울",
                    "shpAddr": "서울 동대문구 한천로46길 56-4 한천로46길 56-4",
                    "ltShpId": "11110635",
                    "l645LtNtslYn": "Y",
                    "wnShpRnk": 1, 
                    "atmtPsvYnTxt": "자동",
                    "shpLat": 37.581578,
                    "shpLot": 127.071366
                  }
                ]
            }
        }

    def test_get_latest_draw_number(self):
        # Update mock response to have multiple items, simulating ascending order (1, 2, ..., 1200)
        multi_draw_response = {
            "resultCode": None,
            "resultMessage": None,
            "data": {
                "list": [
                     { "ltEpsd": 1, "ltRflYmd": "20021207" },
                     { "ltEpsd": 1200, "ltRflYmd": "20251129" }
                ]
            }
        }
        
        mock_resp = MagicMock()
        mock_resp.json.return_value = multi_draw_response
        self.crawler.session.get.return_value = mock_resp

        draw_no = self.crawler.get_latest_draw_number()
        # Should pick max (1200), not first (1)
        self.assertEqual(draw_no, 1200)

    def test_crawl_draw(self):
        # Setup mocks for draw and store calls
        def side_effect(url, params=None, headers=None, data=None):
            mock_resp = MagicMock()
            if "selectPstLt645Info" in url:
                mock_resp.json.return_value = self.draw_detail_response
            elif "selectLtWnShp" in url:
                mock_resp.json.return_value = self.store_response
            return mock_resp

        self.crawler.session.get.side_effect = side_effect
        
        # Test
        result = self.crawler.crawl_draw(1200)
        
        self.assertIsNotNone(result)
        self.assertEqual(result['draw_no'], 1200)
        self.assertEqual(result['draw_date'], "2025-11-29")
        self.assertEqual(result['numbers'], [1, 2, 4, 16, 20, 32])
        self.assertEqual(result['bonus_number'], 45)
        self.assertEqual(result['total_sales_amount'], "118339596000")
        
        # Verify prize info
        self.assertEqual(len(result['prize_info']), 5)
        self.assertEqual(result['prize_info'][0]['winner_count'], "12")
        self.assertEqual(result['prize_info'][0]['total_prize'], "28287598500")

        # Verify store info (only rank 1 should be included)
        stores = result['first_prize_store_info']
        self.assertEqual(len(stores), 1)
        self.assertEqual(stores[0]['type'], '자동') # Verify mapped from atmtPsvYnTxt
        self.assertEqual(stores[0]['store_id'], "11110635")

if __name__ == '__main__':
    unittest.main()
