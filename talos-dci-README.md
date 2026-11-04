# DCI lab assets moved to dedicated project

Talos / CLAB DCI service definitions (RouterInterconnect, BridgeDomainInterconnect) live in:

**`C:\Users\darrenri\Documents\eda-dci-lab`**

This repo holds the microsegmentation demos: the WSL `kind` lab catalog (`variants/`) and the Talos #2 build of
tests A–H (`talos/`). The only interconnects owned here are test H's `router-interconnect-ms-dci-1/-2`
(`talos/gen-gate4.py`); the DCI services themselves stay in `eda-dci-lab`.
