import yaml, pathlib
repo = pathlib.Path(r"/mnt/c/Users/darrenri/Documents/eda-microsegmentation-demo/variants")

def pick(file, names):
    docs = []
    for d in yaml.safe_load_all(pathlib.Path(file).read_text(encoding="utf-8")):
        if d and d.get("metadata", {}).get("name") in names:
            docs.append(d)
    return docs

vn = pick(repo / "virtualnetworks.yaml", {"vnet-ms-routed"})[0]
assoc = pick(repo / "association-policies.yaml", {"ms-assoc-routed"})[0]
msp = pick(repo / "microsegmentation-policies.yaml", {"ms-policy-routed"})[0]
out = repo / "_variant-c-apply.yaml"
out.write_text("---\n".join(yaml.dump(d, sort_keys=False) for d in [vn, assoc, msp]), encoding="utf-8")
print("wrote", out)
