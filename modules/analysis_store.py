"""
analysis_store.py — migração dos perfis/diagnósticos antigos (arquivos JSON em
output/) para a tabela `analyses` (modules/app_store.py: SQLite ou Postgres).

Até aqui a UI listava `output/*_profile.json` e emparelhava cada arquivo com um
`*_diagnosis.json` pelo nome. Agora o SQLite é a fonte única: esta função importa
uma vez cada arquivo legado ainda não visto e registra o nome em `legacy_imports`,
para que um perfil excluído na UI não "ressuscite" a partir do arquivo antigo.
"""

import json
import os
from datetime import datetime, timezone

from modules.app_store import AppStore

PROFILE_SUFFIX = "_profile.json"
DIAGNOSIS_SUFFIX = "_diagnosis.json"
NAME_SEP = "__"


def parse_profile_name(name: str) -> dict:
    """Extrai subject/depth/n_games de um nome `{subject}__d{depth}[_g{n}]_{uid}`.

    Nomes fora desse formato (ex.: `sprandel`) viram apenas `{"subject": name}`.
    """
    out = {"subject": name, "depth": None, "n_games": None}
    if NAME_SEP not in name:
        return out
    subject, meta = name.rsplit(NAME_SEP, 1)
    tokens = meta.split("_")
    if not (tokens and tokens[0].startswith("d") and tokens[0][1:].isdigit()):
        return out
    out["subject"] = subject
    out["depth"] = int(tokens[0][1:])
    if len(tokens) >= 2 and tokens[1].startswith("g") and tokens[1][1:].isdigit():
        out["n_games"] = int(tokens[1][1:])
    return out


def _created_at(profile: dict, path: str) -> str:
    """Data da análise em UTC ('YYYY-MM-DD HH:MM:SS'): generated_at ou mtime do arquivo."""
    generated = profile.get("generated_at")
    if generated:
        try:
            dt = datetime.strptime(generated.replace(" UTC", ""), "%Y-%m-%d %H:%M")
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            pass
    mtime = datetime.fromtimestamp(os.path.getmtime(path), tz=timezone.utc)
    return mtime.strftime("%Y-%m-%d %H:%M:%S")


def import_legacy_outputs(db: AppStore, output_dir: str, owner_id: int | None = None) -> int:
    """Importa para o banco os `*_profile.json` (+ diagnóstico) ainda não importados.

    owner_id: dono das análises importadas (None = sem dono; a conta administradora
    as assume em claim_orphan_analyses). Idempotente; arquivos ilegíveis são
    ignorados. Retorna quantos foram importados.
    """
    if not output_dir or not os.path.isdir(output_dir):
        return 0

    imported = 0
    for fname in sorted(os.listdir(output_dir)):
        if not fname.endswith(PROFILE_SUFFIX):
            continue
        name = fname[: -len(PROFILE_SUFFIX)]
        if db.is_legacy_imported(name):
            continue
        if db.get_analysis(name) is not None:
            db.mark_legacy_imported(name)
            continue

        path = os.path.join(output_dir, fname)
        try:
            with open(path, "r", encoding="utf-8") as f:
                profile = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue

        parsed = parse_profile_name(name)
        meta = profile.get("metadata") or {}
        db.save_analysis(
            name,
            profile,
            subject=parsed["subject"],
            source=meta.get("source"),
            depth=meta.get("depth") or parsed["depth"],
            n_games=parsed["n_games"],
            created_at=_created_at(profile, path),
            owner_id=owner_id,
        )

        diag_path = os.path.join(output_dir, name + DIAGNOSIS_SUFFIX)
        if os.path.exists(diag_path):
            try:
                with open(diag_path, "r", encoding="utf-8") as f:
                    db.save_diagnosis(name, json.load(f))
            except (OSError, json.JSONDecodeError):
                pass

        db.mark_legacy_imported(name)
        imported += 1
    return imported
