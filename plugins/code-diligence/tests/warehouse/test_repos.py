from pathlib import Path

from code_diligence.warehouse.connection import open_warehouse
from code_diligence.warehouse.migrations import migrate
from code_diligence.warehouse.repos import get_repo, list_repos, upsert_repo
from code_diligence.warehouse.targets import register_target


def test_upsert_repo_inserts_then_updates(tmp_path: Path) -> None:
    db_path = tmp_path / "test.duckdb"
    with open_warehouse(db_path) as conn:
        migrate(conn)
        register_target(conn, target_id="acme", name="Acme")
        upsert_repo(
            conn,
            repo_id="acme/api",
            target_id="acme",
            name="api",
            source_url="https://github.com/acme/api",
            default_branch="main",
        )
        first = get_repo(conn, "acme/api")
        upsert_repo(
            conn,
            repo_id="acme/api",
            target_id="acme",
            name="api",
            source_url="https://github.com/acme/api",
            default_branch="trunk",
        )
        second = get_repo(conn, "acme/api")
    assert first is not None and second is not None
    assert first["default_branch"] == "main"
    assert second["default_branch"] == "trunk"


def test_list_repos_filters_by_target(tmp_path: Path) -> None:
    db_path = tmp_path / "test.duckdb"
    with open_warehouse(db_path) as conn:
        migrate(conn)
        register_target(conn, target_id="acme", name="Acme")
        register_target(conn, target_id="beta", name="Beta")
        upsert_repo(conn, repo_id="acme/api", target_id="acme", name="api", source_url="x")
        upsert_repo(conn, repo_id="acme/web", target_id="acme", name="web", source_url="y")
        upsert_repo(conn, repo_id="beta/api", target_id="beta", name="api", source_url="z")
        acme = list_repos(conn, "acme")
        beta = list_repos(conn, "beta")
    assert {r["repo_id"] for r in acme} == {"acme/api", "acme/web"}
    assert {r["repo_id"] for r in beta} == {"beta/api"}
