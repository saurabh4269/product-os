#!/usr/bin/env bash
# Idempotent Google Cloud SDK install for Cloud Agent environments.
set -euo pipefail

if command -v gcloud >/dev/null 2>&1; then
  echo "gcloud already installed: $(gcloud version 2>/dev/null | head -1)"
  exit 0
fi

export CLOUDSDK_CORE_DISABLE_PROMPTS=1
TMP="$(mktemp -d)"
curl -fsSL https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-cli-linux-x86_64.tar.gz \
  | tar -xz -C "$TMP"
"$TMP"/google-cloud-sdk/install.sh --quiet --usage-reporting=false --path-update=false
install_dir="$HOME/google-cloud-sdk"
if [[ ! -d "$install_dir" ]]; then
  mv "$TMP"/google-cloud-sdk "$install_dir"
fi
echo "export PATH=\"$install_dir/bin:\$PATH\"" >> "$HOME/.bashrc"
export PATH="$install_dir/bin:$PATH"
gcloud --version | head -1
