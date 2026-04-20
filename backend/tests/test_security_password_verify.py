from api.core import security


def test_verify_password_fails_closed_on_unexpected_argon2_error(monkeypatch):
    class ExplodingHasher:
        def verify(self, hashed, plain):
            raise RuntimeError("boom")

    monkeypatch.setattr(security, "_ph", ExplodingHasher())

    assert security.verify_password("Nanovia!Pass123", "$argon2id$dummy") is False
