"""code-diligence CLI: typer-based entry point."""
import os
import shutil
import subprocess
from pathlib import Path

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from code_diligence.curation.orchestrate import run_curation_pass
from code_diligence.ingest.cheap_tools import run_cheap_tools_for_repo
from code_diligence.ingest.isolation import isolated
from code_diligence.ingest.persist import persist_repo_git_facts
from code_diligence.ingest.walker import walk_commits
from code_diligence.narration.confidence import compute_axis_confidence
from code_diligence.narration.taxonomy import load_taxonomy_into_warehouse
from code_diligence.narration.runner import run_narrator_for_target
from code_diligence.settings.loader import load_target_settings
from code_diligence.tools.git_truck import GIT_TRUCK_VERSION
from code_diligence.warehouse.connection import open_warehouse
from code_diligence.warehouse.migrations import migrate
from code_diligence.warehouse.repos import upsert_repo
from code_diligence.warehouse.targets import register_target, update_tooling_versions


app = typer.Typer(help="code-diligence: PE technical due diligence dashboard from git history.")


def _infer_full_name(repo_dir: Path) -> str:
    """Parse git remote origin URL and return 'owner/repo', or fall back to dir name."""
    import re
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_dir), "remote", "get-url", "origin"],
            capture_output=True, text=True, timeout=5,
        )
        url = result.stdout.strip()
        # Match github.com/owner/repo with optional .git suffix
        m = re.search(r"github\.com[:/]([^/]+/[^/]+?)(?:\.git)?$", url)
        if m:
            return m.group(1)
    except Exception:  # noqa: BLE001
        pass
    return repo_dir.name


def _collect_tooling_versions(*, full: bool) -> dict[str, str]:
    """Return {tool_name: version} for every tool reachable on this machine.

    Always records the in-tree walker wrapper. For each external CLI, runs its
    --version flag and records the trimmed output; tools not on PATH are
    recorded as "not-installed" so the column reflects environment provenance.
    """
    from importlib.metadata import PackageNotFoundError, version as _pkg_version
    try:
        pkg_version = _pkg_version("code-diligence")
    except PackageNotFoundError:
        pkg_version = "0.0.0"
    versions: dict[str, str] = {"code-diligence-walker": pkg_version}
    cheap = [
        ("git-fame", ["git-fame", "--version"]),
        ("git-of-theseus", ["git-of-theseus-analyze", "--version"]),
        ("git-truck", ["npx", "--yes", f"git-truck@{GIT_TRUCK_VERSION}", "--version"]),
    ]
    expensive = [
        ("hercules", ["hercules", "--version"]),
        ("code-maat", ["java", "-version"]),
        ("repowise", ["repowise", "--version"]),
    ]
    candidates = cheap + (expensive if full else [])
    for name, cmd in candidates:
        if not shutil.which(cmd[0]):
            versions[name] = "not-installed"
            continue
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            out = (result.stdout or result.stderr or "").strip().splitlines()
            versions[name] = out[0] if out else "unknown"
        except Exception:  # noqa: BLE001
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
    if not (quick or full):
        console.print("[red]Specify either --quick or --full[/red]")
        raise typer.Exit(2)

    s = load_target_settings(settings)
    warehouse_path = Path(s.storage.warehouse_path).expanduser()
    repo_root = Path(s.storage.repo_clone_root).expanduser()

    with open_warehouse(warehouse_path) as conn:
        migrate(conn)
        register_target(
            conn, target_id=s.target_id, name=s.target_name,
            description=s.description,
        )

        # Discover repos: subdirs of repo_clone_root each containing .git
        candidates = [d for d in sorted(repo_root.iterdir()) if (d / ".git").is_dir()]
        if not candidates:
            console.print(f"[yellow]No git repos found under {repo_root}[/yellow]")
            return

        with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console) as progress:
            task = progress.add_task("ingesting", total=len(candidates))
            for repo_dir in candidates:
                repo_id = f"{s.target_id}/{repo_dir.name}"
                progress.update(task, description=f"ingesting {repo_id}")
                upsert_repo(
                    conn, repo_id=repo_id, target_id=s.target_id,
                    name=repo_dir.name, source_url=str(repo_dir),
                )
                # clone-or-fetch is a no-op here because dest == source for local fixture
                # but the call validates the path is a usable git repo
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

        # Curation pass: heuristics → YAML → warehouse curation tables
        # Best-effort target_domain inference from settings; analyst can override
        # via the FTE classification YAML afterward.
        target_domain: str | None = None
        if s.sources.github.enabled and s.sources.github.orgs:
            target_domain = f"{s.sources.github.orgs[0]}.com"

        curation_dir = Path(s.storage.curation_dir).expanduser()
        run_curation_pass(
            conn,
            target_id=s.target_id,
            target_domain=target_domain,
            curation_dir=curation_dir,
            repo_root=repo_root,
            abandoned_threshold_days=s.heuristics.abandoned_threshold_days,
        )

        if full:
            from code_diligence.ingest.expensive_tools import run_expensive_tools_for_repo
            for repo_dir in candidates:
                repo_id = f"{s.target_id}/{repo_dir.name}"
                run_expensive_tools_for_repo(
                    conn, target_id=s.target_id, repo_id=repo_id, repo_path=repo_dir,
                )

        if full and s.sources.github.enabled:
            from code_diligence.settings.loader import resolve_token
            from code_diligence.ingest.platform import run_platform_pass_for_repo
            token = resolve_token(s.sources.github.token_env)
            for repo_dir in candidates:
                repo_id = f"{s.target_id}/{repo_dir.name}"
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

        narrator_tier = "full" if full else "quick"
        if shutil.which("claude") and os.environ.get("ANTHROPIC_API_KEY"):
            run_narrator_for_target(
                warehouse_path=warehouse_path,
                target_id=s.target_id, tier=narrator_tier,
            )
        else:
            console.print("[yellow]Skipping narrator pass (claude CLI or ANTHROPIC_API_KEY missing); "
                          "dashboard will render without narrative summaries.[/yellow]")

        update_tooling_versions(
            conn, target_id=s.target_id,
            versions=_collect_tooling_versions(full=full),
        )

        console.print(f"[green]{'Full' if full else 'Quick'} tier ingest complete for {s.target_id}[/green]")


if __name__ == "__main__":
    app()
