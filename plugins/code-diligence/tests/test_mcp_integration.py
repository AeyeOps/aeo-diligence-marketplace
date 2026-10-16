"""Exercise warehouse operations over their actual MCP transport."""
import json
import subprocess
from pathlib import Path

from code_diligence.narration.taxonomy import load_taxonomy_into_warehouse
from code_diligence.warehouse.connection import open_warehouse
from code_diligence.warehouse.migrations import migrate
from code_diligence.warehouse.targets import register_target

MCP_DIR = Path(__file__).parent.parent / "mcp" / "diligence-warehouse"


def test_mcp_operations_over_stdio(tmp_path: Path) -> None:
    warehouse = tmp_path / "warehouse.duckdb"
    with open_warehouse(warehouse) as conn:
        migrate(conn)
        register_target(conn, target_id="acme", name="Acme")
        load_taxonomy_into_warehouse(conn)
    proc = subprocess.Popen(
        ["uv", "run", "--directory", str(MCP_DIR), "python", "-m", "server", "--warehouse", str(warehouse)],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True,
    )
    try:
        assert proc.stdin is not None and proc.stdout is not None
        request_id = 0

        def request(method: str, params: dict) -> dict:
            nonlocal request_id
            request_id += 1
            proc.stdin.write(json.dumps({"jsonrpc": "2.0", "id": request_id, "method": method, "params": params}) + "\n")
            proc.stdin.flush()
            response = json.loads(proc.stdout.readline())
            assert response["id"] == request_id
            assert "error" not in response, response
            return response["result"]

        request("initialize", {
            "protocolVersion": "2024-11-05", "capabilities": {},
            "clientInfo": {"name": "integration-check", "version": "1"},
        })
        proc.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n")
        proc.stdin.flush()
        listed = request("tools/list", {})
        assert {tool["name"] for tool in listed["tools"]} == {
            "list_tables", "describe_table", "read_query", "write_narrative",
        }
        tables = request("tools/call", {"name": "list_tables", "arguments": {}})
        assert {row["name"] for row in tables["structuredContent"]["tables"]} >= {"targets", "narratives"}
        columns = request("tools/call", {"name": "describe_table", "arguments": {"name": "targets"}})
        assert columns["structuredContent"]["columns"][0]["name"] == "target_id"
        read = request("tools/call", {
            "name": "read_query", "arguments": {"sql": "SELECT target_id FROM targets UNION SELECT 'second'"},
        })
        assert sorted(read["structuredContent"]["rows"]) == [["acme"], ["second"]]
        rejected = request("tools/call", {"name": "read_query", "arguments": {"sql": "DELETE FROM targets"}})
        assert rejected["isError"]
        written = request("tools/call", {"name": "write_narrative", "arguments": {
            "target_id": "acme", "axis": "people", "section_key": "bus_factor_map",
            "body_md": "Ownership data is unavailable.", "tier": "quick",
        }})
        assert written["structuredContent"]["ok"]
        reread = request("tools/call", {"name": "read_query", "arguments": {"sql": "SELECT body_md FROM narratives"}})
        assert reread["structuredContent"]["rows"] == [["Ownership data is unavailable."]]
    finally:
        proc.terminate()
        proc.wait(timeout=5)
