#!/usr/bin/env bash
# Build a synthetic diligence target with N small repos.
# Usage: build_synthetic_target.sh <output_dir>
set -euo pipefail
out="${1:?output_dir required}"
mkdir -p "$out"

mk_commit() {
  local repo="$1" name="$2" email="$3" msg="$4" file="$5" content="$6"
  cd "$repo"
  echo "$content" >> "$file"
  git add "$file"
  GIT_AUTHOR_NAME="$name" GIT_AUTHOR_EMAIL="$email" \
  GIT_COMMITTER_NAME="$name" GIT_COMMITTER_EMAIL="$email" \
    git commit -m "$msg" --quiet
  cd - > /dev/null
}

mk_repo() {
  local name="$1"
  local repo="$out/$name"
  mkdir -p "$repo"
  cd "$repo"
  git init --quiet -b main
  git config commit.gpgsign false
  cd - > /dev/null
  echo "$repo"
}

# --- repo: api (production-ish, multiple authors, recent activity) ---
api=$(mk_repo "api")
mk_commit "$api" "Pat Smith" "pat@acme.com" "feat: bootstrap api" main.py "print('hi')"
mk_commit "$api" "Pat Smith" "pat@acme.com" "feat: add auth" auth.py "def login(): pass"
mk_commit "$api" "Pat Smith" "pat@gmail.com"  "feat: add user crud" users.py "def get_user(): pass"
mk_commit "$api" "Mike Brown" "mike@acme.com" "fix: typo" main.py "# fixed"
mk_commit "$api" "Pat Smith" "pat@acme.com" "refactor: split modules" main.py "from auth import *"
mk_commit "$api" "Mike Brown" "mike@acme.com" "feat: add metrics" metrics.py "def emit(): pass"

# --- repo: web (production-ish) ---
web=$(mk_repo "web")
mk_commit "$web" "Daisy Dev" "daisy@acme.com" "feat: bootstrap web" index.html "<html/>"
mk_commit "$web" "Daisy Dev" "daisy@acme.com" "feat: add login page" login.html "<form/>"
mk_commit "$web" "Mike Brown" "mike@acme.com" "fix: layout" index.html "<div/>"

# --- repo: contractor-tool (one-shot contributor pattern) ---
ct=$(mk_repo "contractor-tool")
mk_commit "$ct" "Ext Contractor" "contractor@vendor.com" "feat: tool" tool.py "def run(): pass"
mk_commit "$ct" "Ext Contractor" "contractor@vendor.com" "feat: more tool" tool.py "def run2(): pass"
mk_commit "$ct" "Ext Contractor" "contractor@vendor.com" "feat: finish" tool.py "def run3(): pass"

# --- repo: docs ---
docs=$(mk_repo "docs")
mk_commit "$docs" "Daisy Dev" "daisy@acme.com" "docs: index" README.md "# Acme docs"
mk_commit "$docs" "Daisy Dev" "daisy@acme.com" "docs: install" INSTALL.md "## install"

# --- repo: legacy-old (abandoned) ---
legacy=$(mk_repo "legacy-old")
GIT_COMMITTER_DATE="2019-01-15 12:00:00 +0000" GIT_AUTHOR_DATE="2019-01-15 12:00:00 +0000" \
  mk_commit "$legacy" "Old Engineer" "old@acme.com" "init" main.py "# very old"
GIT_COMMITTER_DATE="2019-03-20 10:00:00 +0000" GIT_AUTHOR_DATE="2019-03-20 10:00:00 +0000" \
  mk_commit "$legacy" "Old Engineer" "old@acme.com" "wip" main.py "# more old"

# --- repo: fork-of-something (fork class) ---
fork=$(mk_repo "vendored-lib")
mk_commit "$fork" "Daisy Dev" "daisy@acme.com" "vendor: import upstream lib at v1.2.3" lib.py "# upstream"
# .fork-of marker — env-var protected to prevent any host git identity leak
( cd "$fork" \
  && echo "fork-of: github.com/upstream/lib" > .fork-of \
  && git add .fork-of \
  && GIT_AUTHOR_NAME="Daisy Dev" GIT_AUTHOR_EMAIL="daisy@acme.com" \
     GIT_COMMITTER_NAME="Daisy Dev" GIT_COMMITTER_EMAIL="daisy@acme.com" \
     git commit -m "meta: mark as fork" --quiet )

echo "Synthetic target built at: $out"
ls "$out"
