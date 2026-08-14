#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

if [[ ! -d venv ]]; then
  echo "Creating virtual environment..."
  python3 -m venv venv
  source venv/bin/activate
  pip install -r requirements.txt
else
  source venv/bin/activate
fi

if [[ ! -f contract_watch.db ]]; then
  echo "Seeding sample data..."
  python seed.py
fi

echo ""
echo "Starting Contract Watch..."
echo ""
exec python run.py
