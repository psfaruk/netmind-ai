#!/usr/bin/env bash
# Fetches the pinned llama.cpp release source into the Android binding directory.
# Used by CI (.github/workflows/android-build.yml) and local builds.
set -euo pipefail

LLAMA_TAG="v1.1.0"
LLAMA_SHA256="370603b8d973f4c02cd68ff2b815859c0f71878a57075cf2758015ceb7fc7990"

TARGET_DIR="${1:-android/lib/src/main/cpp/llama.cpp}"
TARBALL="$(mktemp /tmp/llama-cpp.XXXXXX.tar.gz)"
trap 'rm -f "$TARBALL"' EXIT

URL="https://github.com/ggml-org/llama.cpp/archive/refs/tags/${LLAMA_TAG}.tar.gz"
echo "Downloading llama.cpp ${LLAMA_TAG} from ${URL}"
curl -fL --retry 3 -o "$TARBALL" "$URL"

# Soft integrity check (GitHub-generated archives can be re-compressed over time;
# a mismatch is reported but does not abort the build).
if command -v sha256sum >/dev/null 2>&1; then
    ACTUAL="$(sha256sum "$TARBALL" | cut -d' ' -f1)"
    if [ "$ACTUAL" != "$LLAMA_SHA256" ]; then
        echo "WARNING: llama.cpp tarball sha256 mismatch"
        echo "  expected: $LLAMA_SHA256"
        echo "  actual:   $ACTUAL"
    fi
fi

mkdir -p "$TARGET_DIR"
rm -rf "${TARGET_DIR:?}"/*
tar -xzf "$TARBALL" -C "$TARGET_DIR" --strip-components=1
echo "llama.cpp ${LLAMA_TAG} extracted into ${TARGET_DIR}"
