"""Write talos/default-deny-cf.yaml: the C and F policies (with default deny) from the gate 2 and 3 files.
Regenerate those first; apply only after every leaf has lpm-source-lookup active (scripts/leaf-reboot.sh).
E keeps no default deny (see gen-gate3.py)."""
import json
import pathlib

HERE = pathlib.Path(__file__).parent
WANT = ("ms-policy-routed", "ms-policy-enf-router")
docs = [json.loads(d) for f in ("gate2-pod1-acd.yaml", "gate3-pod2-befg.yaml")
        for d in HERE.joinpath(f).read_text(encoding="utf-8").split("\n---\n")[1:]]
pols = [d for d in docs if d["kind"] == "MicroSegmentationPolicy" and d["metadata"]["name"] in WANT]
assert len(pols) == len(WANT)
HERE.joinpath("default-deny-cf.yaml").write_text(
    "# Restore the default deny entry on tests C and F.\n"
    + "".join("---\n" + json.dumps(p, indent=2) + "\n" for p in pols), encoding="utf-8")
for p in pols:
    print(p["metadata"]["name"], [e["description"] for e in p["spec"]["entries"]][-1])
