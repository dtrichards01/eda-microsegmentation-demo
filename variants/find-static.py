import yaml, subprocess
d = yaml.safe_load(subprocess.check_output(["kubectl", "get", "crd", "virtualnetworks.services.eda.nokia.com", "-o", "yaml"]))
schema = d["spec"]["versions"][0]["schema"]["openAPIV3Schema"]["properties"]["spec"]["properties"]

def find(obj, key, path="spec"):
    if isinstance(obj, dict):
        if key in obj:
            print(path + "." + key)
        for k, v in obj.items():
            find(v, key, path + "." + k)

find(schema, "staticRoutes")
