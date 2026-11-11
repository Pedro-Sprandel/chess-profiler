"""manage.py — account administration and SQLite → configured-store migration."""
import io

import pytest

import manage
from modules.app_store import AppStore


def _run(monkeypatch, *argv, stdin=""):
    monkeypatch.setattr("sys.stdin", io.StringIO(stdin))
    manage.main(list(argv))


class TestUsers:
    def test_create_user_from_stdin(self, monkeypatch, capsys, store):
        _run(monkeypatch, "create-user", "ana", "--password-stdin", stdin="correct-horse\n")
        assert "ana" in capsys.readouterr().out
        assert store.authenticate("ana", "correct-horse")["is_admin"]

    def test_create_user_rejects_weak_password(self, monkeypatch):
        with pytest.raises(SystemExit):
            _run(monkeypatch, "create-user", "ana", "--password-stdin", stdin="short\n")

    def test_set_password(self, monkeypatch, store):
        store.create_user("ana", "correct-horse")
        _run(monkeypatch, "set-password", "ana", "--password-stdin", stdin="another-pass\n")
        assert store.authenticate("ana", "another-pass")

    def test_delete_user(self, monkeypatch, store):
        user = store.create_user("ana", "correct-horse")
        _run(monkeypatch, "delete-user", "ana", "--yes")
        assert store.get_user(user["id"]) is None

    def test_list_users_and_info(self, monkeypatch, capsys, store):
        store.create_user("ana", "correct-horse")
        _run(monkeypatch, "list-users")
        _run(monkeypatch, "info")
        out = capsys.readouterr().out
        assert "ana [admin]" in out and "Contas: 1" in out


class TestImportSqlite:
    def test_copies_analyses_with_diagnosis_to_owner(self, monkeypatch, tmp_path, store):
        src_path = tmp_path / "laptop.db"
        with AppStore(path=src_path) as src:
            src.save_analysis("run1", {"weaknesses": []}, subject="bob", depth=10,
                              created_at="2026-05-01 12:00:00")
            src.save_diagnosis("run1", {"en": {"confidence": "HIGH"}})
            src.save_explanation("fen", "e2e4", "weak_square", "pt", "texto")
        owner = store.create_user("ana", "correct-horse")

        _run(monkeypatch, "import-sqlite", str(src_path), "--owner", "ana")
        _run(monkeypatch, "import-sqlite", str(src_path), "--owner", "ana")  # idempotent

        rows = store.list_analyses(owner_id=owner["id"])
        assert [r["name"] for r in rows] == ["run1"]
        rec = store.get_analysis("run1")
        assert rec["created_at"] == "2026-05-01 12:00:00"
        assert rec["diagnosis"] == {"en": {"confidence": "HIGH"}}
        assert store.get_explanation("fen", "e2e4", "weak_square", "pt") == "texto"
