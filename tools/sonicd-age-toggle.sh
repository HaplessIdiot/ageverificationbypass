#!/bin/bash
# sonicd-age-toggle — toggle bypassAgeVerification on your user record
# and optionally invoke ageverificationbypass.py for the D-Bus layer
#
# Usage:
#   sonicd-age-toggle.sh on         # bypass on, birthDate hidden (default)
#   sonicd-age-toggle.sh off        # bypass off, birthDate exposed to callers
#   sonicd-age-toggle.sh status     # show current state
#   sonicd-age-toggle.sh spoof      # set birthDate to 1970-01-01 and bypass off
#   sonicd-age-toggle.sh restore    # re-enable bypass, clear birthDate

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AVB_SCRIPT="${AVB_SCRIPT:-${SCRIPT_DIR}/bypassageverification.py}"
TARGET_USER="${TARGET_USER:-$(whoami)}"

require_root() {
    if [[ $EUID -ne 0 ]]; then
        echo "error: this operation requires root (homectl requires admin)" >&2
        echo "       run with: sudo $0 $*" >&2
        exit 1
    fi
}

cmd_status() {
    echo "=== sonicd age verification status ==="
    echo "User: ${TARGET_USER}"
    homectl show "${TARGET_USER}" 2>/dev/null | grep -E "bypassAgeVerification|birthDate" \
        || echo "(no age verification fields set on record)"
    if command -v busctl &>/dev/null; then
        echo ""
        echo "=== D-Bus layer ==="
        busctl call org.freedesktop.AgeVerification1 \
            /org/freedesktop/AgeVerification1 \
            org.freedesktop.AgeVerification1 GetAgeBracket 2>/dev/null \
            && echo "D-Bus age verification: RESPONDING" \
            || echo "D-Bus age verification: NOT RESPONDING (bypass active or not installed)"
    fi
}

cmd_on() {
    require_root "$@"
    echo "Enabling bypass for ${TARGET_USER}..."
    homectl update "${TARGET_USER}" --json-patch='[{"op":"add","path":"/bypassAgeVerification","value":true}]'
    echo "bypassAgeVerification=true — birthDate will not be exposed to callers"
    if [[ -f "${AVB_SCRIPT}" ]]; then
        echo "Running D-Bus layer bypass..."
        python3 "${AVB_SCRIPT}"
    fi
}

cmd_off() {
    require_root "$@"
    echo "Disabling bypass for ${TARGET_USER}..."
    homectl update "${TARGET_USER}" --json-patch='[{"op":"add","path":"/bypassAgeVerification","value":false}]'
    echo "bypassAgeVerification=false — birthDate will be exposed to callers if set"
}

cmd_spoof() {
    require_root "$@"
    echo "Setting birthDate to 1970-01-01 and disabling bypass for ${TARGET_USER}..."
    homectl update "${TARGET_USER}" \
        --json-patch='[
            {"op":"add","path":"/bypassAgeVerification","value":false},
            {"op":"add","path":"/birthDate","value":"1970-01-01"}
        ]'
    echo "birthDate=1970-01-01, bypass=false — callers will see epoch date"
    echo "Use '$0 restore' when done"
}

cmd_restore() {
    require_root "$@"
    echo "Restoring bypass and clearing birthDate for ${TARGET_USER}..."
    homectl update "${TARGET_USER}" \
        --json-patch='[
            {"op":"add","path":"/bypassAgeVerification","value":true},
            {"op":"remove","path":"/birthDate"}
        ]'
    echo "bypassAgeVerification=true, birthDate cleared"
    if [[ -f "${AVB_SCRIPT}" ]]; then
        echo "Running D-Bus layer bypass..."
        python3 "${AVB_SCRIPT}"
    fi
}

case "${1:-}" in
    on)      cmd_on "$@" ;;
    off)     cmd_off "$@" ;;
    status)  cmd_status ;;
    spoof)   cmd_spoof "$@" ;;
    restore) cmd_restore "$@" ;;
    *)
        echo "Usage: $0 {on|off|status|spoof|restore}"
        echo ""
        echo "  on       — enable bypass (default sonicd behavior)"
        echo "  off      — disable bypass, expose birthDate to callers"
        echo "  status   — show current state of record and D-Bus layer"
        echo "  spoof    — set birthDate to 1970-01-01, disable bypass"
        echo "             (use to satisfy services that require a date)"
        echo "  restore  — re-enable bypass, remove birthDate"
        echo ""
        echo "Set TARGET_USER=username to target a different user."
        echo "Set AVB_SCRIPT=/path/to/bypassageverification.py to"
        echo "specify the D-Bus bypass script location."
        exit 1
        ;;
esac
