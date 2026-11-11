"""Administração de contas e dados (usa o mesmo banco da interface: DATABASE_URL ou SQLite).

    python manage.py info
    python manage.py create-user ana [--admin]        # pede a senha (ou --password-stdin)
    python manage.py set-password ana                 # redefine e encerra as sessões
    python manage.py delete-user ana                  # apaga a conta e as análises dela
    python manage.py list-users
    python manage.py import-sqlite data/profiler.db --owner ana
        # copia as análises (e explicações) de um SQLite local para o banco configurado
        # — ex.: levar para o Postgres do deploy o que foi analisado antes no PC
    python manage.py purge-sessions                   # remove sessões expiradas
"""
import argparse
import getpass
import json
import sys

from modules.app_store import AppStore, AuthError


def _read_password(args) -> str:
    if args.password_stdin:
        return sys.stdin.readline().rstrip("\n")
    first = getpass.getpass("Senha: ")
    if getpass.getpass("Confirme a senha: ") != first:
        sys.exit("As senhas não conferem.")
    return first


def _user_or_exit(store: AppStore, username: str) -> dict:
    user = store.get_user_by_username(username)
    if user is None:
        sys.exit(f"Conta não encontrada: {username}")
    return user


def cmd_info(store, args):
    print(f"Banco: {store.location}")
    print(f"Contas: {store.user_count()}")
    print(f"Análises: {len(store.list_analyses())}")


def cmd_create_user(store, args):
    try:
        user = store.create_user(args.username, _read_password(args),
                                 is_admin=True if args.admin else None)
    except AuthError as e:
        sys.exit(f"Erro: {e.code}")
    print(f"Conta criada: {user['username']} (id {user['id']}"
          f"{', administradora' if user['is_admin'] else ''})")


def cmd_set_password(store, args):
    try:
        store.set_password(args.username, _read_password(args))
    except AuthError as e:
        sys.exit(f"Erro: {e.code}")
    print("Senha redefinida; sessões abertas foram encerradas.")


def cmd_delete_user(store, args):
    user = _user_or_exit(store, args.username)
    n = len(store.list_analyses(owner_id=user["id"]))
    if not args.yes:
        answer = input(f"Apagar {user['username']} e {n} análise(s)? Digite o nome para confirmar: ")
        if answer.strip() != user["username"]:
            sys.exit("Cancelado.")
    store.delete_user(user["id"])
    print("Conta apagada.")


def cmd_list_users(store, args):
    for u in store.list_users():
        n = len(store.list_analyses(owner_id=u["id"]))
        flag = " [admin]" if u["is_admin"] else ""
        print(f"{u['id']:>4}  {u['username']}{flag}  análises={n}  "
              f"criada={u['created_at'][:16]}  último login={(u['last_login_at'] or '—')[:16]}")


def cmd_import_sqlite(store, args):
    owner = _user_or_exit(store, args.owner)
    with AppStore(path=args.path) as src:
        if not store.is_pg and src.path.resolve() == store.path.resolve():
            sys.exit("Origem e destino são o mesmo banco.")
        copied = skipped = 0
        for row in src.iter_analysis_rows():
            if store.get_analysis(row["name"]) is not None:
                skipped += 1
                continue
            store.save_analysis(
                row["name"], json.loads(row["profile_json"]), subject=row["subject"],
                source=row["source"], depth=row["depth"], n_games=row["n_games"],
                created_at=row["created_at"], owner_id=owner["id"],
            )
            if row.get("diagnosis_json"):
                store.save_diagnosis(row["name"], json.loads(row["diagnosis_json"]),
                                     diagnosed_at=row.get("diagnosed_at"))
            copied += 1
        explanations = src._all("SELECT fen, move_played, concept_key, lang, text FROM explanations")
        for e in explanations:
            store.save_explanation(e["fen"], e["move_played"], e["concept_key"], e["lang"], e["text"])
    print(f"Análises copiadas: {copied} (já existentes: {skipped}); explicações: {len(explanations)}")


def cmd_purge_sessions(store, args):
    print(f"Sessões expiradas removidas: {store.purge_expired_sessions()}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Administração do Chess Profiler")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("info", help="mostra qual banco está em uso").set_defaults(fn=cmd_info)

    p = sub.add_parser("create-user", help="cria uma conta")
    p.add_argument("username")
    p.add_argument("--admin", action="store_true", help="marca a conta como administradora")
    p.add_argument("--password-stdin", action="store_true", help="lê a senha da entrada padrão")
    p.set_defaults(fn=cmd_create_user)

    p = sub.add_parser("set-password", help="redefine a senha de uma conta")
    p.add_argument("username")
    p.add_argument("--password-stdin", action="store_true")
    p.set_defaults(fn=cmd_set_password)

    p = sub.add_parser("delete-user", help="apaga uma conta e as análises dela")
    p.add_argument("username")
    p.add_argument("--yes", action="store_true", help="não pede confirmação")
    p.set_defaults(fn=cmd_delete_user)

    sub.add_parser("list-users", help="lista as contas").set_defaults(fn=cmd_list_users)

    p = sub.add_parser("import-sqlite", help="copia análises de um SQLite para o banco configurado")
    p.add_argument("path", help="arquivo SQLite de origem (ex.: data/profiler.db)")
    p.add_argument("--owner", required=True, help="conta que vai receber as análises")
    p.set_defaults(fn=cmd_import_sqlite)

    sub.add_parser("purge-sessions", help="remove sessões expiradas").set_defaults(fn=cmd_purge_sessions)
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    with AppStore() as store:
        args.fn(store, args)


if __name__ == "__main__":
    main()
