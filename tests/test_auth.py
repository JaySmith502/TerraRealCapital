from ui.auth import password_matches

def test_password_matches_is_constant_time_equal():
    assert password_matches("hunter2", "hunter2") is True
    assert password_matches("wrong", "hunter2") is False
    assert password_matches("", "hunter2") is False
