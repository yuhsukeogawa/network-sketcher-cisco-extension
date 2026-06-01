"""Map CML topology + parsed configs → Network Sketcher topology model.

Outputs a plain-dict model (`build_ns_model`) that the command builder
serialises into NS CLI commands. The model is also written to
``artifacts/ns_model.json`` for human review.

Layout policy (RULE 0):
  row 0 = WAN / Internet / waypoint clouds
  row 1 = BGW / Border / Firewall
  row 2 = Spine
  row 3 = Leaf / Distribution / Aggregation
  row 4 = Access
  row 5 = Endpoint / Host / Server / PC / IoT

Area policy (RULE 3):
  - Group nodes by shared CML "site" tag (e.g. site1, site2, wan-isn).
  - If a node has multiple site-like tags, prefer the most-specific one (`site*`).
  - WAN / inter-site fabric is its own waypoint area (`*_wp_`).
  - Nodes with no usable tag fall into the catch-all area `default`.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from .stencil_mapper import (
    NS_AP, NS_CLOUD, NS_FIREWALL, NS_L3SWITCH, NS_PC, NS_ROUTER,
    NS_SERVER, NS_SWITCH, NS_WLC, StencilMapping,
)


# ---------------------------------------------------------------------------
# Data classes (intermediate NS model)
# ---------------------------------------------------------------------------

@dataclass
class NSDevice:
    name: str
    area: str
    row: int
    stencil: StencilMapping
    is_endpoint: bool
    routing_attribute: str = ""    # free-text BGP/OSPF/EVPN summary (RULE 11.5 + Attribute-D)


@dataclass
class NSL1Link:
    a_device: str
    a_port: str
    b_device: str
    b_port: str


@dataclass
class NSVirtualPort:
    device: str
    port: str                       # 'Vlan 100', 'Loopback 0', 'Port-channel 10'
    is_loopback: bool = False
    vlan_id: Optional[int] = None   # for SVIs


@dataclass
class NSIPAssignment:
    device: str
    port: str
    cidrs: List[str]


@dataclass
class NSL2Segment:
    device: str
    port: str                       # physical L1 port, or SVI for self-binding (RULE 15)
    vlans: List[str]                # ['Vlan100', 'Vlan200']


@dataclass
class NSPortChannel:
    device: str
    physical_ports: List[str]
    portchannel_name: str           # 'Port-channel 10'


@dataclass
class NSModel:
    areas: List[List[str]] = field(default_factory=list)            # area layout 2-D grid
    area_to_devices: Dict[str, List[List[str]]] = field(default_factory=dict)  # area -> 2-D device grid (rows)
    devices: Dict[str, NSDevice] = field(default_factory=dict)
    l1_links: List[NSL1Link] = field(default_factory=list)
    virtual_ports: List[NSVirtualPort] = field(default_factory=list)
    ip_assignments: List[NSIPAssignment] = field(default_factory=list)
    l2_segments_phys: List[NSL2Segment] = field(default_factory=list)  # L2 on physical ports
    l2_segments_svi: List[NSL2Segment] = field(default_factory=list)   # SVI self-binding (RULE 15)
    port_channels: List[NSPortChannel] = field(default_factory=list)
    vrf_renames: List[Tuple[str, str, str]] = field(default_factory=list)  # (device, port, vrf)


# ---------------------------------------------------------------------------
# Port-name normalisation (CML → NS conventions, with spaces)
# ---------------------------------------------------------------------------

_IFACE_TYPE_PATTERNS = [
    # Order matters: long-form first so 'eth0' doesn't beat 'Ethernet1/1'.
    (re.compile(r"^GigabitEthernet", re.IGNORECASE), "GigabitEthernet"),
    (re.compile(r"^TenGigabitEthernet", re.IGNORECASE), "TenGigabitEthernet"),
    (re.compile(r"^TwentyFiveGigE", re.IGNORECASE), "TwentyFiveGigE"),
    (re.compile(r"^FortyGigabitEthernet", re.IGNORECASE), "FortyGigabitEthernet"),
    (re.compile(r"^HundredGigE", re.IGNORECASE), "HundredGigE"),
    (re.compile(r"^FastEthernet", re.IGNORECASE), "FastEthernet"),
    (re.compile(r"^Ethernet", re.IGNORECASE), "Ethernet"),
    # Linux-style 'eth0', 'eth1' (alpine / generic Linux host NIC names) -> NS 'Ethernet 0'.
    (re.compile(r"^eth\d", re.IGNORECASE), "Ethernet"),
    (re.compile(r"^ens\d", re.IGNORECASE), "Ethernet"),
    (re.compile(r"^mgmt", re.IGNORECASE), "mgmt"),
    (re.compile(r"^Loopback", re.IGNORECASE), "Loopback"),
    (re.compile(r"^Lo", re.IGNORECASE), "Loopback"),
    (re.compile(r"^Vlan", re.IGNORECASE), "Vlan"),
    (re.compile(r"^Port-?channel", re.IGNORECASE), "Port-channel"),
    (re.compile(r"^Po(\d)", re.IGNORECASE), "Port-channel"),
    (re.compile(r"^Tunnel", re.IGNORECASE), "Tunnel"),
    (re.compile(r"^nve", re.IGNORECASE), "nve"),
]


def normalise_port_name(raw: str) -> str:
    """Convert a raw Cisco interface name into the NS convention (with a single
    space between the type token and the number portion).
    Examples:
        Ethernet1/1         -> Ethernet 1/1
        Vlan100             -> Vlan 100
        loopback0           -> Loopback 0
        port-channel10      -> Port-channel 10
        GigabitEthernet0/2.20 -> GigabitEthernet 0/2.20
        mgmt0               -> mgmt 0
        eth0                -> Ethernet 0    (Linux NIC convention)
        eth1                -> Ethernet 1
        ens3                -> Ethernet 3
    """
    raw = raw.strip()
    for pat, canonical in _IFACE_TYPE_PATTERNS:
        m = pat.match(raw)
        if m:
            matched = raw[:m.end()]
            remainder = raw[m.end():].lstrip()
            # If the matched prefix consumed only the type letters (e.g. 'eth'),
            # remainder will start with the digit. If the matched prefix consumed
            # one digit too (because of the `\d` in the pattern), back up so we
            # retain the digit in `remainder`.
            if pat.pattern in (r"^eth\d", r"^ens\d"):
                # Re-extract: skip only the alphabetic prefix.
                m2 = re.match(r"^[A-Za-z]+", raw)
                if m2:
                    remainder = raw[m2.end():].lstrip()
            return f"{canonical} {remainder}" if remainder else canonical
    return raw  # unknown form: leave as-is


# ---------------------------------------------------------------------------
# CML link / interface plumbing
# ---------------------------------------------------------------------------

def _index_cml_interfaces(nodes: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Return {interface_id: {"node_id":..., "label":..., "node_label":...}}"""
    iface_index: Dict[str, Dict[str, Any]] = {}
    for n in nodes:
        node_id = n.get("id")
        node_label = n.get("label", "")
        for iface in n.get("interfaces", []) or []:
            iid = iface.get("id")
            if not iid:
                continue
            iface_index[iid] = {
                "node_id": node_id,
                "node_label": node_label,
                "iface_id": iid,
                "iface_label": iface.get("label", "") or iface.get("slot", ""),
                "iface_slot": iface.get("slot"),
                "iface_type": iface.get("type", ""),
            }
    return iface_index


# ---------------------------------------------------------------------------
# Area / hierarchy assignment
# ---------------------------------------------------------------------------

SITE_TAG_RE = re.compile(r"^(site\d+|wan-?isn|wan|core|dc\d+|pod\d+|hq|branch\d+|campus)$", re.IGNORECASE)
ENDPOINT_NDEF = {"alpine", "ubuntu", "centos", "tiny-linux", "server", "desktop",
                  "win-desktop", "win-server", "wireless-client"}
WAYPOINT_NDEF = {"external_connector"}


def _pick_area(node: Dict[str, Any]) -> str:
    """Choose an area name from a CML node's tags / label."""
    tags = [str(t).lower() for t in (node.get("tags") or [])]
    for t in tags:
        if SITE_TAG_RE.match(t):
            return t.lower()
    # Heuristics on label: e.g. "s1-spine1" => site1, "s2-leaf1" => site2.
    label = (node.get("label", "") or "").lower()
    m = re.match(r"^s(\d+)-", label)
    if m:
        return f"site{m.group(1)}"
    if any(k in label for k in ["wan", "isn", "internet", "cloud"]):
        return "wan-isn"
    if label.startswith("h") and re.match(r"^h\d", label):
        # alpine host labelling pattern h11, h21 => site1, site2
        if len(label) >= 2 and label[1].isdigit():
            return f"site{label[1]}"
    return "default"


def _pick_row(node: Dict[str, Any], stencil: StencilMapping) -> int:
    tags = [str(t).lower() for t in (node.get("tags") or [])]
    nd = (node.get("node_definition") or "").lower()
    label = (node.get("label", "") or "").lower()

    if stencil.stencil_type == NS_CLOUD or nd in WAYPOINT_NDEF or "wan" in label or "isn" in label:
        return 0
    if any(t in tags for t in ["bgw", "border", "edge"]) or "bgw" in label or "border" in label:
        return 1
    if stencil.stencil_type == NS_FIREWALL:
        return 1
    if "spine" in tags or "spine" in label:
        return 2
    if "leaf" in tags or "leaf" in label:
        return 3
    if stencil.stencil_type == NS_L3SWITCH:
        return 3
    if any(k in label for k in ["core", "dist", "agg"]):
        return 3
    if stencil.stencil_type in {NS_SWITCH, NS_WLC}:
        return 4
    if stencil.stencil_type == NS_AP:
        return 4
    if nd in ENDPOINT_NDEF or stencil.stencil_type in {NS_SERVER, NS_PC}:
        return 5
    return 3  # safe default for unknown infra (Router)


def assign_areas_and_rows(
    nodes: List[Dict[str, Any]],
    stencils: Dict[str, StencilMapping],
) -> Dict[str, NSDevice]:
    devices: Dict[str, NSDevice] = {}
    for n in nodes:
        label = str(n.get("label", ""))
        if not label:
            continue
        st = stencils[label]
        area = _pick_area(n)
        row = _pick_row(n, st)
        is_endpoint = st.stencil_type in {NS_SERVER, NS_PC} or (n.get("node_definition") or "") in ENDPOINT_NDEF
        devices[label] = NSDevice(
            name=label,
            area=area,
            row=row,
            stencil=st,
            is_endpoint=is_endpoint,
        )
    return devices


def build_area_layout(devices: Dict[str, NSDevice]) -> Tuple[List[List[str]], Dict[str, List[List[str]]]]:
    """Return (area_layout, area_to_device_grid).

    Strategy:
      - Areas are placed left-to-right in row 0 (one outer row is enough for POC).
      - Within an area, devices are placed top-to-bottom by `row`, then sorted
        by name on the same row.
      - Waypoint areas (`wan-isn`) become `*_wp_` placed between site areas if
        present.
    """
    by_area: Dict[str, List[NSDevice]] = {}
    for d in devices.values():
        by_area.setdefault(d.area, []).append(d)

    ordered_areas: List[str] = sorted(by_area.keys(), key=_area_sort_key)
    # Promote wan-isn-style areas to waypoint naming so NS treats them as clouds.
    rendered_areas: List[str] = []
    name_map: Dict[str, str] = {}
    for a in ordered_areas:
        if a in {"wan-isn", "wan", "internet", "cloud"}:
            rendered = f"{a}_wp_"
        else:
            rendered = a
        rendered_areas.append(rendered)
        name_map[a] = rendered

    # Re-apply area names back to devices.
    for d in devices.values():
        d.area = name_map.get(d.area, d.area)

    area_to_grid: Dict[str, List[List[str]]] = {}
    for orig_area, devs in by_area.items():
        rendered = name_map[orig_area]
        # Group by row, sort each row by label.
        row_buckets: Dict[int, List[str]] = {}
        for d in devs:
            row_buckets.setdefault(d.row, []).append(d.name)
        grid: List[List[str]] = []
        for row_idx in sorted(row_buckets.keys()):
            grid.append(sorted(row_buckets[row_idx]))
        area_to_grid[rendered] = grid

    area_layout = [rendered_areas]
    return area_layout, area_to_grid


def _area_sort_key(area: str) -> Tuple[int, str]:
    # WAN clouds go first (left), then site1, site2, ... then 'default' last.
    if area in {"wan-isn", "wan", "internet", "cloud"}:
        return (0, area)
    m = re.match(r"site(\d+)", area)
    if m:
        return (1, f"{int(m.group(1)):03d}")
    if area == "default":
        return (9, area)
    return (5, area)


# ---------------------------------------------------------------------------
# L1 link extraction (from CML topology)
# ---------------------------------------------------------------------------

def build_l1_links(
    links: List[Dict[str, Any]],
    iface_index: Dict[str, Dict[str, Any]],
) -> List[NSL1Link]:
    out: List[NSL1Link] = []
    for link in links:
        a_iface = iface_index.get(link.get("interface_a", ""))
        b_iface = iface_index.get(link.get("interface_b", ""))
        if not a_iface or not b_iface:
            continue
        a_port = normalise_port_name(a_iface["iface_label"] or "")
        b_port = normalise_port_name(b_iface["iface_label"] or "")
        if not a_port or not b_port:
            continue
        out.append(NSL1Link(
            a_device=a_iface["node_label"],
            a_port=a_port,
            b_device=b_iface["node_label"],
            b_port=b_port,
        ))
    return out


# ---------------------------------------------------------------------------
# Apply parsed configs (VLANs / SVIs / Loopbacks / L3 / port-channels / VRFs)
# ---------------------------------------------------------------------------

def apply_parsed_configs(
    model: NSModel,
    parsed_configs: Dict[str, Any],   # label -> ParsedConfig
    cml_node_labels: Set[str],
) -> Dict[str, Dict[str, int]]:
    """Walk every parsed config and fill model.l2_segments / virtual_ports etc.

    Returns a per-device stat dict for the parse_report.md.
    """
    stats: Dict[str, Dict[str, int]] = {}
    for label, cfg in parsed_configs.items():
        if label not in model.devices:
            continue
        is_endpoint = model.devices[label].is_endpoint
        st = {"vlans": 0, "svi": 0, "loopback": 0,
              "l3_phys": 0, "l2_trunk": 0, "l2_access": 0, "portchannel": 0, "vrf": 0}

        # Per-VLAN are recorded only for routing-summary; NS doesn't have a
        # VLAN-table concept independent of an SVI binding. So we just count.
        st["vlans"] = len(cfg.vlans)

        # Track port-channel members for the portchannel_bulk call.
        po_members: Dict[int, List[str]] = {}

        for iname, iface in cfg.interfaces.items():
            ns_port = normalise_port_name(iname)

            if iface.kind == "svi":
                if not is_endpoint and iface.ipv4:
                    vid = _extract_vlan_id(iname)
                    model.virtual_ports.append(NSVirtualPort(
                        device=label, port=ns_port, vlan_id=vid,
                    ))
                    model.ip_assignments.append(NSIPAssignment(
                        device=label, port=ns_port,
                        cidrs=[a.cidr for a in iface.ipv4 + iface.ipv4_secondary],
                    ))
                    if vid is not None:
                        model.l2_segments_svi.append(NSL2Segment(
                            device=label, port=ns_port,
                            vlans=[f"Vlan{vid}"],
                        ))
                    if iface.vrf:
                        model.vrf_renames.append((label, ns_port, iface.vrf))
                    st["svi"] += 1

            elif iface.kind == "loopback":
                if iface.ipv4:
                    model.virtual_ports.append(NSVirtualPort(
                        device=label, port=ns_port, is_loopback=True,
                    ))
                    model.ip_assignments.append(NSIPAssignment(
                        device=label, port=ns_port,
                        cidrs=[a.cidr for a in iface.ipv4],
                    ))
                    if iface.vrf:
                        model.vrf_renames.append((label, ns_port, iface.vrf))
                    st["loopback"] += 1

            elif iface.kind == "portchannel":
                # The port-channel virtual interface itself.
                if iface.ipv4:
                    model.ip_assignments.append(NSIPAssignment(
                        device=label, port=ns_port,
                        cidrs=[a.cidr for a in iface.ipv4],
                    ))
                    st["l3_phys"] += 1
                if iface.trunk_allowed_vlans and not is_endpoint:
                    model.l2_segments_phys.append(NSL2Segment(
                        device=label, port=ns_port,
                        vlans=[f"Vlan{v}" for v in iface.trunk_allowed_vlans],
                    ))
                    st["l2_trunk"] += 1
                if iface.access_vlan and not is_endpoint:
                    model.l2_segments_phys.append(NSL2Segment(
                        device=label, port=ns_port,
                        vlans=[f"Vlan{iface.access_vlan}"],
                    ))
                    st["l2_access"] += 1
                if iface.vrf:
                    model.vrf_renames.append((label, ns_port, iface.vrf))

            elif iface.kind in {"physical", "subif"}:
                if iface.channel_group is not None:
                    po_members.setdefault(iface.channel_group, []).append(ns_port)
                    st["portchannel"] += 1
                    continue
                if iface.is_routed() and iface.ipv4:
                    model.ip_assignments.append(NSIPAssignment(
                        device=label, port=ns_port,
                        cidrs=[a.cidr for a in iface.ipv4 + iface.ipv4_secondary],
                    ))
                    if iface.vrf:
                        model.vrf_renames.append((label, ns_port, iface.vrf))
                    st["l3_phys"] += 1
                else:
                    if is_endpoint:
                        # Endpoint side: do nothing here; IP (if any) is direct (RULE 11.5).
                        if iface.ipv4:
                            model.ip_assignments.append(NSIPAssignment(
                                device=label, port=ns_port,
                                cidrs=[a.cidr for a in iface.ipv4],
                            ))
                            st["l3_phys"] += 1
                    else:
                        # Switch-mode physical port: l2_segment.
                        if iface.mode == "trunk" and iface.trunk_allowed_vlans:
                            model.l2_segments_phys.append(NSL2Segment(
                                device=label, port=ns_port,
                                vlans=[f"Vlan{v}" for v in iface.trunk_allowed_vlans],
                            ))
                            st["l2_trunk"] += 1
                        elif iface.access_vlan:
                            model.l2_segments_phys.append(NSL2Segment(
                                device=label, port=ns_port,
                                vlans=[f"Vlan{iface.access_vlan}"],
                            ))
                            st["l2_access"] += 1

            elif iface.kind == "mgmt":
                # Mgmt interfaces are usually in 'management' VRF — record as
                # L3 physical with VRF tag (NS represents it as L3 on the port).
                if iface.ipv4:
                    model.ip_assignments.append(NSIPAssignment(
                        device=label, port=ns_port,
                        cidrs=[a.cidr for a in iface.ipv4],
                    ))
                    if iface.vrf:
                        model.vrf_renames.append((label, ns_port, iface.vrf))
                    st["l3_phys"] += 1

            # Tunnel / nve / others: routing-summary text only.

        # Emit port-channels we collected.
        for po_id, members in po_members.items():
            pc_name = f"Port-channel {po_id}"
            model.port_channels.append(NSPortChannel(
                device=label,
                physical_ports=sorted(set(members)),
                portchannel_name=pc_name,
            ))

        # Routing summary -> stored on device for assess.py.
        if cfg.routing_summary_lines:
            model.devices[label].routing_attribute = "\n".join(cfg.routing_summary_lines[:30])

        stats[label] = st
    return stats


def _extract_vlan_id(iface_name: str) -> Optional[int]:
    m = re.search(r"(\d+)$", iface_name)
    return int(m.group(1)) if m else None


# ---------------------------------------------------------------------------
# Top-level builder
# ---------------------------------------------------------------------------

def build_ns_model(
    nodes: List[Dict[str, Any]],
    links: List[Dict[str, Any]],
    stencils: Dict[str, StencilMapping],
    parsed_configs: Dict[str, Any],
) -> Tuple[NSModel, Dict[str, Dict[str, int]]]:
    model = NSModel()
    model.devices = assign_areas_and_rows(nodes, stencils)
    model.areas, model.area_to_devices = build_area_layout(model.devices)

    iface_index = _index_cml_interfaces(nodes)
    model.l1_links = build_l1_links(links, iface_index)

    parse_stats = apply_parsed_configs(
        model, parsed_configs,
        cml_node_labels={str(n.get("label", "")) for n in nodes},
    )
    return model, parse_stats


# ---------------------------------------------------------------------------
# JSON serialisation helper
# ---------------------------------------------------------------------------

def model_to_dict(model: NSModel) -> Dict[str, Any]:
    return {
        "area_layout": model.areas,
        "area_to_devices": model.area_to_devices,
        "devices": {
            name: {
                "area": d.area, "row": d.row, "is_endpoint": d.is_endpoint,
                "stencil": d.stencil.stencil_type,
                "model": d.stencil.model,
                "os": d.stencil.os,
                "confidence": d.stencil.confidence,
                "routing_attribute_len": len(d.routing_attribute),
            }
            for name, d in sorted(model.devices.items())
        },
        "l1_links": [
            {"a_device": x.a_device, "a_port": x.a_port,
             "b_device": x.b_device, "b_port": x.b_port}
            for x in model.l1_links
        ],
        "virtual_ports": [
            {"device": v.device, "port": v.port,
             "is_loopback": v.is_loopback, "vlan_id": v.vlan_id}
            for v in model.virtual_ports
        ],
        "ip_assignments": [
            {"device": ip.device, "port": ip.port, "cidrs": ip.cidrs}
            for ip in model.ip_assignments
        ],
        "l2_segments_phys": [
            {"device": s.device, "port": s.port, "vlans": s.vlans}
            for s in model.l2_segments_phys
        ],
        "l2_segments_svi": [
            {"device": s.device, "port": s.port, "vlans": s.vlans}
            for s in model.l2_segments_svi
        ],
        "port_channels": [
            {"device": pc.device, "physical_ports": pc.physical_ports,
             "portchannel_name": pc.portchannel_name}
            for pc in model.port_channels
        ],
        "vrf_renames": [
            {"device": d, "port": p, "vrf": v}
            for (d, p, v) in model.vrf_renames
        ],
    }
