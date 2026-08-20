from otklik_backend.secrets.store import account_for, context_source_account_for


def test_context_source_account_for_is_deterministic_and_distinct() -> None:
    assert context_source_account_for(7) == "context_source.7"
    assert context_source_account_for(7) == context_source_account_for(7)
    assert context_source_account_for(7) != context_source_account_for(8)
    assert context_source_account_for(7) != account_for("7")
