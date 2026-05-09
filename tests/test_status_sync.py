from runner import status_sync


def test_update_live_issue_sla_section_appends_and_patches(monkeypatch):
    patched_payloads = []

    def fake_github_api(method, url, token, payload=None):
        if method == "GET":
            return {"body": "# CTOA Live Status\n\n- Generated: now\n"}
        patched_payloads.append(payload)
        return {"number": 1}

    monkeypatch.setattr(status_sync, "github_api", fake_github_api)

    changed = status_sync.update_live_issue_sla_section(
        "https://api.github.com/repos/famatyyk/CTOAi",
        "token",
        1,
        "## SLA Alert: Approval Pending >12h\n\n- item",
    )

    assert changed is True
    assert len(patched_payloads) == 1
    body = patched_payloads[0]["body"]
    assert "<!-- ctoa-sla-section:start -->" in body
    assert "## SLA Alert: Approval Pending >12h" in body
    assert "<!-- ctoa-sla-section:end -->" in body


def test_update_live_issue_sla_section_no_change(monkeypatch):
    section = (
        "<!-- ctoa-sla-section:start -->\n"
        "## SLA Alert: Approval Pending >12h\n\n- item\n"
        "<!-- ctoa-sla-section:end -->"
    )
    existing = f"# CTOA Live Status\n\n{section}"
    calls = []

    def fake_github_api(method, url, token, payload=None):
        calls.append((method, url, payload))
        if method == "GET":
            return {"body": existing}
        return {"number": 1}

    monkeypatch.setattr(status_sync, "github_api", fake_github_api)

    changed = status_sync.update_live_issue_sla_section(
        "https://api.github.com/repos/famatyyk/CTOAi",
        "token",
        1,
        "## SLA Alert: Approval Pending >12h\n\n- item",
    )

    assert changed is False
    assert [c[0] for c in calls] == ["GET"]


def test_update_live_issue_sla_section_removes_stale_section(monkeypatch):
    existing = (
        "# CTOA Live Status\n\n"
        "<!-- ctoa-sla-section:start -->\n"
        "## SLA Alert: Approval Pending >12h\n\n- old\n"
        "<!-- ctoa-sla-section:end -->"
    )
    patched_payloads = []

    def fake_github_api(method, url, token, payload=None):
        if method == "GET":
            return {"body": existing}
        patched_payloads.append(payload)
        return {"number": 1}

    monkeypatch.setattr(status_sync, "github_api", fake_github_api)

    changed = status_sync.update_live_issue_sla_section(
        "https://api.github.com/repos/famatyyk/CTOAi",
        "token",
        1,
        None,
    )

    assert changed is True
    assert len(patched_payloads) == 1
    assert "<!-- ctoa-sla-section:start -->" not in patched_payloads[0]["body"]
