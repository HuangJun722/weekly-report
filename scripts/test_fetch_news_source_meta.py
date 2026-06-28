import fetch_news

from fetch_news import (
    _extract_official_article_date,
    _registry_source_to_cfg,
    _select_changelog_items,
    _title_mentions_aliases,
    _with_source_meta,
    _get_company_aliases,
)


def test_official_company_title_gets_entity_prefix():
    item = _with_source_meta(
        {
            'title': 'Financial Results for Fiscal Year Ended March 31, 2026',
            'url': 'https://example.com/square-enix',
            'source': 'Square Enix',
            'region': '亚太',
            'event_types': ['earnings'],
            'is_company': True,
            'company_name': 'Square Enix',
        },
        {
            'name': 'Square Enix IR News',
            'source_tier': 'L1 官方/IR源',
            'source_role': 'official_ir',
        },
    )
    assert item['title'].startswith('Square Enix: ')
    assert _title_mentions_aliases(item['title'], _get_company_aliases('Square Enix'))


def test_l1_changelog_infers_entity_name_without_changelog_suffix():
    cfg = _registry_source_to_cfg({
        'id': 'stripe-changelog',
        'name': 'Stripe Changelog',
        'url': 'https://stripe.com/changelog',
        'tier': 'L1',
        'source_type': 'changelog',
        'access_method': 'html',
        'region': '全球',
    })
    assert cfg['company_name'] == 'Stripe'
    assert cfg['is_company'] is True


def test_official_article_date_extracted_from_title_and_url():
    assert _extract_official_article_date(
        'Square Enix: May 14, 2026 Results Briefing Session',
        'https://www.hd.square-enix.com/eng/ir/pdf/26q4slides.pdf',
    ) == '2026-05-14'
    assert _extract_official_article_date(
        'Notice of Revisions to Full-Year Consolidated Financial Forecasts',
        'https://www.hd.square-enix.com/eng/ir/pdf/20260205_02_en.pdf',
    ) == '2026-02-05'


def test_official_html_skips_stale_ir_items():
    old_fetch_url = fetch_news.fetch_url
    try:
        fetch_news.fetch_url = lambda url: """
        <html><body>
          <a href="/eng/ir/pdf/26q4slides.pdf">
            May 14, 2026 Results Briefing Session for the Fiscal Year ended March 31, 2026
          </a>
        </body></html>
        """
        items = fetch_news.fetch_html({
            'name': 'Square Enix IR News',
            'url': 'https://www.hd.square-enix.com/eng/ir/irnews/',
            'source': 'Square Enix',
            'region': '亚太',
            'priority': 3,
            'source_tier': 'L1 官方/IR源',
            'source_role': 'official_ir',
            'company_name': 'Square Enix',
            'is_company': True,
            'max': 4,
        })
    finally:
        fetch_news.fetch_url = old_fetch_url

    assert items == []


def test_changelog_items_extract_direct_dated_links():
    soup = fetch_news.BeautifulSoup(
        """
        <html><body>
          <nav><a href="/pricing">Pricing</a></nav>
          <article>
            <time>June 28, 2026</time>
            <a href="/posts/custom-draft-order-discounts">
              Custom draft order line item discounts now use presentment currency
            </a>
          </article>
          <article>
            <time>June 10, 2025</time>
            <a href="/posts/old-api-update">Old API update</a>
          </article>
        </body></html>
        """,
        'html.parser',
    )
    cfg = _registry_source_to_cfg({
        'id': 'shopify-changelog',
        'name': 'Shopify Changelog',
        'url': 'https://changelog.shopify.com/',
        'tier': 'L1',
        'source_type': 'changelog',
        'access_method': 'html',
        'region': '全球',
        'priority': 3,
    })
    items = _select_changelog_items(soup, cfg)
    assert len(items) == 1
    assert items[0]['company_name'] == 'Shopify'
    assert items[0]['article_date'] == '2026-06-28'
    assert items[0]['event_types'] == ['strategy']
    assert 'developer_change' in items[0]['signal_taxonomy']


if __name__ == '__main__':
    test_official_company_title_gets_entity_prefix()
    test_l1_changelog_infers_entity_name_without_changelog_suffix()
    test_official_article_date_extracted_from_title_and_url()
    test_official_html_skips_stale_ir_items()
    test_changelog_items_extract_direct_dated_links()
    print('fetch news source meta tests passed')
