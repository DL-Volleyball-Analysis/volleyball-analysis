#!/usr/bin/env bash
# Start the whole app offline and open one analysed match: API (:8000), two analysis workers, review UI (:5173).
#
#   scripts/demo.sh                      # opens fixed_gcu_ucla
#   scripts/demo.sh broadcast_side_rally # opens another analysed video by name
#   scripts/demo.sh --check              # start, check every part answers, stop
#
# Results come from webapp/data (already analysed), so nothing waits on analysis. Ctrl-C stops everything; the workers
# put any job they were running back in the queue.
set -euo pipefail
cd "$(dirname "$0")/.."
py=.venv/bin/python
name=fixed_gcu_ucla
check=0
for a in "$@"; do
  case "$a" in
    --check) check=1 ;;
    *) name="$a" ;;
  esac
done

db=webapp/data/webapp.db
[ -f "$db" ] || { echo "no app database at $db: analyse a video first" >&2; exit 1; }
vid=$(sqlite3 "$db" "SELECT id FROM videos WHERE name = '$name' LIMIT 1")
[ -n "$vid" ] || { echo "no video named $name; videos: $(sqlite3 "$db" 'SELECT name FROM videos' | tr '\n' ' ')" >&2; exit 1; }
for port in 8000 5173; do
  if lsof -iTCP:$port -sTCP:LISTEN -t >/dev/null 2>&1; then echo "port $port is in use" >&2; exit 1; fi
done

mkdir -p outputs/demo
pids=()
stop() {
  for p in "${pids[@]}"; do kill -TERM "$p" 2>/dev/null || true; done
  wait 2>/dev/null || true
}
trap stop EXIT

$py -m uvicorn vball_app.main:app --port 8000 >outputs/demo/api.log 2>&1 &
pids+=($!)
$py -m vball_app.worker --workers 2 >outputs/demo/worker.log 2>&1 &
pids+=($!)
(cd webapp/frontend && exec npx vite --port 5173 --strictPort) >outputs/demo/ui.log 2>&1 &
pids+=($!)

wait_for() {
  for _ in $(seq 60); do curl -fsS "$1" >/dev/null 2>&1 && return 0; sleep 0.5; done
  echo "$2 did not start (see outputs/demo/)" >&2; exit 1
}
wait_for http://127.0.0.1:8000/health "API"
wait_for http://localhost:5173/ "UI"
wait_for "http://localhost:5173/api/videos/$vid/stages" "UI -> API proxy"
for _ in $(seq 60); do grep -q "ready" outputs/demo/worker.log && break; sleep 0.5; done
echo "API, $(grep -c ' ready ' outputs/demo/worker.log) workers and UI are up"

url="http://localhost:5173/videos/$vid"
if [ "$check" = 1 ]; then
  curl -fsS "http://127.0.0.1:8000/videos/$vid/stages" | $py -c "import json,sys; print({s['name']: s['status'] for s in json.load(sys.stdin)})"
  echo "ok: $url"
  exit 0
fi
open "$url"
echo "$name -> $url   (Ctrl-C to stop)"
wait
