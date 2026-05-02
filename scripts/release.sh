#!/usr/bin/env bash
# One-shot release: bump version in setup.py, commit, tag, push.
# Usage: scripts/release.sh <patch|minor|major|X.Y.Z>
# Examples:
#   scripts/release.sh patch     # 1.5.0 -> 1.5.1
#   scripts/release.sh minor     # 1.5.0 -> 1.6.0
#   scripts/release.sh major     # 1.5.0 -> 2.0.0
#   scripts/release.sh 1.7.3     # explicit
#
# After push, the pypi-publish.yml workflow builds + publishes to PyPI.

set -euo pipefail

if [ $# -ne 1 ]; then
  echo "usage: $0 <patch|minor|major|X.Y.Z>" >&2
  exit 1
fi

cd "$(git rev-parse --show-toplevel)"

# Refuse to release with uncommitted changes (other than setup.py we're about to touch).
if ! git diff-index --quiet HEAD --; then
  echo "error: working tree has uncommitted changes. commit or stash first." >&2
  git status --short >&2
  exit 1
fi

BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$BRANCH" != "main" ] && [ "$BRANCH" != "master" ]; then
  echo "error: must release from main/master, currently on '$BRANCH'." >&2
  exit 1
fi

CURRENT=$(grep -oP '(?<=^    version=")[^"]+' setup.py)
if [ -z "$CURRENT" ]; then
  echo "error: could not parse current version from setup.py" >&2
  exit 1
fi

case "$1" in
  patch|minor|major)
    NEW=$(python3 -c "
import sys
parts = '$CURRENT'.split('.')
major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
bump = '$1'
if bump == 'patch': patch += 1
elif bump == 'minor': minor += 1; patch = 0
elif bump == 'major': major += 1; minor = 0; patch = 0
print(f'{major}.{minor}.{patch}')
")
    ;;
  [0-9]*.[0-9]*.[0-9]*)
    NEW="$1"
    ;;
  *)
    echo "error: '$1' is not patch|minor|major or a valid X.Y.Z version" >&2
    exit 1
    ;;
esac

echo "Releasing: $CURRENT -> $NEW"

# Confirm with the user.
read -r -p "Proceed? [y/N] " confirm
if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
  echo "aborted."
  exit 1
fi

# Update setup.py (single source of truth).
sed -i "s/^    version=\"$CURRENT\",/    version=\"$NEW\",/" setup.py

# Verify the change took.
if ! grep -q "    version=\"$NEW\"," setup.py; then
  echo "error: setup.py update failed; aborting." >&2
  exit 1
fi

# Commit, tag, push.
git add setup.py
git commit -m "Release v$NEW"
git tag "v$NEW"
git push origin "$BRANCH" "v$NEW"

echo ""
echo "Pushed v$NEW. PyPI publish workflow should be running:"
echo "  https://github.com/benteigland11/pypeeker/actions"
