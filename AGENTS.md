# Fund 1 dashboard deployment

`https://brainai.bot/fund1-dashboard/` is served from
`ubuntu@13.53.199.22:/home/ubuntu/brainai-hq-v2/public/fund1-dashboard/index.html`.
Pushing this repository or the `fork` remote does **not** update that URL.

The live file has server-only trade records. Never replace it with this checkout's
entire `index.html`. For daily BTC analysis, update the local analysis block and
run `python3 scripts/deploy-live-analysis.py`. The script merges only the
`daily-analysis` block into a fresh live copy, backs up the previous file, and
verifies the public URL. `--check` compares without deploying.
