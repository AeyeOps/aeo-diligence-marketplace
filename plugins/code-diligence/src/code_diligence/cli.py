"""code-diligence CLI: typer-based entry point."""
import re
import shutil
import subprocess
from pathlib import Path

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from code_diligence.curation.orchestrate import run_curation_pass
from code_diligence.github.client import GitHubClient, paginate
from code_diligence.ingest.cheap_tools import run_cheap_tools_for_repo
from code_diligence.ingest.cloner import clone_or_fetch
from code_diligence.ingest.isolation import isolated
from code_diligence.ingest.persist import persist_repo_git_facts
from code_diligence.ingest.walker import walk_commits
from code_diligence.narration.confidence import compute_axis_confidence
from code_diligence.narration.taxonomy import load_taxonomy_into_warehouse
from code_diligence.settings.loader import load_target_settings, resolve_token
from code_diligence.tools.code_maat import CODE_MAAT_JAR, CODE_MAAT_VERSION
from code_diligence.tools.git_truck import GIT_TRUCK_VERSION
from code_diligence.warehouse.connection import open_warehouse
from code_diligence.warehouse.migrations import migrate
from code_diligence.warehouse.repos import upsert_repo
from code_diligence.warehouse.targets import register_target, update_tooling_versions

app = typer.Typer(help="code-diligence: PE technical due diligence dashboard from git history.")


def _infer_full_name(repo_dir: Path) -> str:
    """Parse git remote origin URL and return 'owner/repo', or fall back to dir name."""
    result = subprocess.run(
        ["git", "-C", str(repo_dir), "remote", "get-url", "origin"],
        capture_output=True, text=True, check=False,
    )
    if result.returncode == 0:
        match = re.search(r"github\.com[:/]([^/]+/[^/]+?)(?:\.git)?$", result.stdout.strip())
        if match:
            return match.group(1)
    return repo_dir.name


def _collect_tooling_versions(*, full: bool) -> dict[str, str]:
    """Return {tool_name: version} for every tool reachable on this machine.

    Always records the in-tree walker wrapper. For each external CLI, runs its
    --version flag and records the trimmed output; tools not on PATH are
    recorded as "not-installed" so the column reflects environment provenance.
    """
    from importlib.metadata import PackageNotFoundError
    from importlib.metadata import version as _pkg_version
    try:
        pkg_version = _pkg_version("code-diligence")
    except PackageNotFoundError:
        pkg_version = "0.0.0"
    versions: dict[str, str] = {"code-diligence-walker": pkg_version}
    cheap = [
        ("git-fame", ["git-fame", "--version"]),
        ("git-of-theseus", ["git-of-theseus-analyze", "--version"]),
    ]
    expensive = [
        ("hercules", ["hercules", "--version"]),
        ("repowise", ["repowise", "--version"]),
    ]
    candidates = cheap + (expensive if full else [])
    versions["git-truck"] = GIT_TRUCK_VERSION if shutil.which("npx") else "not-installed"
    if full:
        versions["code-maat"] = CODE_MAAT_VERSION if CODE_MAAT_JAR.exists() and shutil.which("java") else "not-installed"
    for name, cmd in candidates:
        if not shutil.which(cmd[0]):
            versions[name] = "not-installed"
            continue
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            out = (result.stdout or result.stderr or "").strip().splitlines()
            versions[name] = out[0] if result.returncode == 0 and out else "unknown"
        except (OSError, subprocess.TimeoutExpired):
            versions[name] = "error"
    return versions
console = Console()


@app.callback()
def _main() -> None:
    """code-diligence: PE technical due diligence dashboard from git history."""


@app.command()
def ingest(
    settings: Path = typer.Argument(..., help="Path to a target's .local.md settings file"),
    quick: bool = typer.Option(False, "--quick", help="Quick tier: cheap tools only"),
    full: bool = typer.Option(False, "--full", help="Full tier: cheap + expensive tools"),
) -> None:
    """Ingest a target's repos into its warehouse."""
    if quick == full:
        console.print("[red]Specify either --quick or --full[/red]")
        raise typer.Exit(2)

    s = load_target_settings(settings)
    warehouse_path = Path(s.storage.warehouse_path).expanduser()
    repo_root = Path(s.storage.repo_clone_root).expanduser()

    token = None
    remote_repos = []
    if s.sources.github.enabled:
        assert s.sources.github.token_env is not None
        token = resolve_token(s.sources.github.token_env)
        with GitHubClient(token=token) as client:
            for org in s.sources.github.orgs:
                remote_repos.extend(
                    repo for repo in paginate(client, f"/orgs/{org}/repos", type="all")
                    if s.sources.github.include_archived or not repo["archived"]
                )
        repo_root.mkdir(parents=True, exist_ok=True)

    with open_warehouse(warehouse_path) as conn:
        migrate(conn)
        register_target(
            conn, target_id=s.target_id, name=s.target_name,
            description=s.description,
        )

        metadata = {}
        failed_repos = set()
        for remote in remote_repos:
            relative_name = remote["full_name"]
            repo_dir = repo_root / relative_name
            repo_id = f"{s.target_id}/{relative_name}"
            metadata[repo_dir] = remote
            upsert_repo(
                conn, repo_id=repo_id, target_id=s.target_id,
                name=relative_name, source_url=remote["clone_url"],
                default_branch=remote["default_branch"],
                language_primary=remote["language"], is_archived=remote["archived"],
            )
            fetched = isolated(
                conn, target_id=s.target_id, repo_id=repo_id,
                tool="git-fetch", tool_version=None,
                fn=lambda r=remote, d=repo_dir: clone_or_fetch(
                    source_url=r["clone_url"], dest=d, token=token,
                ),
            )
            if fetched is None:
                failed_repos.add(repo_dir)

        candidates = sorted(metadata.keys() - failed_repos) if s.sources.github.enabled else sorted({
            p.parent for pattern in ("*/.git", "*/*/.git")
            for p in repo_root.glob(pattern)
        })
        if not candidates:
            raise typer.BadParameter(f"No usable git repositories under {repo_root}")

        with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console) as progress:
            task = progress.add_task("ingesting", total=len(candidates))
            for repo_dir in candidates:
                relative_name = repo_dir.relative_to(repo_root).as_posix()
                repo_id = f"{s.target_id}/{relative_name}"
                progress.update(task, description=f"ingesting {repo_id}")
                upsert_repo(
                    conn, repo_id=repo_id, target_id=s.target_id,
                    name=relative_name, source_url=metadata.get(repo_dir, {}).get("clone_url", str(repo_dir)),
                    default_branch=metadata.get(repo_dir, {}).get("default_branch"),
                    language_primary=metadata.get(repo_dir, {}).get("language"),
                    is_archived=metadata.get(repo_dir, {}).get("archived", False),
                )
                if repo_dir not in metadata:
                    remote = subprocess.run(
                        ["git", "-C", str(repo_dir), "remote", "get-url", "origin"],
                        capture_output=True, text=True,
                    )
                    if remote.returncode == 0:
                        fetched = isolated(
                            conn, target_id=s.target_id, repo_id=repo_id,
                            tool="git-fetch", tool_version=None,
                            fn=lambda d=repo_dir, url=remote.stdout.strip(): clone_or_fetch(source_url=url, dest=d),
                        )
                        if fetched is None:
                            failed_repos.add(repo_dir)
                            continue
                isolated(
                    conn, target_id=s.target_id, repo_id=repo_id,
                    tool="walker", tool_version="0.1.0",
                    fn=lambda d=repo_dir, rid=repo_id: persist_repo_git_facts(
                        conn, repo_id=rid, commits=walk_commits(d),
                    ),
                )
                run_cheap_tools_for_repo(
                    conn, target_id=s.target_id, repo_id=repo_id,
                    repo_path=repo_dir,
                )
                progress.advance(task)

        candidates = [repo_dir for repo_dir in candidates if repo_dir not in failed_repos]


        target_domain: str | None = None

        curation_dir = Path(s.storage.curation_dir).expanduser()
        run_curation_pass(
            conn,
            target_id=s.target_id,
            target_domain=target_domain,
            curation_dir=curation_dir,
            repo_root=repo_root,
            abandoned_threshold_days=s.heuristics.abandoned_threshold_days,
            fte_inference=s.heuristics.fte_inference,
        )

        if full:
            from code_diligence.ingest.expensive_tools import (
                run_expensive_tools_for_repo,
            )
            for repo_dir in candidates:
                repo_id = f"{s.target_id}/{repo_dir.relative_to(repo_root).as_posix()}"
                run_expensive_tools_for_repo(
                    conn, target_id=s.target_id, repo_id=repo_id, repo_path=repo_dir,
                )

        if full and s.sources.github.enabled:
            from code_diligence.ingest.platform import run_platform_pass_for_repo
            assert token is not None
            for repo_dir in candidates:
                repo_id = f"{s.target_id}/{repo_dir.relative_to(repo_root).as_posix()}"
                repo_full_name = _infer_full_name(repo_dir)
                run_platform_pass_for_repo(
                    conn, target_id=s.target_id, repo_id=repo_id,
                    repo_full_name=repo_full_name, token=token,
                    pr_data=s.sources.github_platform.pr_data,
                    actions_data=s.sources.github_platform.actions_data,
                    issues_data=s.sources.github_platform.issues_data,
                )

        compute_axis_confidence(conn, target_id=s.target_id)

        load_taxonomy_into_warehouse(conn)

        update_tooling_versions(
            conn, target_id=s.target_id,
            versions=_collect_tooling_versions(full=full),
        )

        console.print(f"Curation files: {curation_dir}")
        for filename in ("identity-merges.yaml", "fte-classification.yaml", "repo-classification.yaml"):
            import yaml
            entries = yaml.safe_load((curation_dir / filename).read_text())
            console.print(f"{filename}: {len(entries['needs_review'])} entries need review")
        conn.execute("UPDATE targets SET last_refreshed_at = CURRENT_TIMESTAMP WHERE target_id = ?", [s.target_id])
        failures = conn.execute(
            "SELECT tool, class, COUNT(*) FROM tool_failures WHERE target_id = ? GROUP BY tool, class",
            [s.target_id],
        ).fetchall()
        for tool, failure_class, count in failures:
            console.print(f"[yellow]{tool}: {count} recorded {failure_class} failures[/yellow]")
        console.print(f"[green]{'Full' if full else 'Quick'} tier ingest complete for {s.target_id}[/green]")


if __name__ == "__main__":
    app()
