#!/usr/bin/env python3
"""Deploy only today's BTC analysis, preserving the live fund's trade ledger."""

import argparse
import hashlib
import os
from pathlib import Path
import subprocess
import tempfile
from datetime import datetime, timezone


HERE = Path(__file__).resolve().parents[1]
SOURCE = HERE / "index.html"
HOST = "ubuntu@13.53.199.22"
LIVE = "/home/ubuntu/brainai-hq-v2/public/fund1-dashboard/index.html"
START = '<div class="analysis" id="daily-analysis">'
END = '<div class="app-footer">'


def run(*args, input_data=None):
    return subprocess.run(args, input=input_data, capture_output=True, check=True).stdout


def sha(data):
    return hashlib.sha256(data).hexdigest()


def block(data):
    assert data.count(START) == 1 and data.count(END) == 1, "Unexpected dashboard structure"
    start, end = data.index(START), data.index(END)
    assert start < end
    return start, end


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Compare without deploying")
    args = parser.parse_args()

    source = SOURCE.read_text()
    today = datetime.now(timezone.utc).strftime("%B %-d, %Y")
    assert today in source[source.index('id="analysis-date"'):][:150], "Local analysis is not dated today"
    source_start, source_end = block(source)
    current_bytes = run("ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", HOST, "cat", LIVE)
    current = current_bytes.decode()
    current_start, current_end = block(current)
    merged = current[:current_start] + source[source_start:source_end] + current[current_end:]
    merged_bytes = merged.encode()
    print(f"current={sha(current_bytes)} updated={sha(merged_bytes)} date={today}")
    if current_bytes == merged_bytes or args.check:
        print("already current" if current_bytes == merged_bytes else "check only")
        return

    with tempfile.NamedTemporaryFile(suffix=".html") as staged:
        staged.write(merged_bytes)
        staged.flush()
        remote_stage = f"/tmp/fund1-analysis-{os.getpid()}.html"
        run("scp", "-q", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", staged.name, f"{HOST}:{remote_stage}")
        remote_code = f"""
from pathlib import Path
from hashlib import sha256
from shutil import copy2
from datetime import datetime, timezone
from os import replace, chmod
live = Path({LIVE!r})
staged = Path({remote_stage!r})
digest = lambda path: sha256(path.read_bytes()).hexdigest()
assert digest(live) == {sha(current_bytes)!r}, 'Live dashboard changed during deployment'
assert digest(staged) == {sha(merged_bytes)!r}, 'Staged dashboard hash mismatch'
backups = Path('/home/ubuntu/fund1-dashboard-backups')
backups.mkdir(mode=0o700, exist_ok=True)
backup = backups / ('index-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '.html')
copy2(live, backup)
assert digest(backup) == {sha(current_bytes)!r}
temporary = live.with_name('.index.html.analysis.tmp')
copy2(staged, temporary)
chmod(temporary, live.stat().st_mode)
replace(temporary, live)
staged.unlink()
assert digest(live) == {sha(merged_bytes)!r}
print('deployed=' + digest(live) + ' backup=' + str(backup))
"""
        print(run("ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", HOST, "python3", "-", input_data=remote_code.encode()).decode().strip())

    public = run("ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", HOST,
                 "curl", "-4fsSL", "--max-time", "15", "https://brainai.bot/fund1-dashboard/")
    assert sha(public) == sha(merged_bytes), "Public dashboard does not match deployment"
    print("public URL verified")


if __name__ == "__main__":
    main()
