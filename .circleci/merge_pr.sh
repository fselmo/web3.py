#!/usr/bin/env bash

if [[ -n "${CIRCLE_PULL_REQUEST}" ]]; then
  PR_INFO_URL="${CIRCLE_PULL_REQUEST/\/pull\//\/pulls\/}"
  PR_INFO_URL="${PR_INFO_URL/github.com/api.github.com\/repos}"
  echo "Fetching PR info from: $PR_INFO_URL"
  PR_RESPONSE=$(curl -L "$PR_INFO_URL")
  PR_BASE_BRANCH=$(echo "$PR_RESPONSE" | python -c 'import json, sys; obj = json.load(sys.stdin); print(obj.get("base", {}).get("ref", ""))' 2>/dev/null)
  if [[ -z "$PR_BASE_BRANCH" ]]; then
    echo "Could not determine PR base branch from API response: $PR_RESPONSE"
    echo "Skipping merge step."
    exit 0
  fi
  git fetch origin +"$PR_BASE_BRANCH":circleci/pr-base
  # We need these config values or git complains when creating the
  # merge commit
  git config --global user.name "Circle CI"
  git config --global user.email "circleci@example.com"
  git merge --no-edit circleci/pr-base
fi
