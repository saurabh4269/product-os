from __future__ import annotations


def test_ads_join_constrains_data_date(engine):
    spend = engine.wh.ads_spend_by_date()
    assert spend
    # Unconstrained join would multiply ~35 days of dimension snapshots.
    assert all(200 < v < 2000 for v in spend.values())
