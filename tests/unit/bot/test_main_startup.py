import bot.main as bot_main


def test_run_handles_startup_failure_without_secondary_error(monkeypatch):
    def _raise_startup_error():
        raise RuntimeError("boom")

    monkeypatch.setattr(bot_main, "create_session", _raise_startup_error)

    bot_main.run()
