"""Tests fuer die Admin-Werkzeuge (backend/admin.py) gegen eine Wegwerf-DB."""
from __future__ import annotations

import pytest

from backend import admin, auth, db
from tests.conftest import TEST_PASSWORD


@pytest.fixture()
def dbp(tmp_path):
    path = tmp_path / "admin.db"
    db.init_db(path)
    return path


def test_create_invites(dbp):
    codes = admin.create_invites(3, db_path=dbp)
    assert len(codes) == 3 and len(set(codes)) == 3
    for code in codes:
        inv = db.get_invite_code(code, db_path=dbp)
        assert inv is not None and inv["used_by"] is None
        assert len(code) >= 10  # lang genug gegen Raten


def test_reset_password_changes_login_and_kills_sessions(dbp):
    code = admin.create_invites(1, db_path=dbp)[0]
    user = auth.register_user(code, "reset@example.com", "Reset Test",
                              TEST_PASSWORD, db_path=dbp)
    token = auth.create_session(user["id"], db_path=dbp)
    assert auth.get_user_for_token(token, db_path=dbp) is not None

    admin.reset_password("Reset@Example.com", "neuesgeheim1", db_path=dbp)

    # Altes Passwort weg, neues gilt, alle Sessions abgemeldet.
    fresh = db.get_user_by_email("reset@example.com", db_path=dbp)
    assert auth.verify_password("neuesgeheim1", fresh["password_hash"])
    assert not auth.verify_password(TEST_PASSWORD, fresh["password_hash"])
    assert auth.get_user_for_token(token, db_path=dbp) is None


def test_reset_password_unknown_email(dbp):
    with pytest.raises(ValueError, match="Kein Konto"):
        admin.reset_password("niemand@example.com", "neuesgeheim1", db_path=dbp)


def test_reset_password_validates_rules(dbp):
    code = admin.create_invites(1, db_path=dbp)[0]
    auth.register_user(code, "regeln@example.com", "Regeln", TEST_PASSWORD, db_path=dbp)
    with pytest.raises(ValueError, match="mindestens 8 Zeichen"):
        admin.reset_password("regeln@example.com", "kurz", db_path=dbp)
