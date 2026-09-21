#!/bin/sh
# Print the FMAPI bearer token from the file the backend keeps fresh.
# Backend refreshes ./.anthropic_token every ~15 min — see core/fmapi_auth.py.
cat "$(dirname "$0")/.anthropic_token"
