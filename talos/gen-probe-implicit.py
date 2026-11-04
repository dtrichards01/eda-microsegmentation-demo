"""Write the implicit-default probe for test G: ms-policy-enf-bd without "allow blue to/from green"
and without "default deny" (probe-g-no-bluegreen.yaml) and the unchanged policy to put back (probe-g-restore.yaml)."""
import copy
import json
import pathlib

HERE = pathlib.Path(__file__).parent
docs = [json.loads(d) for d in HERE.joinpath("gate3-pod2-befg.yaml").read_text(encoding="utf-8").split("\n---\n")[1:]]
orig = next(d for d in docs if d["kind"] == "MicroSegmentationPolicy" and d["metadata"]["name"] == "ms-policy-enf-bd")
probe = copy.deepcopy(orig)
probe["spec"]["entries"] = [e for e in probe["spec"]["entries"]
                            if e["description"] not in ("allow blue to/from green", "default deny")]
for name, doc, note in (("probe-g-no-bluegreen.yaml", probe, "G probe: no blue<->green rule, no default deny"),
                        ("probe-g-restore.yaml", orig, "G probe restore: original policy")):
    HERE.joinpath(name).write_text(f"# {note}\n---\n" + json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    print(name, [e["description"] for e in doc["spec"]["entries"]])
