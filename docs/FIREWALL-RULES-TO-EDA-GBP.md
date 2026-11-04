# Palo Alto rules and the EDA / SR Linux microsegmentation model

How a Palo Alto security rule maps onto EDA microsegmentation (GroupTag, AssociationPolicy,
MicroSegmentationPolicy) and SR Linux group-based policy (GBP), and what the firewall app
`firewall.eda.labs` does with each part of a rule. Checked on Talos #2 on 2026-11-04 against the installed
Microsegmentation CRDs (`microsegmentation.eda.nokia.com/v1alpha1`), SR Linux 26.7.1 on 7220 IXR-D2L, and
the firewall app v1.8.2 source (`Projects/eda-fw-integration/firewall/internal/policy`).

Related: `EDA-Microsegmentation.md` (variants A–H and how classification works), and the firewall app's
`firewall/docs/POLICY-GATES.md` (how a rule becomes a policy, and the checklist gates).

## 1. The core difference: a firewall names hosts, the fabric names attachments

| | Palo Alto | EDA / SR Linux |
|---|---|---|
| How an endpoint gets an identity | By **address**: an address object (`ip-netmask`, `ip-range`, `ip-wildcard`, `fqdn`), a static address group, or a dynamic address group whose members are registered IPs | By **where it attaches**: the GroupTag is set on a VLAN, BridgeInterface, RoutedInterface or IRBInterface, or on a StaticRoute prefix (AssociationPolicy `associationTargets`) |
| Can one IP get a tag? | Yes, a `/32` address object | **No.** There is no IP-to-tag or MAC-to-tag setting in EDA or in SR Linux |
| Can one MAC get a tag? | Not used in security rules | **No.** The MAC table's `group-based-policy-tag` is learned state, copied from the tag of the subinterface the MAC was learned on |
| What a rule matches | Zones, source and destination addresses, users, applications, services, URL categories, HIP | Source GroupTag, destination GroupTag, IP version, protocol, source and destination port, TCP flags |
| Default | The rulebase ends in an explicit or implicit deny | **No implicit deny.** Unmatched traffic is forwarded unless the policy ends in a `match: {}` Drop entry |

Proof from the live model:

- **AssociationPolicy** targets are only `vlans`, `bridgeInterfaces`, `routedInterfaces`, `irbInterfaces`, `staticRoutes`, and their label-selector forms. There is no field for an IP address, a prefix outside a static route, or a MAC.
- **SR Linux 26.7.1** sets a group in configuration in only two places:
  - `network-instance <ni> group-based-policy interface <subif> group` (per subinterface);
  - `network-instance <ni> static-routes route <prefix> group-based-policy group` (per static route).
  
  Everything else is state learned from those: the MAC table tag, the ARP and ND neighbour tag, and the route-table tag. The EVPN and BGP `gbp-tag` community (`add-community`, `install-from-community`) only carries a learned tag to other leaves. It never creates one.

So the fabric's unit of identity is "everything behind this attachment". A firewall group is only enforceable in the fabric if it names exactly the hosts behind one or more attachments.

## 2. Element-by-element mapping

"App today" is what firewall app v1.8.2 does, with the reason code it puts on the FirewallPolicyReport.

| Palo Alto element | Closest EDA / SR Linux construct | App today | Gap |
|---|---|---|---|
| Rule tag `eda-export-to-gbp` | None. Selects which rules are exported | Only tagged rules are read | None |
| Source / destination **zone** | Roughly the service: `serviceTargets` (virtual networks, routers, bridge domains) | Recorded on the report (`from`, `to`), not translated. The policy targets the virtual networks where the GroupTags are associated | Zones and services are not the same thing. A zone can span several VNETs, and a VNET several zones |
| **Static address group** | **GroupTag**, same name in lower case (`EDA-RED` to `eda-red`) | Derived GroupTag. Placement comes from the operator's AssociationPolicies | None, as long as the group matches attachments (see section 3) |
| **Dynamic address group** (tag filter; registered IPs) | GroupTag | Members are the firewall's runtime registered IPs, each checked like a static member | Membership is dynamic on the firewall but fixed configuration in EDA. EDA cannot follow a host that is re-tagged on the firewall |
| Address object `ip-netmask` **/32** (one host) | **None for a single host.** The only per-host tool is a StaticRoute `/32` with a group, which is untested (see section 4) | Accepted as a member if it lies inside an IRB subnet of the GroupTag's attachment. Otherwise MEMBER_OUTSIDE_TAG_TARGETS, UNMANAGED_MEMBER or AMBIGUOUS_SCOPE | **The fabric tags the whole attachment, not the one host.** Section 3 |
| Address object `ip-netmask` subnet (`/24` etc.) | StaticRoute prefix with a group (variant E), for prefixes reached through a next hop; or a whole VLAN if the subnet is the IRB subnet | PREFIX_MEMBER_NOT_IN_V1 | Not translated in v1 |
| Address object `ip-range`, `ip-wildcard`, `fqdn` | None | MEMBER_TYPE_NOT_IN_V1 | No equivalent |
| Address object used directly in a rule (not in a group) | None | UNCONTROLLED_IDENTITY | Use a group |
| `any` source or destination | An entry with no `sourceGroupTag` or `destinationGroupTag` matches every group | ANY_SOURCE / ANY_DESTINATION (refused on purpose, so a firewall `any` never becomes a fabric-wide allow) | Policy choice, not a model gap |
| Several groups on one side | `sourceGroupTag` and `destinationGroupTag` are lists in the CRD | MULTIPLE_SOURCE_OBJECTS / MULTIPLE_DESTINATION_OBJECTS (v1 is one group to one group) | App limit, could be lifted |
| Negated source or destination | None | NEGATED_SOURCE / NEGATED_DESTINATION | No equivalent |
| IPv6 | `ipVersion: IPv6` exists | ADDRESS_FAMILY_NOT_IN_V1 | App limit |
| **Service** `tcp`/`udp` port, range, source port; service groups | `protocolName`, `destinationPortNumber` / `destinationPortRange` / `destinationPortOperator`, the same for source ports | Translated: one entry per port, groups expanded | None |
| Service `any` | Entry with no protocol or port | Translated as any | None |
| Service `application-default` | None (needs App-ID) | NGFW_REQUIRED (APP_DEFAULT_SERVICE) | No equivalent |
| Other IP protocols (ICMP, GRE, ESP) | `protocolName` / `protocolNumber` exist | UNSUPPORTED_PROTOCOL | App limit (v1 is TCP/UDP only) |
| Application (App-ID) | None | NGFW_REQUIRED (APP_ID) | Stays on the firewall |
| User-ID, URL category, HIP, security profiles | None | NGFW_REQUIRED | Stays on the firewall |
| Action `allow` | `action.forward: Accept` | Translated | None |
| Action `deny`, `drop` | `action.forward: Drop` | Translated | None |
| Action `reset-client`, `reset-server`, `reset-both` | None (GBP can only accept or drop) | UNSUPPORTED_ACTION | No equivalent |
| Rule type `intrazone`, `interzone` | None | RULE_TYPE_NOT_IN_V1 | Only `universal` |
| Schedule | None | SCHEDULED | No equivalent |
| Disabled rule | None | Not translated | None |
| Log at session end, log forwarding | `action.log`, `action.collectStats` per entry | Not set: derived entries carry only the forward action | Could map `log-end` to `log` |
| Rule order, first match wins | Entry order, first match wins | Kept: one ordered `fw-<firewall>` policy | None |
| Final deny, or the rulebase's implicit deny | An explicit `match: {}` Drop entry, last | **Not exported.** The fabric stays allow-by-default for everything the policy does not name | The default deny belongs to the Microsegmentation app (gate F) |
| Direction and return traffic | `bidirectional` per entry (CRD default true) | Accept entries are bidirectional and Drop entries one way (`derive.go`), as on the live `fw-palo-alto` | PAN rules are one way with stateful return. GBP is stateless, so an allow must cover both directions, while a one-way drop matches the firewall rule |

## 3. The IP gap in practice: a /32 member widens to the whole attachment

The firewall app validates in **one direction only**. Every member of the firewall group must sit inside an IRB subnet of the GroupTag's attachment (`identity.go`, `inTargets`). It does **not** check the reverse: that the attachment holds no other hosts. It can't, because EDA has no per-host identity to compare against.

Live example (dcgw lab, 2026-11-02):

| Palo Alto | EDA |
|---|---|
| `EDA-RED` = address object `10.31.1.10/32` (`fw-client-pan-inside`) | GroupTag `eda-red` associated with VLAN `fw-pan-inside` |

Today `10.31.1.10` is the only host on `fw-pan-inside`, so firewall and fabric agree. If a second host, say `10.31.1.11`, is cabled into that VLAN, the leaf tags it `eda-red` as well. The Palo Alto still treats it as not RED. The fabric would then apply `eda-red to eda-blue TCP 80/443 Accept` and `eda-red to eda-green Drop` to a host the firewall rule never named. The report still shows the group RESOLVED.

What this means for policy:

- **A derived Accept can grant more than the firewall granted.** It is only safe while every host behind the attachment is a member of the group.
- **A derived Drop can block more than the firewall blocked.**
- **The reverse case:** a host the firewall adds to `EDA-RED`, but which sits on another attachment, is reported as MEMBER_OUTSIDE_TAG_TARGETS. The group is then left untranslated rather than silently mis-tagged. That direction is safe.

**Design rule that makes the two models agree:** give each security group its own attachment, meaning its own VLAN, bridge interface or routed interface. Define the firewall group as exactly the hosts on that attachment, ideally the IRB subnet itself. The fabric and the firewall then name the same set of hosts by construction. This is how the lab is built: one client per zone VLAN.

## 4. What exists between "one attachment" and "one IP"

| Mechanism | Granularity | Validated | Limits |
|---|---|---|---|
| VLAN / BridgeInterface / RoutedInterface / IRB association | Every host behind the subinterface | Yes, variants A–D, F–H | Per attachment only |
| StaticRoute association with a prefix | Traffic **to** the prefix, in an L3 service | Yes for `/24` (variant E) | Routed traffic only. Only the destination is classified. If the packet is routed to a next hop and then bridged, the source tag is lost and a default deny drops it (test report §0.5) |
| StaticRoute `/32` for one host | Destination tag for that one IP, routed traffic only | **No** | Not tested. It would override the host's EVPN `/32`, and it does nothing for bridged traffic in the same subnet or for the host as a source on its own leaf (source tags there come from the MAC table) |
| Learned host routes with the `gbp-tag` community (`hostRoutePopulate.dynamic`, ARP/ND) | One `/32` per host, carried between leaves and across the DCI | Yes (variant H) | The tag is copied from the host's attachment. It is distribution, not classification |

## 5. Authoring guidance for rules exported to EDA

A rule tagged `eda-export-to-gbp` is a contract. It should only use what the fabric can enforce exactly. Since firewall app v1.8.3 the app enforces the identity part of the contract (section 5.3). Rules that break it are not refused on the firewall: they keep working there, and the FirewallPolicyReport shows them rejected with the reason. The report is the check that the guidance was followed.

### 5.1 Identity: a group is one subnet, and the subnet is one tag

| Do | Why |
|----|-----|
| Name the group exactly as its GroupTag, in **lower case** (`eda-red`, not `EDA-RED`) | Names are not translated. An upper-case group name rejects every rule that uses it (GROUP_NAME_NOT_LOWERCASE) |
| Make each group hold **one address object per subnet**, and set that object to **the IRB subnet** of a bridge domain (`10.31.1.0/24` for `fw-pan-inside`), or to the subnet of a routed interface | Every host in the subnet is behind that bridge domain's attachments, so "the subnet" and "the hosts the fabric tags" are the same set |
| Associate the GroupTag with **every** attachment (VLAN, bridge interface) of that bridge domain | If one VLAN in the bridge domain carries another tag, or none, the subnet is split and no single tag equals it |
| Use one bridge domain or routed subnet per security group | The variant A design (one shared subnet, three VLANs in three colours) cannot be written as a subnet rule. Each colour there is a set of VLANs, not a prefix |
| Several subnets in one group are fine, if each one follows the rows above | The GroupTag is associated with the attachments of every subnet |
| Do not use `/32` host objects | A `/32` would tag the whole attachment (section 3), so it is rejected (HOST_MEMBER_NOT_SUPPORTED) |
| Avoid dynamic address groups for exported rules | Runtime membership cannot follow into EDA, and registered IPs are `/32`s |
| Use IPv4 `ip-netmask` objects only | Ranges, wildcards, FQDNs and IPv6 are not translated in v1 |

The IRB gateway address lies inside the subnet, but it does not need to match. Traffic to the gateway is extracted to the CPU and is not filtered by group-based policy.

### 5.2 Rule shape

| Field | Use | Not translated if |
|-------|-----|-------------------|
| Source, destination | Exactly one address group each | `any`, several objects, an address object instead of a group, negation |
| Application | `any` | Any App-ID (stays NGFW_REQUIRED) |
| Service | `any`, or TCP/UDP services and service groups with ports or ranges | `application-default`, other protocols (v1) |
| User, URL category, HIP, profiles | none | any set (NGFW_REQUIRED) |
| Action | `allow`, `deny`, `drop` | `reset-*` |
| Rule type | `universal` | `intrazone`, `interzone` |
| Schedule | none | any schedule |
| Zones | Free. Not translated. The policy applies where the GroupTags are associated | — |
| Order | Exported rules above the rules that are not exported, with no non-exported rule in between that overlaps them | An earlier, overlapping rule of the other action class (PRECEDENCE_AMBIGUOUS) |
| Final deny | Do not rely on it in the fabric | It is never exported. Add a `match: {}` Drop to the policy on the EDA side if the fabric must default-deny |

### 5.3 What the app enforces (firewall app v1.8.3)

| Element | Accepted when | Otherwise |
|---------|---------------|-----------|
| Group name | It is all lower case and a valid GroupTag name; it maps to the GroupTag of exactly that name | GROUP_NAME_NOT_LOWERCASE: no GroupTag is derived and every rule using the group is rejected (UNSUPPORTED, no candidate). GROUPTAG_NAME_INVALID for other bad names |
| Prefix member | It **equals** the IRB subnet of a bridge domain, or the subnet of a routed interface | SUBNET_NOT_ATTACHMENT (overlaps a subnet without equalling it), UNMANAGED_MEMBER (outside every subnet), AMBIGUOUS_SCOPE (equal to subnets in two virtual networks) |
| Attachments of that subnet | Every VLAN and bridge interface of the bridge domain, or the routed interface, carries this group's GroupTag and no other | MEMBER_OUTSIDE_TAG_TARGETS (none carry it), SUBNET_SPLIT_ACROSS_TAGS (one carries no tag, or another tag too) |
| `/32` member, including a DAG registered IP | Never | HOST_MEMBER_NOT_SUPPORTED |

An AssociationPolicy on `routedInterfaces` is now a checked target. Selector and static-route targets still block the group.

The lab Palo Alto follows this since 2026-11-02: static groups `eda-red`, `eda-blue` and `eda-green` hold `10.31.1.0/24`, `10.31.2.0/24` and `10.21.1.0/24`, and RED to BLUE and RED to GREEN use them and translate (3 entries). `EDA-RED-to-SECURE-ALLOW` still names `EDA-RED` and `EDA-SECURE` and is shown rejected with GROUP_NAME_NOT_LOWERCASE. A `/32` would only be safe where the host has an attachment to itself, which needs the learned-host check (ATTACHMENT_WIDER_THAN_GROUP, section 6) before it can be accepted.

## 6. Gaps to close, and who owns them

| Gap | Owner | Proposal |
|---|---|---|
| No per-IP or per-MAC classification (an endpoint or prefix to GroupTag) | Nokia (EDA Microsegmentation app, SR Linux GBP) | Feature request: an AssociationPolicy target for host IPs or prefixes and MACs, programmed as SR Linux static group assignments |
| Attachment wider than the firewall group (section 3) | Firewall app | New check: read the learned hosts on each tagged attachment (ARP/ND and MAC table through EQL). Flag ATTACHMENT_WIDER_THAN_GROUP and do not translate while a host behind it is not a firewall member |
| Dynamic address group membership changes | Firewall app, then the Nokia feature above | Report the drift today. Only per-IP classification can follow it |
| Subnet members equal to an IRB or routed subnet, lower-case group names, no `/32` (section 5.3) | Firewall app | Done in v1.8.3 |
| IPv6, more protocols, several groups per side, `log-end` | Firewall app | Profile extensions (`microseg-1to1` v2). The EDA model already has the fields |
| Zero-trust tail (the firewall's final deny) | Microsegmentation app operator (gate F) | Add an explicit `match: {}` Drop as the last entry. Note variant E's caveat |
| App-ID, User-ID, URL, HIP, profiles, reset actions, schedules | Stays on the firewall | Traffic that needs them must keep crossing the firewall (NGFW_REQUIRED) |
