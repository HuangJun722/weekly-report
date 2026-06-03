from evidence_atoms import build_evidence_atoms, can_promote_to_narrative, evidence_independence


def event(**overrides):
    base = {
        'title': 'African healthtech startup raises funding',
        'url': 'https://example.com/a',
        'source': 'Ventureburn',
        'source_tier': 'L2 垂直交易源',
        'event_types': ['funding'],
        'region': '非洲',
        'trend_topic': '非洲医疗科技融资',
        'company_name': 'HealthCo',
        'date': '2026-06-02',
    }
    base.update(overrides)
    return base


def test_similar_events_collapse_into_one_atom():
    atoms = build_evidence_atoms([
        event(url='https://example.com/a', company_name='HealthCo'),
        event(url='https://example.com/b', company_name='BioCo'),
    ])
    assert len(atoms) == 1
    assert not can_promote_to_narrative(atoms)


def test_independent_evidence_can_promote():
    atoms = build_evidence_atoms([
        event(
            url='https://example.com/a',
            source='TechCrunch',
            source_tier='L2 垂直交易源',
            company_name='Careem',
            region='中东',
            trend_topic='中东出行平台整合',
            event_types=['ma'],
        ),
        event(
            url='https://example.com/b',
            source='Careem Press',
            source_tier='L1 官方/IR源',
            company_name='Careem',
            region='中东',
            trend_topic='中东出行平台整合',
            event_types=['partnership'],
        ),
    ])
    stats = evidence_independence(atoms)
    assert stats['atom_count'] == 2
    assert stats['source_family_count'] == 2
    assert can_promote_to_narrative(atoms)


if __name__ == '__main__':
    test_similar_events_collapse_into_one_atom()
    test_independent_evidence_can_promote()
    print('evidence atom tests passed')
