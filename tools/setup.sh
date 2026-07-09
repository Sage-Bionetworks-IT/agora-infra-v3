#!/usr/bin/env bash

# Safer bash scripts
set -euxo pipefail

# Install uv (pinned version + SHA256-verified binary). Skipped if already installed.
if ! command -v uv >/dev/null; then
  UV_VERSION="0.11.7"
  case "$(uname -s)-$(uname -m)" in
    Linux-x86_64)
      UV_TARBALL="uv-x86_64-unknown-linux-gnu.tar.gz"
      UV_SHA256="6681d691eb7f9c00ac6a3af54252f7ab29ae72f0c8f95bdc7f9d1401c23ea868"
      ;;
    Linux-aarch64)
      UV_TARBALL="uv-aarch64-unknown-linux-gnu.tar.gz"
      UV_SHA256="f2ee1cde9aabb4c6e43bd3f341dadaf42189a54e001e521346dc31547310e284"
      ;;
    *)
      echo "No pinned uv binary for $(uname -s)-$(uname -m)."
      echo "Install uv manually: https://docs.astral.sh/uv/getting-started/installation/"
      exit 1
      ;;
  esac
  UV_TMP="$(mktemp -d)"
  trap 'rm -rf "$UV_TMP"' EXIT
  curl -fsSL -o "$UV_TMP/$UV_TARBALL" \
    "https://github.com/astral-sh/uv/releases/download/$UV_VERSION/$UV_TARBALL"
  echo "$UV_SHA256  $UV_TMP/$UV_TARBALL" | sha256sum -c -
  tar -xzf "$UV_TMP/$UV_TARBALL" -C "$UV_TMP" --strip-components=1
  mkdir -p "$HOME/.local/bin"
  install -m 755 "$UV_TMP/uv" "$HOME/.local/bin/uv"
  install -m 755 "$UV_TMP/uvx" "$HOME/.local/bin/uvx"
  export PATH="$HOME/.local/bin:$PATH"
fi

# Install Node.js dependencies
npm install -g aws-cdk@2.1007.0 --ignore-scripts

# Install Python dependencies (creates .venv, installs from uv.lock)
uv sync

# Install git hooks
git config --global --add safe.directory "$PWD"
uv run pre-commit install --install-hooks
