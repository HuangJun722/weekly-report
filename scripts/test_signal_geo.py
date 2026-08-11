"""Tests for signal_geo country tagging (Signal = event + country dimension)."""

import json
import os
import sys
import unittest

try:
    from signal_geo import (
        company_to_countries, entity_country_map, tag_event_country,
    )
except ImportError:
    from scripts.signal_geo import (
        company_to_countries, entity_country_map, tag_event_country,
    )

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load_pool():
    with open(os.path.join(REPO_ROOT, 'data', 'entity_pool.json'), encoding='utf-8') as f:
        return json.load(f)


class TestEntityCountryMap(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pool = _load_pool()
        cls.map = entity_country_map(cls.pool)

    def test_all_entities_have_geo(self):
        for e in self.pool['entities']:
            info = self.map.get(e['id'])
            self.assertIsNotNone(info, f'no geo for {e["id"]}')
            self.assertTrue(info['hq'], f'empty hq for {e["id"]}')
            self.assertTrue(info['markets'], f'empty markets for {e["id"]}')

    def test_tier1_countries_present(self):
        # Tier 1 八国都应有至少一个对象落地
        tier1 = {'印尼', '越南', '日本', '韩国', '沙特', '阿联酋', '巴西', '墨西哥'}
        hq_set = {info['hq'] for info in self.map.values()}
        markets_set = set()
        for info in self.map.values():
            markets_set.update(info['markets'])
        for c in tier1:
            self.assertIn(c, hq_set | markets_set, f'Tier1 {c} 无对象落地')


class TestTagEvent(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pool = _load_pool()
        cls.map = entity_country_map(cls.pool)

    def test_company_market_wins(self):
        ev = {'title': 'Kakao Pay Q2 revenue rises', 'company_name': 'Kakao'}
        tag = tag_event_country(ev, entity_map=self.map)
        self.assertEqual(tag['tag_method'], 'company_market')
        self.assertIn('韩国', tag['countries'])

    def test_no_company_uses_title(self):
        ev = {'title': 'Google in India embeds AI into Google Pay'}
        tag = tag_event_country(ev, entity_map=self.map)
        self.assertEqual(tag['tag_method'], 'title_keyword')
        self.assertIn('印度', tag['countries'])

    def test_unknown_returns_empty(self):
        ev = {'title': 'Global AI model release', 'company_name': ''}
        tag = tag_event_country(ev, entity_map=self.map)
        self.assertEqual(tag['tag_method'], '')
        self.assertEqual(tag['primary_country'], '')

    def test_markets_resolution(self):
        countries = company_to_countries(self.map, 'Naver')
        self.assertIn('韩国', countries)

    def test_changelog_company(self):
        ev = {'title': 'Cloudflare: WAF Release', 'company_name': 'Cloudflare'}
        tag = tag_event_country(ev, entity_map=self.map)
        self.assertEqual(tag['primary_country'], '美国')


if __name__ == '__main__':
    unittest.main()
