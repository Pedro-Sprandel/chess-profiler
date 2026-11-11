"""Legacy output/*.json → SQLite import."""
import json

import pytest

from modules.analysis_store import import_legacy_outputs, parse_profile_name
from modules.app_store import AppStore

PROFILE = {"generated_at": "2026-05-13 18:20 UTC", "total_games": 30,
           "total_positions_analyzed": 900, "overall_error_rate": 0.25,
           "metadata": {"player": "bob", "source": "chess_com", "depth": 12},
           "weaknesses": []}


@pytest.fixture
def db(store):
    return store


def _write(dirpath, name, diagnosis=None):
    (dirpath / f"{name}_profile.json").write_text(json.dumps(PROFILE))
    if diagnosis is not None:
        (dirpath / f"{name}_diagnosis.json").write_text(json.dumps(diagnosis))


class TestParseProfileName:
    def test_structured_name(self):
        assert parse_profile_name("bob__d12_g30_a1b2c3") == {"subject": "bob", "depth": 12, "n_games": 30}

    def test_structured_without_games(self):
        assert parse_profile_name("bob__d10_a1b2c3") == {"subject": "bob", "depth": 10, "n_games": None}

    def test_plain_name(self):
        assert parse_profile_name("sprandel") == {"subject": "sprandel", "depth": None, "n_games": None}


class TestImportLegacy:
    def test_imports_profile_and_diagnosis(self, db, tmp_path):
        _write(tmp_path, "bob__d12_g30_abc123", diagnosis={"en": {"confidence": "HIGH"}})
        assert import_legacy_outputs(db, str(tmp_path)) == 1
        rec = db.get_analysis("bob__d12_g30_abc123")
        assert rec["subject"] == "bob"
        assert rec["depth"] == 12
        assert rec["source"] == "chess_com"
        assert rec["created_at"] == "2026-05-13 18:20:00"
        assert rec["diagnosis"] == {"en": {"confidence": "HIGH"}}

    def test_is_idempotent(self, db, tmp_path):
        _write(tmp_path, "bob")
        import_legacy_outputs(db, str(tmp_path))
        assert import_legacy_outputs(db, str(tmp_path)) == 0
        assert len(db.list_analyses()) == 1

    def test_deleted_analysis_is_not_reimported(self, db, tmp_path):
        _write(tmp_path, "bob")
        import_legacy_outputs(db, str(tmp_path))
        db.delete_analysis("bob")
        assert import_legacy_outputs(db, str(tmp_path)) == 0
        assert db.get_analysis("bob") is None

    def test_skips_unreadable_files(self, db, tmp_path):
        (tmp_path / "broken_profile.json").write_text("{not json")
        assert import_legacy_outputs(db, str(tmp_path)) == 0

    def test_missing_dir(self, db, tmp_path):
        assert import_legacy_outputs(db, str(tmp_path / "nope")) == 0

    def test_owner_can_be_assigned(self, db, tmp_path):
        owner = db.create_user("ana", "correct-horse")
        _write(tmp_path, "bob")
        import_legacy_outputs(db, str(tmp_path), owner_id=owner["id"])
        assert [a["name"] for a in db.list_analyses(owner_id=owner["id"])] == ["bob"]
