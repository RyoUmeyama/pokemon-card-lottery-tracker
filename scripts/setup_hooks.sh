#!/bin/bash
echo "Setting up git hooks..."
cd "$(git rev-parse --show-toplevel)"
git config core.hooksPath .githooks
chmod +x .githooks/pre-push
echo "✅ Git hooks configured. Pre-push test hook is now active."
