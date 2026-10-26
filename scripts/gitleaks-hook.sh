#!/usr/bin/env bash
# Pre-commit hook: scan staged changes for secrets with gitleaks.
#
# Uses `gitleaks` from PATH if it is installed. Otherwise downloads the pinned
# release binary from GitHub once, verifies its SHA-256 checksum and caches it.
# This works without a Go toolchain, so the hook also runs in cloud sessions.
set -euo pipefail

VERSION="8.30.1"

# SHA-256 checksums from the official release (gitleaks_${VERSION}_checksums.txt).
checksum_for() {
  case "$1" in
    linux_x64)    echo "551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb" ;;
    linux_arm64)  echo "e4a487ee7ccd7d3a7f7ec08657610aa3606637dab924210b3aee62570fb4b080" ;;
    darwin_x64)   echo "dfe101a4db2255fc85120ac7f3d25e4342c3c20cf749f2c20a18081af1952709" ;;
    darwin_arm64) echo "b40ab0ae55c505963e365f271a8d3846efbc170aa17f2607f13df610a9aeb6a5" ;;
    *)            echo "" ;;
  esac
}

sha256_of() {
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$1" | awk '{print $1}'
  else
    shasum -a 256 "$1" | awk '{print $1}'
  fi
}

find_gitleaks() {
  if command -v gitleaks >/dev/null 2>&1; then
    command -v gitleaks
    return
  fi

  local os arch platform expected cache_dir bin tmp
  case "$(uname -s)" in
    Linux)  os="linux" ;;
    Darwin) os="darwin" ;;
    *)      os="unsupported" ;;
  esac
  case "$(uname -m)" in
    x86_64 | amd64)  arch="x64" ;;
    arm64 | aarch64) arch="arm64" ;;
    *)               arch="unsupported" ;;
  esac
  platform="${os}_${arch}"
  expected="$(checksum_for "$platform")"
  if [[ -z "$expected" ]]; then
    echo "gitleaks: no pinned binary for $(uname -s)/$(uname -m)." >&2
    echo "Install gitleaks manually: https://github.com/gitleaks/gitleaks#installing" >&2
    exit 1
  fi

  cache_dir="${XDG_CACHE_HOME:-$HOME/.cache}/travelaiagent/gitleaks/${VERSION}"
  bin="${cache_dir}/gitleaks"
  if [[ ! -x "$bin" ]]; then
    echo "gitleaks: downloading v${VERSION} (${platform}) into ${cache_dir}" >&2
    mkdir -p "$cache_dir"
    tmp="$(mktemp -d)"
    trap 'rm -rf "$tmp"' EXIT
    curl -fsSL -o "${tmp}/gitleaks.tar.gz" \
      "https://github.com/gitleaks/gitleaks/releases/download/v${VERSION}/gitleaks_${VERSION}_${platform}.tar.gz"
    if [[ "$(sha256_of "${tmp}/gitleaks.tar.gz")" != "$expected" ]]; then
      echo "gitleaks: checksum mismatch, refusing to run the downloaded binary." >&2
      exit 1
    fi
    tar -xzf "${tmp}/gitleaks.tar.gz" -C "$tmp" gitleaks
    install -m 0755 "${tmp}/gitleaks" "$bin"
  fi
  echo "$bin"
}

GITLEAKS="$(find_gitleaks)"
exec "$GITLEAKS" git --pre-commit --redact --staged --verbose
