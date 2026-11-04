"""Write talos/fix-c-policy.yaml: only ms-policy-routed from gate2-pod1-acd.yaml (regenerate gate 2 first)."""
import json
import pathlib

HERE = pathlib.Path(__file__).parent
docs = [json.loads(d) for d in HERE.joinpath("gate2-pod1-acd.yaml").read_text(encoding="utf-8").split("\n---\n")[1:]]
pol = [d for d in docs if d["kind"] == "MicroSegmentationPolicy" and d["metadata"]["name"] == "ms-policy-routed"]
HERE.joinpath("fix-c-policy.yaml").write_text(
    "# Test C fix: ms-policy-routed without the default deny entry.\n---\n" + json.dumps(pol[0], indent=2) + "\n",
    encoding="utf-8")
print([e["description"] for e in pol[0]["spec"]["entries"]])
