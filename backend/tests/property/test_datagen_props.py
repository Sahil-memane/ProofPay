"""Hypothesis property tests for datagen."""
from hypothesis import given, settings, strategies as st
from backend.app.simulator.datagen.generator import generate_dataset


@given(
    n=st.integers(min_value=1, max_value=50),
    rate=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
    seed=st.integers(min_value=0, max_value=9999),
)
@settings(max_examples=30)
def test_datagen_count_invariant(n, rate, seed):
    invs, pays = generate_dataset(n_cases=n, anomaly_rate=rate, seed=seed)
    assert len(invs) == n
    assert len(pays) >= n  # duplicates may add extras


@given(seed=st.integers(min_value=0, max_value=9999))
@settings(max_examples=20)
def test_public_dict_never_leaks_raw_customer_id(seed):
    invs, _ = generate_dataset(n_cases=10, seed=seed)
    for inv in invs:
        pub = inv.to_public_dict()
        assert inv.customer_id not in pub.values()
