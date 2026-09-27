# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
# mcp-kill —— 按 mcp-analyze.py 生成的计划执行清杀（带 PID 复用防护），并输出前后内存对比
# 用法：uv run scripts/mcp-kill.py [--plan-path <mcp-kill-plan.json>]
# 防护：执行前重新快照，仅当 PID 仍是 cmd.exe/node.exe 且命令行含 npx 才杀。

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
DEFAULT_PLAN = SCRIPTS_DIR / "mcp-kill-plan.json"

MB = 1024 * 1024
WRAPPERS = {"cmd.exe", "node.exe", "conhost.exe", "npm.exe"}

PS_QUERY_PROCS = (
    "Get-CimInstance Win32_Process | Select-Object ProcessId, ParentProcessId, Name, CommandLine, "
    "WorkingSetSize, @{n='CreatedIso';e={ if ($_.CreationDate) { $_.CreationDate.ToString('o') } else { $null } }} "
    "| ConvertTo-Json -Compress"
)
PS_QUERY_OS = (
    "Get-CimInstance Win32_OperatingSystem | Select-Object TotalVisibleMemorySize, FreePhysicalMemory "
    "| ConvertTo-Json -Compress"
)

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
if sys.stderr.encoding and sys.stderr.encoding.lower() not in ("utf-8", "utf8"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def ps_json(query: str):
    r = subprocess.run(
        ["powershell", "-NoProfile", "-Command", query],
        capture_output=True, text=True, encoding="utf-8", errors="replace", maxBuffer=64 * 1024 * 1024,
    )
    if r.returncode != 0:
        print(f"PowerShell 查询失败：{r.stderr.strip()}", file=sys.stderr)
        sys.exit(1)
    raw = r.stdout.strip()
    if not raw:
        return []
    parsed = json.loads(raw)
    return parsed if isinstance(parsed, list) else [parsed]


def is_npx_related(p: dict) -> bool:
    cl = p.get("CommandLine") or ""
    return (p["Name"] == "node.exe" and "npx" in cl) or \
           (p["Name"] == "cmd.exe" and "/c" in cl and "npx" in cl)


def root_name_of(p: dict, by_id: dict[int, dict]) -> str:
    """沿 wrapper 链上溯（最多 8 跳）找真实 owner 名。"""
    cur, rn = p, "(dead)"
    for _ in range(8):
        par = by_id.get(int(cur["ParentProcessId"]))
        if not par:
            break
        if par["Name"] not in WRAPPERS:
            rn = par["Name"]
            break
        cur = par
    return rn


def main() -> int:
    parser = argparse.ArgumentParser(description="按计划执行 MCP 僵尸进程清杀并输出前后对比")
    parser.add_argument("--plan-path", default=str(DEFAULT_PLAN), help="清杀计划路径")
    args = parser.parse_args()

    plan = json.loads(Path(args.plan_path).read_text(encoding="utf-8"))
    baseline = plan["Baseline"]

    # fresh snapshot for at-kill-time verification (anti PID-reuse)
    all_procs = ps_json(PS_QUERY_PROCS)
    by_id = {int(p["ProcessId"]): p for p in all_procs}

    ok = skipped = already_gone = 0
    for tp in plan["KillTops"]:
        p = by_id.get(int(tp))
        if not p:
            already_gone += 1
            print(f"PID {tp} : already gone")
            continue
        if p["Name"] not in ("cmd.exe", "node.exe"):
            skipped += 1
            print(f"SKIP PID {tp} : unexpected name {p['Name']}")
            continue
        if "npx" not in (p.get("CommandLine") or ""):
            skipped += 1
            print(f"SKIP PID {tp} : cmdline no longer matches npx")
            continue
        r = subprocess.run(["taskkill.exe", "/PID", str(tp), "/T", "/F"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode == 0:
            ok += 1
        else:
            skipped += 1
            print(f"FAIL PID {tp} : {(r.stdout + r.stderr).strip()}")
    print(f"killed chains={ok}  skipped={skipped}  alreadyGone={already_gone}")

    time.sleep(3)

    # ---- after stats ----
    os_info = ps_json(PS_QUERY_OS)[0]
    total_kb = int(os_info["TotalVisibleMemorySize"])
    free_kb = int(os_info["FreePhysicalMemory"])
    after_free = round(free_kb / 1024 / 1024, 2)
    after_pct = round(100 * (1 - free_kb / total_kb), 1)

    proc2 = ps_json(PS_QUERY_PROCS)
    cnt_node = sum(1 for p in proc2 if p["Name"] == "node.exe")
    cnt_cmd = sum(1 for p in proc2 if p["Name"] == "cmd.exe")
    cnt_con = sum(1 for p in proc2 if p["Name"] == "conhost.exe")

    # census of remaining npx-related processes (should all be younger than the threshold)
    by_id2 = {int(p["ProcessId"]): p for p in proc2}
    remain = [p for p in proc2 if is_npx_related(p)]

    print()
    print(f"=== BEFORE ===  Mem {baseline['UsedPct']}% used, {baseline['FreeGB']} GB free")
    print(f"=== AFTER  ===  Mem {after_pct}% used, {after_free} GB free")
    print(f"remaining: node={cnt_node}  cmd={cnt_cmd}  conhost={cnt_con}  npx-related={len(remain)}")
    if remain:
        remain_by_root: dict[str, list] = {}
        now = datetime.now()
        for p in remain:
            remain_by_root.setdefault(root_name_of(p, by_id2), []).append(p)
        for root, group in remain_by_root.items():
            max_age = max(
                round((now - datetime.fromisoformat(p["CreatedIso"])).total_seconds() / 3600, 1)
                for p in group if p.get("CreatedIso")
            )
            print(f"  {root:<20} count={len(group):<3} maxAge={max_age}h")
    return 0


if __name__ == "__main__":
    sys.exit(main())
