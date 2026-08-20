import yaml, pathlib
repo = pathlib.Path("/mnt/c/Users/darrenri/Documents/eda-microsegmentation-demo/variants")
docs = list(yaml.safe_load_all((repo / "edge-interfaces-dot1q.yaml").read_text(encoding="utf-8")))
for d in docs:
    if not d: continue
    n = d.get("metadata", {}).get("name", "")
    if any(x in n for x in ("leaf-5", "leaf-6", "leaf-7")):
        print(n)
