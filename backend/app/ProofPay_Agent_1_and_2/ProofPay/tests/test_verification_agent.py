from ProofPay.agents.verification_agent.nodes import verify_evidence, _public_http_url


def test_verification_routes_unverifiable_deliverable_to_client_review():
    state = {
        "milestone": {
            "acceptance_criteria": [
                {"id": "c1", "type": "deliverable_check", "weight": 0.8,
                 "must_pass": True, "params": {"deliverable": "Shopping cart", "acceptance_checks": ["Cart total updates"]}},
                {"id": "c2", "type": "manual_review", "weight": 0.2,
                 "must_pass": False, "params": {"checklist": ["UI looks clean"]}},
            ]
        },
        "submission": {},
    }
    result = verify_evidence(state)
    assert result["decision"] == "CLIENT_REVIEW_REQUIRED"
    assert result["verification_score"] == 0.0
    assert all(item["status"] == "review_required" for item in result["criterion_results"])


def test_verification_fails_must_pass_criterion_when_evidence_missing():
    state = {
        "milestone": {
            "acceptance_criteria": [
                {"id": "c1", "type": "url_returns_200", "weight": 1.0,
                 "must_pass": True, "params": {"url": ""}},
            ]
        },
        "submission": {},
    }
    result = verify_evidence(state)
    assert result["decision"] == "CLIENT_REVIEW_REQUIRED"
    assert result["criterion_results"][0]["status"] == "review_required"


def test_private_and_local_urls_are_rejected():
    assert not _public_http_url("http://127.0.0.1:8000")
    assert not _public_http_url("http://localhost/admin")
    assert not _public_http_url("http://192.168.1.10")


def test_provider_neutral_deliverable_does_not_need_provider_config():
    from ProofPay.agents.scoping_agent.validators import detect_unresolved_and_placeholder_params
    milestones = [{
        "title": "Payment Integration",
        "description": "Implement a provider-neutral payment gateway integration.",
        "acceptance_criteria": [{
            "type": "deliverable_check", "params": {
                "deliverable": "Payment gateway integration",
                "acceptance_checks": ["Test payment flow completes successfully"]
            }
        }]
    }]
    errors, unresolved = detect_unresolved_and_placeholder_params(milestones, {})
    assert "payment_provider" not in unresolved
    assert not any("payment provider" in item.lower() for item in errors)


def test_verification_result_persists_separately_from_locked_plan(tmp_path):
    from ProofPay.services.database import SQLiteProjectStore
    database_file = tmp_path / "verification-test.db"
    store = SQLiteProjectStore(f"sqlite:////{database_file.as_posix().lstrip('/')}")
    try:
        store.save_verification_submission(
            submission_id="sub_test", project_id="project_test", milestone_id="m1",
            freelancer_id="freelancer_test", status="CLIENT_REVIEW_REQUIRED",
            result={"decision": "CLIENT_REVIEW_REQUIRED", "verification_score": 0.75},
        )
        saved = store.get_verification_submission("sub_test")
        assert saved["status"] == "CLIENT_REVIEW_REQUIRED"
        assert saved["result"]["verification_score"] == 0.75
        assert store.list_verification_submissions("project_test", "m1")[0]["submission_id"] == "sub_test"
    finally:
        store.close()
