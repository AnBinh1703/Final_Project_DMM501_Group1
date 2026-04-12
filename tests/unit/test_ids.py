from src.utils.ids import new_request_id


def test_new_request_id_is_uuid_like() -> None:
    rid = new_request_id()
    assert isinstance(rid, str)
    assert len(rid) >= 32
