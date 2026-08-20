#!/usr/bin/env python3
"""Probe remote EDA and list fabric resources."""
import json
import os
import urllib.parse
import urllib.request

HOST = os.environ.get("EDA_HOST", "https://100.124.186.55").rstrip("/")
USER = os.environ.get("EDA_USER", "admin")
PASS = os.environ.get("EDA_PASS", "admin")


def post_token():
    data = urllib.parse.urlencode(
        {
            "grant_type": "password",
            "client_id": "eda",
            "username": USER,
            "password": PASS,
        }
    ).encode()
    url = f"{HOST}/core/httpproxy/v1/keycloak/realms/eda/protocol/openid-connect/token"
    req = urllib.request.Request(url, data=data, method="POST")
    with urllib.request.urlopen(req, context=__import__("ssl")._create_unverified_context(), timeout=30) as r:
        return json.load(r)["access_token"]


def get(token: str, path: str):
    url = f"{HOST}{path}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, context=__import__("ssl")._create_unverified_context(), timeout=30) as r:
        return json.load(r)


def main():
    token = post_token()
    print("TOKEN_OK")
    ns = get(token, "/api/kubernetes/apis/core/v1/namespaces")
    names = [i["metadata"]["name"] for i in ns.get("items", [])]
    for n in sorted(names):
        if any(x in n for x in ("srl", "dcgw", "clab", "dci", "leaf", "spine")):
            print("NS", n)

    for ns in names:
        if "srl-leaf-spine" in ns or ns == "srl-leaf-spine-dcgw":
            print(f"=== routers in {ns} ===")
            try:
                routers = get(
                    token,
                    f"/api/kubernetes/apis/services.eda.nokia.com/v1/namespaces/{ns}/routers",
                )
                for r in routers.get("items", []):
                    print(r["metadata"]["name"], r.get("status", {}).get("operationalState"))
            except Exception as e:
                print("routers err", e)
            print(f"=== existing routerinterconnects in {ns} ===")
            try:
                ris = get(
                    token,
                    f"/api/kubernetes/apis/services.eda.nokia.com/v1/namespaces/{ns}/routerinterconnects",
                )
                print(json.dumps(ris, indent=2)[:8000] if ris.get("items") else "none")
            except Exception as e:
                print("ri err", e)


if __name__ == "__main__":
    main()
