"""
app_store.py — persistência durável dos dados de usuário.

Guarda o que não pode ser perdido num redeploy:
  users          : contas (nome + hash PBKDF2 da senha), bloqueio por tentativas.
  sessions       : sessões de login (só o SHA-256 do token; o token fica no cookie).
  analyses       : uma linha por análise (perfil + diagnóstico), com dono (owner_id).
  explanations   : cache das respostas "Explicar este erro" (compartilhado, por posição).
  legacy_imports : arquivos output/*_profile.json já importados.

Backends (escolhido em tempo de execução):
  - PostgreSQL quando DATABASE_URL está definida (Neon, Supabase, Render Postgres…).
    É a opção de deploy: o banco vive fora do container, então os dados sobrevivem a
    redeploys/reinícios mesmo em hospedagens sem disco persistente.
  - SQLite caso contrário (desenvolvimento local, CLI, testes) — no mesmo arquivo de
    modules/db.py (data/profiler.db), preservando as análises que já existem nele.

O cache do Stockfish e o dataset de posições continuam em modules/db.py (SQLite
local): são regeneráveis e de escrita intensa (milhares de linhas por análise), e
não compensam a latência de rede de um banco remoto.

Uso:
    from modules.app_store import AppStore

    with AppStore() as store:
        user = store.create_user("ana", "senha-forte")
        token = store.create_session(user["id"])
        store.user_for_token(token)            # -> user dict | None
        store.save_analysis(name, profile, owner_id=user["id"], ...)
        store.list_analyses(owner_id=user["id"])
"""

import hashlib
import hmac
import json
import re
import secrets
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

import config
from modules import db as _db_module

# ── Políticas de autenticação ─────────────────────────────────────────────────

PBKDF2_ITERATIONS = 600_000          # recomendação OWASP (2023) para PBKDF2-HMAC-SHA256
MAX_FAILED_LOGINS = 5                # tentativas erradas seguidas antes do bloqueio
LOCKOUT_MINUTES = 15
MIN_PASSWORD_LEN = 8
MAX_PASSWORD_LEN = 256
USERNAME_RE = re.compile(r"^[A-Za-z0-9_.-]{3,32}$")

_TS_FMT = "%Y-%m-%d %H:%M:%S.%f"


class AuthError(ValueError):
    """Falha de conta/login com um código estável (traduzido na UI: auth.err.<code>).

    Códigos: username_invalid, password_short, password_long, username_taken,
    invalid_credentials, locked, wrong_password, unknown_user.
    """

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _now(delta: timedelta | None = None) -> str:
    """Timestamp UTC ordenável como texto ('YYYY-MM-DD HH:MM:SS.ffffff')."""
    dt = datetime.now(timezone.utc)
    if delta:
        dt += delta
    return dt.strftime(_TS_FMT)


# ── Senhas ────────────────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    """'pbkdf2_sha256$<iter>$<salt hex>$<hash hex>' — o nº de iterações vai junto,
    então subir PBKDF2_ITERATIONS no futuro não invalida senhas antigas."""
    iterations = PBKDF2_ITERATIONS
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"pbkdf2_sha256${iterations}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, iterations, salt, digest = stored.split("$")
        if algo != "pbkdf2_sha256":
            return False
        candidate = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"),
                                        bytes.fromhex(salt), int(iterations))
    except (ValueError, TypeError, AttributeError):
        return False
    return hmac.compare_digest(candidate.hex(), digest)


def _needs_rehash(stored: str) -> bool:
    try:
        return int(stored.split("$")[1]) < PBKDF2_ITERATIONS
    except (IndexError, ValueError):
        return True


_dummy_hash_cache: dict[int, str] = {}


def _dummy_hash() -> str:
    """Hash descartável: login de usuário inexistente gasta o mesmo tempo que um real,
    para não revelar pelo tempo de resposta quais nomes existem."""
    if PBKDF2_ITERATIONS not in _dummy_hash_cache:
        _dummy_hash_cache[PBKDF2_ITERATIONS] = hash_password(secrets.token_hex(8))
    return _dummy_hash_cache[PBKDF2_ITERATIONS]


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def validate_username(username: str) -> str:
    username = (username or "").strip()
    if not USERNAME_RE.match(username):
        raise AuthError("username_invalid")
    return username


def validate_password(password: str) -> str:
    password = password or ""
    if len(password) < MIN_PASSWORD_LEN:
        raise AuthError("password_short")
    if len(password) > MAX_PASSWORD_LEN:
        raise AuthError("password_long")
    return password


# ── Conexões ──────────────────────────────────────────────────────────────────

def is_postgres_url(url: str | None) -> bool:
    return bool(url) and url.startswith(("postgres://", "postgresql://"))


_pools: dict = {}
_pools_lock = threading.Lock()
_schema_ready: set = set()
_schema_lock = threading.Lock()


def _pg_pool(url: str):
    """Pool de conexões por processo (Streamlit atende várias sessões em threads).

    check_connection descarta conexões que o servidor fechou por ociosidade (Neon e
    Supabase fazem isso), evitando erros na primeira consulta após um tempo parado.
    """
    with _pools_lock:
        pool = _pools.get(url)
        if pool is None:
            from psycopg.rows import dict_row
            from psycopg_pool import ConnectionPool

            pool = ConnectionPool(
                url,
                min_size=1,
                max_size=config.DB_POOL_MAX,
                kwargs={"autocommit": True, "row_factory": dict_row},
                check=ConnectionPool.check_connection,
                name="chess-profiler",
                open=True,
            )
            _pools[url] = pool
        return pool


def close_pools():
    """Fecha os pools de Postgres (testes / encerramento)."""
    with _pools_lock:
        for pool in _pools.values():
            pool.close()
        _pools.clear()


def reset_schema_cache():
    """Esquece quais bancos já tiveram o schema criado (testes que recriam tabelas)."""
    with _schema_lock:
        _schema_ready.clear()


def _schema(pg: bool) -> list[str]:
    pk = "BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY" if pg else "INTEGER PRIMARY KEY AUTOINCREMENT"
    ref = "BIGINT" if pg else "INTEGER"
    real = "DOUBLE PRECISION" if pg else "REAL"
    return [
        f"""CREATE TABLE IF NOT EXISTS users (
            id            {pk},
            username      TEXT    NOT NULL,
            username_key  TEXT    NOT NULL UNIQUE,
            password_hash TEXT    NOT NULL,
            is_admin      INTEGER NOT NULL DEFAULT 0,
            failed_logins INTEGER NOT NULL DEFAULT 0,
            locked_until  TEXT,
            created_at    TEXT    NOT NULL,
            last_login_at TEXT
        )""",
        f"""CREATE TABLE IF NOT EXISTS sessions (
            token_hash TEXT PRIMARY KEY,
            user_id    {ref} NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL
        )""",
        "CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id)",
        f"""CREATE TABLE IF NOT EXISTS analyses (
            name               TEXT PRIMARY KEY,
            subject            TEXT NOT NULL,
            source             TEXT,
            n_games            INTEGER,
            depth              INTEGER,
            total_games        INTEGER,
            total_positions    INTEGER,
            overall_error_rate {real},
            n_weaknesses       INTEGER,
            profile_json       TEXT NOT NULL,
            diagnosis_json     TEXT,
            created_at         TEXT NOT NULL,
            diagnosed_at       TEXT,
            owner_id           {ref} REFERENCES users(id) ON DELETE CASCADE
        )""",
        "CREATE INDEX IF NOT EXISTS idx_analyses_subject ON analyses(subject)",
        """CREATE TABLE IF NOT EXISTS explanations (
            fen         TEXT NOT NULL,
            move_played TEXT NOT NULL DEFAULT '',
            concept_key TEXT NOT NULL,
            lang        TEXT NOT NULL,
            text        TEXT NOT NULL,
            created_at  TEXT,
            PRIMARY KEY (fen, move_played, concept_key, lang)
        )""",
        """CREATE TABLE IF NOT EXISTS legacy_imports (
            name        TEXT PRIMARY KEY,
            imported_at TEXT
        )""",
    ]


# ── Store ─────────────────────────────────────────────────────────────────────

_USER_COLS = "id, username, is_admin, created_at, last_login_at"
_ANALYSIS_SUMMARY_COLS = (
    "name, subject, source, n_games, depth, total_games, total_positions, "
    "overall_error_rate, n_weaknesses, created_at, diagnosed_at, owner_id, "
    "CASE WHEN diagnosis_json IS NULL THEN 0 ELSE 1 END AS has_diagnosis"
)


def _public_user(row: dict | None) -> dict | None:
    if row is None:
        return None
    return {
        "id": row["id"],
        "username": row["username"],
        "is_admin": bool(row["is_admin"]),
        "created_at": row.get("created_at"),
        "last_login_at": row.get("last_login_at"),
    }


class AppStore:
    """Acesso aos dados duráveis. Use como context manager ou chame close()."""

    def __init__(self, url: str | None = None, path: str | Path | None = None):
        # Resolvido na chamada (não no import) para os testes poderem redirecionar.
        if url is None and path is None:
            url = config.DATABASE_URL
        self.is_pg = is_postgres_url(url)
        self._pool = None

        if self.is_pg:
            self._pool = _pg_pool(url)
            self._conn = self._pool.getconn()
            key = ("pg", url)
            self.location = "postgresql"
        else:
            if url:
                if not url.startswith("sqlite:///"):
                    raise ValueError(
                        "DATABASE_URL deve começar com postgresql:// (ou sqlite:///caminho)."
                    )
                path = url[len("sqlite:///"):]
            self.path = Path(path) if path is not None else Path(_db_module.DEFAULT_DB_PATH)
            self.path.parent.mkdir(parents=True, exist_ok=True)
            # isolation_level=None → autocommit, mesma semântica do pool Postgres.
            self._conn = sqlite3.connect(str(self.path), check_same_thread=False,
                                         isolation_level=None)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA foreign_keys = ON")
            self._conn.execute("PRAGMA journal_mode = WAL")
            self._conn.execute("PRAGMA busy_timeout = 5000")
            key = ("sqlite", str(self.path.resolve()))
            self.location = str(self.path)

        try:
            self._ensure_schema(key)
        except Exception:
            self.close()
            raise

    # ── SQL helpers ───────────────────────────────────────────────────────────

    def _x(self, sql: str, params=()):
        if self.is_pg:
            sql = sql.replace("?", "%s")
        return self._conn.execute(sql, params)

    def _one(self, sql: str, params=()) -> dict | None:
        row = self._x(sql, params).fetchone()
        return dict(row) if row is not None else None

    def _all(self, sql: str, params=()) -> list[dict]:
        return [dict(r) for r in self._x(sql, params).fetchall()]

    @contextmanager
    def _tx(self):
        """Transação explícita (as conexões estão em autocommit)."""
        if self.is_pg:
            with self._conn.transaction():
                yield
        else:
            self._conn.execute("BEGIN IMMEDIATE")
            try:
                yield
            except BaseException:
                self._conn.execute("ROLLBACK")
                raise
            self._conn.execute("COMMIT")

    def _integrity_errors(self) -> tuple:
        if self.is_pg:
            import psycopg
            return (psycopg.errors.IntegrityError,)
        return (sqlite3.IntegrityError,)

    def _ensure_schema(self, key):
        if key in _schema_ready:
            return
        with _schema_lock:
            if key in _schema_ready:
                return
            for stmt in _schema(self.is_pg):
                self._x(stmt)
            self._migrate()
            self._x("CREATE INDEX IF NOT EXISTS idx_analyses_owner ON analyses(owner_id, created_at)")
            _schema_ready.add(key)

    def _migrate(self):
        """Bancos criados antes do login: a tabela `analyses` não tinha dono."""
        if self.is_pg:
            self._x("ALTER TABLE analyses ADD COLUMN IF NOT EXISTS owner_id BIGINT "
                    "REFERENCES users(id) ON DELETE CASCADE")
            return
        cols = {r["name"] for r in self._all("PRAGMA table_info(analyses)")}
        if "owner_id" not in cols:
            self._x("ALTER TABLE analyses ADD COLUMN owner_id INTEGER "
                    "REFERENCES users(id) ON DELETE CASCADE")

    # ── Usuários ──────────────────────────────────────────────────────────────

    def user_count(self) -> int:
        return self._one("SELECT COUNT(*) AS n FROM users")["n"]

    def create_user(self, username: str, password: str, is_admin: bool | None = None) -> dict:
        """Cria a conta. A primeira conta do banco vira administradora (is_admin=None).

        Levanta AuthError(username_invalid|password_short|password_long|username_taken).
        """
        username = validate_username(username)
        validate_password(password)
        key = username.lower()
        if self._one("SELECT 1 AS x FROM users WHERE username_key = ?", (key,)):
            raise AuthError("username_taken")

        admin_expr = ("CASE WHEN EXISTS (SELECT 1 FROM users) THEN 0 ELSE 1 END"
                      if is_admin is None else "?")
        params = [username, key, hash_password(password)]
        if is_admin is not None:
            params.append(int(is_admin))
        params.append(_now())
        try:
            row = self._one(
                "INSERT INTO users (username, username_key, password_hash, is_admin, created_at) "
                f"SELECT ?, ?, ?, {admin_expr}, ? RETURNING {_USER_COLS}",
                params,
            )
        except self._integrity_errors():
            raise AuthError("username_taken")
        return _public_user(row)

    def get_user(self, user_id: int) -> dict | None:
        return _public_user(self._one(f"SELECT {_USER_COLS} FROM users WHERE id = ?", (user_id,)))

    def get_user_by_username(self, username: str) -> dict | None:
        return _public_user(self._one(f"SELECT {_USER_COLS} FROM users WHERE username_key = ?",
                                      ((username or "").strip().lower(),)))

    def list_users(self) -> list[dict]:
        rows = self._all(f"SELECT {_USER_COLS} FROM users ORDER BY id")
        return [_public_user(r) for r in rows]

    def authenticate(self, username: str, password: str) -> dict:
        """Confere usuário e senha. Retorna o usuário ou levanta AuthError.

        Após MAX_FAILED_LOGINS erros seguidos a conta fica bloqueada por
        LOCKOUT_MINUTES (AuthError("locked")), contendo força bruta.
        """
        row = self._one("SELECT * FROM users WHERE username_key = ?",
                        ((username or "").strip().lower(),))
        if row is None:
            verify_password(password or "", _dummy_hash())
            raise AuthError("invalid_credentials")

        now = _now()
        if row["locked_until"] and row["locked_until"] > now:
            raise AuthError("locked")

        if not verify_password(password or "", row["password_hash"]):
            failed = (row["failed_logins"] or 0) + 1
            if failed >= MAX_FAILED_LOGINS:
                self._x("UPDATE users SET failed_logins = 0, locked_until = ? WHERE id = ?",
                        (_now(timedelta(minutes=LOCKOUT_MINUTES)), row["id"]))
                raise AuthError("locked")
            self._x("UPDATE users SET failed_logins = ? WHERE id = ?", (failed, row["id"]))
            raise AuthError("invalid_credentials")

        updates, params = ["failed_logins = 0", "locked_until = NULL", "last_login_at = ?"], [now]
        if _needs_rehash(row["password_hash"]):
            updates.append("password_hash = ?")
            params.append(hash_password(password))
        self._x(f"UPDATE users SET {', '.join(updates)} WHERE id = ?", (*params, row["id"]))
        row["last_login_at"] = now
        return _public_user(row)

    def change_password(self, user_id: int, current: str, new: str,
                        keep_token: str | None = None):
        """Troca a senha (exige a atual) e encerra as outras sessões do usuário."""
        row = self._one("SELECT password_hash FROM users WHERE id = ?", (user_id,))
        if row is None:
            raise AuthError("unknown_user")
        if not verify_password(current or "", row["password_hash"]):
            raise AuthError("wrong_password")
        validate_password(new)
        with self._tx():
            self._x("UPDATE users SET password_hash = ? WHERE id = ?", (hash_password(new), user_id))
            self.revoke_user_sessions(user_id, except_token=keep_token)

    def set_password(self, username: str, new: str):
        """Redefinição administrativa (manage.py): sem a senha atual; derruba as sessões."""
        user = self.get_user_by_username(username)
        if user is None:
            raise AuthError("unknown_user")
        validate_password(new)
        with self._tx():
            self._x("UPDATE users SET password_hash = ?, failed_logins = 0, locked_until = NULL "
                    "WHERE id = ?", (hash_password(new), user["id"]))
            self.revoke_user_sessions(user["id"])

    def delete_user(self, user_id: int):
        """Remove a conta, suas sessões e suas análises (ON DELETE CASCADE)."""
        with self._tx():
            self._x("DELETE FROM sessions WHERE user_id = ?", (user_id,))
            self._x("DELETE FROM analyses WHERE owner_id = ?", (user_id,))
            self._x("DELETE FROM users WHERE id = ?", (user_id,))

    # ── Sessões ───────────────────────────────────────────────────────────────

    def create_session(self, user_id: int, ttl_days: int | None = None) -> str:
        """Abre uma sessão e devolve o token (só o hash dele é gravado)."""
        token = secrets.token_urlsafe(32)
        ttl = ttl_days if ttl_days is not None else config.SESSION_TTL_DAYS
        self._x("INSERT INTO sessions (token_hash, user_id, created_at, expires_at) "
                "VALUES (?, ?, ?, ?)",
                (_token_hash(token), user_id, _now(), _now(timedelta(days=ttl))))
        return token

    def user_for_token(self, token: str | None) -> dict | None:
        """Usuário dono de uma sessão válida (não expirada), ou None."""
        if not token or not isinstance(token, str):
            return None
        row = self._one(
            "SELECT u.id, u.username, u.is_admin, u.created_at, u.last_login_at "
            "FROM sessions s JOIN users u ON u.id = s.user_id "
            "WHERE s.token_hash = ? AND s.expires_at > ?",
            (_token_hash(token), _now()),
        )
        return _public_user(row)

    def revoke_session(self, token: str | None):
        if token:
            self._x("DELETE FROM sessions WHERE token_hash = ?", (_token_hash(token),))

    def revoke_user_sessions(self, user_id: int, except_token: str | None = None):
        if except_token:
            self._x("DELETE FROM sessions WHERE user_id = ? AND token_hash <> ?",
                    (user_id, _token_hash(except_token)))
        else:
            self._x("DELETE FROM sessions WHERE user_id = ?", (user_id,))

    def purge_expired_sessions(self) -> int:
        return self._x("DELETE FROM sessions WHERE expires_at <= ?", (_now(),)).rowcount

    # ── Análises (perfil + diagnóstico) ───────────────────────────────────────

    def save_analysis(self, name: str, profile: dict, subject: str | None = None,
                      source: str | None = None, depth: int | None = None,
                      n_games: int | None = None, created_at: str | None = None,
                      owner_id: int | None = None):
        """Insere ou atualiza o perfil de uma análise (mantém diagnóstico e dono)."""
        self._x(
            """
            INSERT INTO analyses (name, subject, source, n_games, depth, total_games,
                                  total_positions, overall_error_rate, n_weaknesses,
                                  profile_json, created_at, owner_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (name) DO UPDATE SET
                subject = excluded.subject, source = excluded.source,
                n_games = excluded.n_games, depth = excluded.depth,
                total_games = excluded.total_games,
                total_positions = excluded.total_positions,
                overall_error_rate = excluded.overall_error_rate,
                n_weaknesses = excluded.n_weaknesses,
                profile_json = excluded.profile_json,
                owner_id = COALESCE(analyses.owner_id, excluded.owner_id)
            """,
            (
                name, subject or name, source, n_games, depth,
                profile.get("total_games"), profile.get("total_positions_analyzed"),
                profile.get("overall_error_rate"), len(profile.get("weaknesses", [])),
                json.dumps(profile, ensure_ascii=False), created_at or _now(), owner_id,
            ),
        )

    def save_diagnosis(self, name: str, diagnosis: dict, diagnosed_at: str | None = None) -> bool:
        """Anexa o diagnóstico da IA a uma análise existente. False se não existir."""
        cur = self._x("UPDATE analyses SET diagnosis_json = ?, diagnosed_at = ? WHERE name = ?",
                      (json.dumps(diagnosis, ensure_ascii=False), diagnosed_at or _now(), name))
        return cur.rowcount > 0

    @staticmethod
    def _owner_filter(owner_id: int | None) -> tuple[str, tuple]:
        # owner_id=None → sem filtro (CLI / administração). A UI sempre passa o id.
        return ("", ()) if owner_id is None else (" AND owner_id = ?", (owner_id,))

    def list_analyses(self, owner_id: int | None = None) -> list[dict]:
        """Resumos (sem o JSON completo), mais recentes primeiro."""
        cond, params = self._owner_filter(owner_id)
        return self._all(
            f"SELECT {_ANALYSIS_SUMMARY_COLS} FROM analyses WHERE 1 = 1{cond} "
            "ORDER BY created_at DESC, name DESC",
            params,
        )

    def get_analysis(self, name: str, owner_id: int | None = None) -> dict | None:
        """Resumo + `profile` e `diagnosis` parseados, ou None (inexistente / de outro dono)."""
        cond, params = self._owner_filter(owner_id)
        d = self._one(
            f"SELECT {_ANALYSIS_SUMMARY_COLS}, profile_json, diagnosis_json "
            f"FROM analyses WHERE name = ?{cond}",
            (name, *params),
        )
        if d is None:
            return None
        d["profile"] = json.loads(d.pop("profile_json"))
        raw = d.pop("diagnosis_json")
        d["diagnosis"] = json.loads(raw) if raw else None
        return d

    def delete_analysis(self, name: str, owner_id: int | None = None) -> bool:
        cond, params = self._owner_filter(owner_id)
        return self._x(f"DELETE FROM analyses WHERE name = ?{cond}", (name, *params)).rowcount > 0

    def claim_orphan_analyses(self, owner_id: int) -> int:
        """Atribui a `owner_id` as análises sem dono (criadas antes do login ou pela CLI)."""
        return self._x("UPDATE analyses SET owner_id = ? WHERE owner_id IS NULL",
                       (owner_id,)).rowcount

    def iter_analysis_rows(self) -> list[dict]:
        """Linhas cruas de `analyses` (para copiar entre bancos em manage.py)."""
        return self._all("SELECT * FROM analyses ORDER BY created_at")

    # ── Importação de legados ─────────────────────────────────────────────────

    def is_legacy_imported(self, name: str) -> bool:
        return self._one("SELECT 1 AS x FROM legacy_imports WHERE name = ?", (name,)) is not None

    def mark_legacy_imported(self, name: str):
        self._x("INSERT INTO legacy_imports (name, imported_at) VALUES (?, ?) "
                "ON CONFLICT (name) DO NOTHING", (name, _now()))

    # ── Explicações ("Explicar este erro") ────────────────────────────────────

    def get_explanation(self, fen: str, move_played: str | None, concept_key: str,
                        lang: str) -> str | None:
        row = self._one(
            "SELECT text FROM explanations "
            "WHERE fen = ? AND move_played = ? AND concept_key = ? AND lang = ?",
            (fen, move_played or "", concept_key, lang),
        )
        return row["text"] if row else None

    def save_explanation(self, fen: str, move_played: str | None, concept_key: str,
                         lang: str, text: str):
        self._x(
            "INSERT INTO explanations (fen, move_played, concept_key, lang, text, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?) "
            "ON CONFLICT (fen, move_played, concept_key, lang) DO UPDATE SET "
            "text = excluded.text, created_at = excluded.created_at",
            (fen, move_played or "", concept_key, lang, text, _now()),
        )

    # ── Housekeeping ──────────────────────────────────────────────────────────

    def close(self):
        conn, self._conn = getattr(self, "_conn", None), None
        if conn is None:
            return
        if self._pool is not None:
            self._pool.putconn(conn)
        else:
            conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
