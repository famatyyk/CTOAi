def test_resolve_client_profile_from_kamil_client_path():
    from scripts.ops.client_profile_router import resolve_client_profile

    assert resolve_client_profile(r"C:\Users\zycie\Downloads\kamil-client\bin\klient.exe") == "kamil_client"


def test_resolve_client_profile_from_otclient_path():
    from scripts.ops.client_profile_router import resolve_client_profile

    assert resolve_client_profile(r"C:\Games\OTClient\bin\client.exe") == "otclient_generic"
