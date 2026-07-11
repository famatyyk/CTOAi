import argparse
import importlib.util
import json
from pathlib import Path


def _load_module():
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "ops" / "azure_activity_alerts.py"
    spec = importlib.util.spec_from_file_location("azure_activity_alerts", module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_parse_records_payload_supports_log_analytics_tables():
    module = _load_module()

    payload = {
        "tables": [
            {
                "columns": [{"name": "OperationNameValue"}, {"name": "ActivityStatusValue"}],
                "rows": [["Microsoft.Network/networkSecurityGroups/securityRules/delete", "Failed"]],
            }
        ]
    }

    rows = module.parse_records_payload(payload)

    assert len(rows) == 1
    assert rows[0]["OperationNameValue"].endswith("/delete")
    assert rows[0]["ActivityStatusValue"] == "Failed"


def test_normalize_record_picks_expected_fields():
    module = _load_module()

    record = {
        "eventTimestamp": "2026-05-23T13:03:55.000Z",
        "operationName": {"value": "Microsoft.Authorization/roleAssignments/write"},
        "status": {"value": "Succeeded"},
        "subStatus": {"value": "Created"},
        "resourceId": "/subscriptions/x/resourceGroups/rg/providers/Microsoft.KeyVault/vaults/kv-prod",
        "caller": "admin@contoso.com",
        "correlationId": "abc-123",
    }

    normalized = module.normalize_record(record)

    assert normalized["event_type"] == "azure_activity_log"
    assert normalized["operation_name"] == "Microsoft.Authorization/roleAssignments/write"
    assert normalized["resource_id"].endswith("/kv-prod")
    assert normalized["caller"] == "admin@contoso.com"


def test_classify_high_impact_flags_rbac_and_keyvault_as_critical():
    module = _load_module()

    normalized = {
        "operation_name": "Microsoft.Authorization/roleAssignments/write",
        "resource_id": "/subscriptions/x/resourceGroups/rg/providers/Microsoft.KeyVault/vaults/kv-prod",
        "status": "Succeeded",
        "sub_status": "Created",
    }

    classified = module.classify_high_impact(normalized)

    assert classified["severity"] == "critical"
    assert "rbac_change" in classified["labels"]
    assert "keyvault_change" in classified["labels"]


def test_run_pipeline_filters_below_min_severity(tmp_path: Path):
    module = _load_module()

    source = tmp_path / "sample.json"
    source.write_text(
        json.dumps(
            [
                {
                    "eventTimestamp": "2026-05-23T13:03:55.000Z",
                    "operationName": {"value": "Microsoft.Resources/subscriptions/resourcegroups/read"},
                    "status": {"value": "Succeeded"},
                    "subStatus": {"value": "OK"},
                    "resourceId": "/subscriptions/x/resourceGroups/rg-readonly",
                    "caller": "reader@contoso.com",
                    "correlationId": "corr-readonly",
                }
            ]
        ),
        encoding="utf-8",
    )

    args = argparse.Namespace(
        ingest_mode="file",
        source_file=str(source),
        source_format="json",
        routes="jsonl",
        output_jsonl=str(tmp_path / "alerts.jsonl"),
        webhook_url="",
        min_severity="warning",
        dry_run=False,
    )

    result = module.run_pipeline(args)

    assert result["total_records"] == 1
    assert result["routed_alerts"] == 0
    assert result["filtered_alerts"] == 1


def test_run_pipeline_routes_critical_alert_to_jsonl(tmp_path: Path):
    module = _load_module()

    source = tmp_path / "sample.json"
    source.write_text(
        json.dumps(
            [
                {
                    "eventTimestamp": "2026-05-23T13:03:55.000Z",
                    "operationName": {"value": "Microsoft.Compute/virtualMachines/delete"},
                    "status": {"value": "Succeeded"},
                    "subStatus": {"value": "OK"},
                    "resourceId": "/subscriptions/x/resourceGroups/rg/providers/Microsoft.Compute/virtualMachines/vm-a",
                    "caller": "automation@contoso.com",
                    "correlationId": "corr-delete",
                }
            ]
        ),
        encoding="utf-8",
    )

    output = tmp_path / "alerts.jsonl"
    args = argparse.Namespace(
        ingest_mode="file",
        source_file=str(source),
        source_format="json",
        routes="jsonl",
        output_jsonl=str(output),
        webhook_url="",
        min_severity="warning",
        dry_run=False,
    )

    result = module.run_pipeline(args)

    assert result["routed_alerts"] == 1
    lines = output.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    payload = json.loads(lines[0])
    assert payload["severity"] == "critical"
    assert payload["event"]["correlation_id"] == "corr-delete"


def test_post_json_rejects_non_http_webhook_url(monkeypatch):
    module = _load_module()
    calls = []

    def fake_urlopen(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError("urlopen must not run for invalid webhook URLs")

    monkeypatch.setattr(module.urlrequest, "urlopen", fake_urlopen)

    assert module.post_json("file:///tmp/hook", {"ok": True}) == (False, "invalid_url")
    assert module.post_json("example.invalid/hook", {"ok": True}) == (False, "invalid_url")
    assert calls == []


def test_post_json_uses_validated_http_url(monkeypatch):
    module = _load_module()
    calls: dict[str, object] = {}

    class Response:
        status = 204

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    def fake_urlopen(request, timeout: int):
        calls["url"] = request.full_url
        calls["method"] = request.get_method()
        calls["timeout"] = timeout
        return Response()

    monkeypatch.setattr(module.urlrequest, "urlopen", fake_urlopen)

    assert module.post_json("https://hooks.example/alerts", {"ok": True}, timeout_s=3) == (True, "http_204")
    assert calls == {"url": "https://hooks.example/alerts", "method": "POST", "timeout": 3}


def test_post_discord_json_rejects_non_discord_webhook_url(monkeypatch):
    module = _load_module()
    calls = []

    def fake_urlopen(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError("urlopen must not run for invalid Discord webhook URLs")

    monkeypatch.setattr(module.urlrequest, "urlopen", fake_urlopen)

    blocked = [
        "http://discord.com/api/webhooks/123/token",
        "https://hooks.example/alerts",
        "https://hooks.slack.com/services/T/B/C",
        "https://user:secret@discord.com/api/webhooks/123/token",
        "https://discord.com/api/webhooks/123/token?token=secret",
        "https://discord.com/api/webhooks/123/token#fragment",
        "https://discord.com/api/webhooks/123/../token",
        "https://discord.com/api\\webhooks\\123\\token",
    ]

    for url in blocked:
        ok, detail = module.post_discord_json(url, {"ok": True})
        assert ok is False
        assert detail == "invalid_discord_webhook_url"
        assert url not in detail
        assert "secret" not in detail

    assert calls == []


def test_post_discord_json_uses_discord_allowlisted_url(monkeypatch):
    module = _load_module()
    calls: dict[str, object] = {}

    class Response:
        status = 204

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    def fake_urlopen(request, timeout: int):
        calls["url"] = request.full_url
        calls["method"] = request.get_method()
        calls["timeout"] = timeout
        return Response()

    monkeypatch.setattr(module.urlrequest, "urlopen", fake_urlopen)

    url = "https://discord.com/api/webhooks/123/token"
    assert module.post_discord_json(url, {"ok": True}, timeout_s=3) == (True, "http_204")
    assert calls == {"url": url, "method": "POST", "timeout": 3}


def test_route_alert_discord_webhook_rejects_generic_fallback_url(tmp_path: Path, monkeypatch):
    module = _load_module()

    def fake_urlopen(*args, **kwargs):
        raise AssertionError("urlopen must not run for invalid Discord webhook URLs")

    monkeypatch.setattr(module.urlrequest, "urlopen", fake_urlopen)

    result = module.route_alert(
        {"summary": "alert", "severity": "critical", "event": {}, "reasons": []},
        routes=["discord_webhook"],
        output_jsonl=tmp_path / "alerts.jsonl",
        webhook_url="https://hooks.example/alerts",
        discord_webhook_url="",
        dry_run=False,
    )

    assert result["discord_webhook"] == "failed:invalid_discord_webhook_url"
