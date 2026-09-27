# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
# mcp-analyze —— 扫描 MCP 僵尸进程链（npx 拉起的 node 服务 + cmd 包装链），生成清杀计划
# 用法：
#   uv run scripts/mcp-analyze.py                     # 默认阈值 2 小时
#   uv run scripts/mcp-analyze.py --threshold-hours 1
# 规则：① 孤儿链（owner 会话已退出）→ 无论新旧一律清杀；
#       ② 挂靠中但早于阈值 → 清杀；其余保留。
# 说明：进程表经 powershell 子进程取 Win32_Process（CreationDate 转 ISO 字符串），
#       内存基线取 Win32_OperatingSystem；计划落盘 mcp-kill-plan.json 供 mcp-kill.py 执行。

import argparse
import json
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
DEFAULT_PLAN = SCRIPTS_DIR / "mcp-kill-plan.json"

MB = 1024 * 1024

# wrapper processes that may sit inside an MCP chain (between the real owner app and the server)
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
        return None
    parsed = json.loads(raw)
    return parsed if isinstance(parsed, list) else [parsed]


def main() -> int:
    parser = argparse.ArgumentParser(description="扫描 MCP 僵尸进程链并生成清杀计划")
    parser.add_argument("--threshold-hours", type=float, default=2.0, help="清杀阈值小时数（默认 2）")
    parser.add_argument("--plan-path", default=str(DEFAULT_PLAN), help="清杀计划输出路径")
    args = parser.parse_args()

    # ---- baseline memory ----
    os_info = ps_json(PS_QUERY_OS)[0]
    total_kb = int(os_info["TotalVisibleMemorySize"])
    free_kb = int(os_info["FreePhysicalMemory"])
    baseline = {
        "TotalGB": round(total_kb / 1024 / 1024, 2),
        "FreeGB": round(free_kb / 1024 / 1024, 2),
        "UsedPct": round(100 * (1 - free_kb / total_kb), 1),
    }

    # ---- snapshot processes ----
    all_procs = ps_json(PS_QUERY_PROCS)
    by_id = {int(p["ProcessId"]): p for p in all_procs}

    now = datetime.now()
    cutoff = now - timedelta(hours=args.threshold_hours)

    # targets: npx-launched node servers, plus cmd wrappers that launch npx (cmd /c npx ...)
    # NOTE: interactive user terminals never have npx in their own command line, so they are excluded naturally
    targets = [
        p for p in all_procs
        if (p["Name"] == "node.exe" and p.get("CommandLine") and "npx" in p["CommandLine"])
        or (p["Name"] == "cmd.exe" and p.get("CommandLine")
            and "/c" in p["CommandLine"] and "npx" in p["CommandLine"])
    ]

    rows = []
    for t in targets:
        # walk up the chain: through wrapper processes only
        cur, top = t, t
        root_proc, orphan, hops = None, False, 0
        while hops < 10:
            par = by_id.get(int(cur["ParentProcessId"]))
            if not par:
                orphan = True
                break
            # PID-reuse guard: a real parent is always older than its child
            cur_c = cur.get("CreatedIso")
            par_c = par.get("CreatedIso")
            if cur_c and par_c and datetime.fromisoformat(par_c) > datetime.fromisoformat(cur_c):
                orphan = True
                break
            if par["Name"] not in WRAPPERS:
                root_proc = par
                break
            cur, top = par, par
            hops += 1
        created = datetime.fromisoformat(t["CreatedIso"]) if t.get("CreatedIso") else now
        rows.append({
            "Pid": int(t["ProcessId"]),
            "Name": t["Name"],
            "Created": t.get("CreatedIso"),
            "CreatedDt": created,
            "AgeHrs": round((now - created).total_seconds() / 3600, 1),
            "MemMB": round(int(t.get("WorkingSetSize") or 0) / MB),
            "Orphan": orphan,
            "Root": "(dead)" if orphan else (root_proc["Name"] if root_proc else "(deep-chain)"),
            "KillTopPid": int(top["ProcessId"]),
            "KillTopName": top["Name"],
            "CmdLine": t.get("CommandLine") or "",
            "Verdict": "",
        })

    # ---- rule 1: orphans (owner session gone) -> kill regardless of age ----
    for r in rows:
        if r["Orphan"]:
            r["Verdict"] = "orphan"

    # ---- rule 2: any attached instance older than the threshold -> kill ----
    age_tag = f"old>{args.threshold_hours}h"
    for r in rows:
        if not r["Orphan"] and r["CreatedDt"] < cutoff:
            r["Verdict"] = age_tag

    kill_rows = [r for r in rows if r["Verdict"]]
    keep_rows = [r for r in rows if not r["Verdict"]]
    kill_tops = sorted({r["KillTopPid"] for r in kill_rows})

    # ---- report ----
    print("=== BASELINE ===")
    print(f"Mem: {baseline['UsedPct']}% used, {baseline['FreeGB']} GB free / {baseline['TotalGB']} GB total"
          f"   (threshold: {args.threshold_hours}h)")
    print()
    print("=== TARGETS BY ROOT (all npx-related processes found) ===")
    if not rows:
        print("(none found)")
    by_root: dict[str, list] = {}
    for r in rows:
        by_root.setdefault(r["Root"], []).append(r)
    for root, group in sorted(by_root.items(), key=lambda kv: -len(kv[1])):
        print(f"{root:<22} count={len(group):<4} mem={sum(g['MemMB'] for g in group):>6} MB")
    print()
    print(f"=== KILL LIST: {len(kill_rows)} processes in {len(kill_tops)} chains ===")
    for r in sorted(kill_rows, key=lambda x: (x["Verdict"], x["Root"], x["Created"] or "")):
        cl = r["CmdLine"][:70]
        print(f"{r['Pid']:<8} {r['Name']:<9} {r['Root']:<14} age={r['AgeHrs']:>6}h "
              f"{r['Verdict']:<10} top={r['KillTopPid']} :: {cl}")
    print()
    print(f"=== KEEP: {len(keep_rows)} processes ===")
    for r in sorted(keep_rows, key=lambda x: (x["Root"], x["Created"] or "")):
        cl = r["CmdLine"][:70]
        print(f"{r['Pid']:<8} {r['Name']:<9} {r['Root']:<14} age={r['AgeHrs']:>6}h "
              f"top={r['KillTopPid']} :: {cl}")
    print()
    est_mb = sum(r["MemMB"] for r in kill_rows)
    print(f"Estimated direct reclaim from node targets: {est_mb} MB "
          "(working set only; commit + compressed store reclaim may differ)")

    # ---- save kill plan for the execute step ----
    plan = {
        "TakenAt": now.isoformat(),
        "Baseline": baseline,
        "ThresholdHours": args.threshold_hours,
        "KillTops": kill_tops,
    }
    Path(args.plan_path).write_text(json.dumps(plan, indent=2), encoding="utf-8")
    print()
    print(f"Kill plan saved: {args.plan_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
