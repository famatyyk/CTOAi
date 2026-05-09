from runner import issue_sync


def test_list_open_issues_paginates(monkeypatch):
    calls = []

    def fake_github_api(method, url, token, payload=None):
        calls.append((method, url, token, payload))
        if url.endswith("page=1"):
            return [{"number": i} for i in range(100)]
        if url.endswith("page=2"):
            return [{"number": 100}, {"number": 101}]
        return []

    monkeypatch.setattr(issue_sync, "github_api", fake_github_api)

    items = issue_sync.list_open_issues("https://api.github.com/repos/famatyyk/CTOAi", "token")

    assert len(items) == 102
    assert len(calls) == 2
    assert "page=1" in calls[0][1]
    assert "page=2" in calls[1][1]


def test_split_primary_and_duplicates_keeps_oldest_issue_number():
    grouped = {
        "CTOA-001": [{"number": 53}, {"number": 5}, {"number": 43}],
        "CTOA-002": [{"number": 11}],
    }

    primary, duplicates = issue_sync.split_primary_and_duplicates(grouped)

    assert primary["CTOA-001"]["number"] == 5
    assert primary["CTOA-002"]["number"] == 11
    assert [i["number"] for i in duplicates] == [43, 53]
