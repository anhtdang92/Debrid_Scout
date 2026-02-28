#!/bin/bash
# Branch cleanup script for Debrid Scout
# All branches verified safe to delete — no unique code will be lost.

set -e

echo "=== Deleting 3 merged Claude branches ==="
git push origin --delete \
  claude/index-and-push-main-YyBMu \
  claude/index-project-docs-Bh9OS \
  claude/index-project-docs-KC4Y9

echo ""
echo "=== Deleting 1 unmerged Claude branch (older CLAUDE.md, superseded by main) ==="
git push origin --delete claude/index-project-docs-1mbiz

echo ""
echo "=== Deleting 13 Dependabot branches (single-line version bumps, will be recreated) ==="
git push origin --delete \
  dependabot/docker/python-3.14-slim \
  dependabot/github_actions/actions/checkout-6 \
  dependabot/github_actions/actions/setup-node-6 \
  dependabot/github_actions/actions/setup-python-6 \
  dependabot/npm_and_yarn/eslint-10.0.2 \
  dependabot/npm_and_yarn/eslint/js-10.0.1 \
  dependabot/npm_and_yarn/globals-17.3.0 \
  dependabot/npm_and_yarn/lint-staged-16.2.7 \
  dependabot/npm_and_yarn/shx-0.4.0 \
  dependabot/pip/flask-approx-eq-3.1.3 \
  dependabot/pip/flask-wtf-approx-eq-1.2.2 \
  dependabot/pip/gunicorn-approx-eq-25.1 \
  dependabot/pip/pytest-approx-eq-9.0 \
  dependabot/pip/pytest-mock-approx-eq-3.15 \
  dependabot/pip/python-dotenv-approx-eq-1.2.1 \
  dependabot/pip/responses-approx-eq-0.26

echo ""
echo "=== Pruning local tracking refs ==="
git fetch --prune

echo ""
echo "=== Done! Deleted 17 stale branches. Only 'main' remains. ==="
git branch -r
