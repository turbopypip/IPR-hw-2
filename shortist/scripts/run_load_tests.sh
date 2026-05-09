#!/usr/bin/env bash
set -euo pipefail

HOST="${HOST:-http://127.0.0.1:8000}"
REPORT_ROOT="${REPORT_ROOT:-load_reports}"
RUN_ID="${RUN_ID:-$(date '+%Y-%m-%d_%H-%M-%S')}"

run_locust() {
  if command -v uvx >/dev/null 2>&1; then
    uvx locust "$@"
  else
    locust "$@"
  fi
}

run_case() {
  local test_type="$1"
  local case_name="$2"
  local users="$3"
  local spawn_rate="$4"
  local run_time="$5"

  local out_dir="${REPORT_ROOT}/${test_type}/${RUN_ID}/${case_name}"
  local report_prefix="${out_dir}/locust"
  local console_log="${out_dir}/console.log"

  mkdir -p "${out_dir}"

  cat > "${out_dir}/run_info.txt" <<INFO
test_type=${test_type}
case_name=${case_name}
host=${HOST}
users=${users}
spawn_rate=${spawn_rate}
run_time=${run_time}
started_at=$(date -u '+%Y-%m-%dT%H:%M:%SZ')
INFO

  echo "Running ${test_type}/${case_name}: users=${users}, spawn_rate=${spawn_rate}, run_time=${run_time}"
  run_locust \
    -f locustfile.py \
    --host="${HOST}" \
    --headless \
    -u "${users}" \
    -r "${spawn_rate}" \
    -t "${run_time}" \
    --html "${report_prefix}.html" \
    --csv "${report_prefix}" \
    --only-summary \
    2>&1 | tee "${console_log}"
}

main() {
  local mode="${1:-all}"

  case "${mode}" in
    smoke)
      run_case "smoke" "users_5" 5 5 "5s"
      ;;
    stepped)
      run_case "stepped" "users_10" 10 5 "1m"
      run_case "stepped" "users_25" 25 5 "1m"
      run_case "stepped" "users_50" 50 5 "1m"
      run_case "stepped" "users_100" 100 10 "1m"
      ;;
    all)
      run_case "smoke" "users_5" 5 5 "5s"
      run_case "stepped" "users_10" 10 5 "1m"
      run_case "stepped" "users_25" 25 5 "1m"
      run_case "stepped" "users_50" 50 5 "1m"
      run_case "stepped" "users_100" 100 10 "1m"
      ;;
    *)
      echo "Usage: $0 [smoke|stepped|all]" >&2
      exit 2
      ;;
  esac

  echo "Load test reports written to: ${REPORT_ROOT}"
}

main "$@"
