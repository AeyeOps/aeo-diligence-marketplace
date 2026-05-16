"""Smoke test: spawn the MCP server as a subprocess and exchange a JSON-RPC list_tools call."""
import json
import os
import subprocess
import sys
from pathlib import Path

import duckdb
import pytest


PLUGIN_ROOT = Path(__file__).parent.parent
MCP_DIR = PLUGIN_ROOT / "mcp" / "diligence-warehouse"


@pytest.fixture
def warehouse(tmp_path: Path) -> Path:
    db = tmp_path / "t.duckdb"
    conn = duckdb.connect(str(db))
    conn.execute("CREATE TABLE narratives (target_id VARCHAR, axis VARCHAR, "
                 "section_key VARCHAR, body_md VARCHAR, "
                 "generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, "
                 "generator_version VARCHAR, tier VARCHAR, "
                 "PRIMARY KEY (target_id, axis, section_key))")
    conn.execute("CREATE TABLE smoke (x INTEGER)")
    conn.close()
    return db


def test_mcp_server_lists_tools(warehouse: Path) -> None:
    """Exchange one initialize + list_tools round-trip with the server over stdio."""
    proc = subprocess.Popen(
        ["uv", "run", "--directory", str(MCP_DIR), "python", "-m", "server",
         "--warehouse", str(warehouse)],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True,
    )
    try:
        # Minimal JSON-RPC initialize handshake (MCP protocol)
        init_req = {
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "test", "version": "0.0.0"}},
        }
        proc.stdin.write(json.dumps(init_req) + "\n")
        proc.stdin.flush()
        init_resp_line = proc.stdout.readline()
        assert "result" in init_resp_line, f"unexpected init response: {init_resp_line!r}"

        # initialized notification
        proc.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n")
        proc.stdin.flush()

        # tools/list
        list_req = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
        proc.stdin.write(json.dumps(list_req) + "\n")
        proc.stdin.flush()
        list_resp_line = proc.stdout.readline()
        list_resp = json.loads(list_resp_line)
        tool_names = {t["name"] for t in list_resp["result"]["tools"]}
        assert tool_names == {"list_tables", "describe_table", "read_query", "write_narrative"}
    finally:
        proc.terminate()
        proc.wait(timeout=5)
