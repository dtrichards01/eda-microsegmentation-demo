#!/usr/bin/env bash
set -eu
HOST="${EDA_HOST:-https://100.124.186.55}"
USER="${EDA_USER:-admin}"
PASS="${EDA_PASS:-admin}"

tok=$(curl -sk -m 20 -X POST "${HOST}/core/httpproxy/v1/keycloak/realms/eda/protocol/openid-connect/token" \
  -d "grant_type=password" -d "client_id=eda" -d "username=${USER}" -d "password=${PASS}")
echo "$tok" | head -c 300
echo

token=$(python3 -c "import json,sys; print(json.load(sys.stdin).get('access_token',''))" <<<"$tok")
if [ -z "$token" ]; then
  echo "NO_TOKEN"
  exit 1
fi

echo "=== namespaces ==="
curl -sk -m 20 -H "Authorization: Bearer $token" \
  "${HOST}/api/kubernetes/apis/core/v1/namespaces" | python3 -c "
import json,sys
d=json.load(sys.stdin)
for i in d.get('items',[]):
    n=i['metadata']['name']
    if 'srl' in n or 'dcgw' in n or 'clab' in n or 'dci' in n:
        print(n)
"

echo "=== routerinterconnect crd ==="
curl -sk -m 20 -H "Authorization: Bearer $token" \
  "${HOST}/api/kubernetes/apis/apiextensions.k8s.io/v1/customresourcedefinitions/routerinterconnects.services.eda.nokia.com" | head -c 500
echo
