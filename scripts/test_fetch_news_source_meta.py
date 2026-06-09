from fetch_news import _registry_source_to_cfg, _title_mentions_aliases, _with_source_meta, _get_company_aliases


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


if __name__ == '__main__':
    test_official_company_title_gets_entity_prefix()
    test_l1_changelog_infers_entity_name_without_changelog_suffix()
    print('fetch news source meta tests passed')
