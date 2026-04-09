#!/usr/bin/env python3
"""Generate a minimal rigged humanoid GLB for SignBridge.

Creates a simple upper-body avatar with 48 joints matching the bone hierarchy
expected by the dictionary and renderer. The mesh is a low-poly humanoid
(head, torso, upper arms, forearms, hands with finger segments).

Output: app/src/main/assets/models/avatar.glb

No external dependencies — uses only stdlib (struct, json).
"""

import json
import struct
import math
from pathlib import Path

# ── Joint definitions ────────────────────────────────────────────────
# Each joint: (name, parent_index, rest_position_xyz)
# parent_index=-1 means root

JOINTS = [
    # Body (0-5)
    ("right_shoulder", -1, (0.2, 0.4, 0.0)),
    ("right_elbow", 0, (0.35, 0.15, 0.0)),
    ("right_wrist", 1, (0.45, -0.05, 0.0)),
    ("left_shoulder", -1, (-0.2, 0.4, 0.0)),
    ("left_elbow", 3, (-0.35, 0.15, 0.0)),
    ("left_wrist", 4, (-0.45, -0.05, 0.0)),
    # Right hand (6-25)
    ("right_thumb_cmc", 2, (0.48, -0.06, 0.02)),
    ("right_thumb_mcp", 6, (0.50, -0.08, 0.03)),
    ("right_thumb_ip", 7, (0.52, -0.10, 0.03)),
    ("right_thumb_tip", 8, (0.53, -0.12, 0.03)),
    ("right_index_mcp", 2, (0.47, -0.10, 0.01)),
    ("right_index_pip", 10, (0.48, -0.14, 0.01)),
    ("right_index_dip", 11, (0.48, -0.17, 0.01)),
    ("right_index_tip", 12, (0.48, -0.19, 0.01)),
    ("right_middle_mcp", 2, (0.46, -0.10, 0.0)),
    ("right_middle_pip", 14, (0.46, -0.14, 0.0)),
    ("right_middle_dip", 15, (0.46, -0.17, 0.0)),
    ("right_middle_tip", 16, (0.46, -0.19, 0.0)),
    ("right_ring_mcp", 2, (0.44, -0.10, -0.01)),
    ("right_ring_pip", 18, (0.44, -0.14, -0.01)),
    ("right_ring_dip", 19, (0.44, -0.17, -0.01)),
    ("right_ring_tip", 20, (0.44, -0.19, -0.01)),
    ("right_pinky_mcp", 2, (0.43, -0.09, -0.02)),
    ("right_pinky_pip", 22, (0.43, -0.12, -0.02)),
    ("right_pinky_dip", 23, (0.43, -0.14, -0.02)),
    ("right_pinky_tip", 24, (0.43, -0.16, -0.02)),
    # Left hand (26-45)
    ("left_thumb_cmc", 5, (-0.48, -0.06, 0.02)),
    ("left_thumb_mcp", 26, (-0.50, -0.08, 0.03)),
    ("left_thumb_ip", 27, (-0.52, -0.10, 0.03)),
    ("left_thumb_tip", 28, (-0.53, -0.12, 0.03)),
    ("left_index_mcp", 5, (-0.47, -0.10, 0.01)),
    ("left_index_pip", 30, (-0.48, -0.14, 0.01)),
    ("left_index_dip", 31, (-0.48, -0.17, 0.01)),
    ("left_index_tip", 32, (-0.48, -0.19, 0.01)),
    ("left_middle_mcp", 5, (-0.46, -0.10, 0.0)),
    ("left_middle_pip", 34, (-0.46, -0.14, 0.0)),
    ("left_middle_dip", 35, (-0.46, -0.17, 0.0)),
    ("left_middle_tip", 36, (-0.46, -0.19, 0.0)),
    ("left_ring_mcp", 5, (-0.44, -0.10, -0.01)),
    ("left_ring_pip", 38, (-0.44, -0.14, -0.01)),
    ("left_ring_dip", 39, (-0.44, -0.17, -0.01)),
    ("left_ring_tip", 40, (-0.44, -0.19, -0.01)),
    ("left_pinky_mcp", 5, (-0.43, -0.09, -0.02)),
    ("left_pinky_pip", 42, (-0.43, -0.12, -0.02)),
    ("left_pinky_dip", 43, (-0.43, -0.14, -0.02)),
    ("left_pinky_tip", 44, (-0.43, -0.16, -0.02)),
    # Spine/head (46-47) — extra joints to reach 48
    ("spine", -1, (0.0, 0.3, 0.0)),
    ("head", 46, (0.0, 0.6, 0.0)),
]

assert len(JOINTS) == 48, f"Expected 48 joints, got {len(JOINTS)}"


def make_identity_matrix():
    return [
        1, 0, 0, 0,
        0, 1, 0, 0,
        0, 0, 1, 0,
        0, 0, 0, 1,
    ]


def make_translation_matrix(x, y, z):
    return [
        1, 0, 0, 0,
        0, 1, 0, 0,
        0, 0, 1, 0,
        x, y, z, 1,
    ]


def invert_translation_matrix(m):
    """Invert a pure translation matrix."""
    return [
        1, 0, 0, 0,
        0, 1, 0, 0,
        0, 0, 1, 0,
        -m[12], -m[13], -m[14], 1,
    ]


def generate_box_vertices(cx, cy, cz, sx, sy, sz):
    """Generate 8 vertices and 12 triangles for a box."""
    hx, hy, hz = sx / 2, sy / 2, sz / 2
    verts = [
        (cx - hx, cy - hy, cz - hz), (cx + hx, cy - hy, cz - hz),
        (cx + hx, cy + hy, cz - hz), (cx - hx, cy + hy, cz - hz),
        (cx - hx, cy - hy, cz + hz), (cx + hx, cy - hy, cz + hz),
        (cx + hx, cy + hy, cz + hz), (cx - hx, cy + hy, cz + hz),
    ]
    # 6 faces × 2 triangles × 3 indices
    indices = [
        0, 1, 2, 0, 2, 3,  # front
        4, 6, 5, 4, 7, 6,  # back
        0, 4, 5, 0, 5, 1,  # bottom
        2, 6, 7, 2, 7, 3,  # top
        0, 3, 7, 0, 7, 4,  # left
        1, 5, 6, 1, 6, 2,  # right
    ]
    return verts, indices


def generate_sphere_vertices(cx, cy, cz, radius, segments=8, rings=6):
    """Generate a UV sphere."""
    verts = []
    indices = []

    for ring in range(rings + 1):
        phi = math.pi * ring / rings
        for seg in range(segments + 1):
            theta = 2.0 * math.pi * seg / segments
            x = cx + radius * math.sin(phi) * math.cos(theta)
            y = cy + radius * math.cos(phi)
            z = cz + radius * math.sin(phi) * math.sin(theta)
            verts.append((x, y, z))

    for ring in range(rings):
        for seg in range(segments):
            a = ring * (segments + 1) + seg
            b = a + segments + 1
            indices.extend([a, b, a + 1, a + 1, b, b + 1])

    return verts, indices


def generate_cylinder(cx, cy, cz, radius, height, segments=8):
    """Generate a simple cylinder."""
    verts = []
    indices = []
    half_h = height / 2

    # Top and bottom rings
    for i in range(2):
        y = cy + half_h if i == 0 else cy - half_h
        for s in range(segments):
            angle = 2.0 * math.pi * s / segments
            x = cx + radius * math.cos(angle)
            z = cz + radius * math.sin(angle)
            verts.append((x, y, z))

    # Side faces
    for s in range(segments):
        top = s
        bot = s + segments
        next_top = (s + 1) % segments
        next_bot = next_top + segments
        indices.extend([top, bot, next_top, next_top, bot, next_bot])

    return verts, indices


def compute_normals(positions, indices):
    """Compute per-vertex normals by averaging face normals."""
    normals = [[0, 0, 0] for _ in positions]

    for i in range(0, len(indices), 3):
        i0, i1, i2 = indices[i], indices[i + 1], indices[i + 2]
        p0, p1, p2 = positions[i0], positions[i1], positions[i2]

        # Edge vectors
        e1 = (p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2])
        e2 = (p2[0] - p0[0], p2[1] - p0[1], p2[2] - p0[2])

        # Cross product
        nx = e1[1] * e2[2] - e1[2] * e2[1]
        ny = e1[2] * e2[0] - e1[0] * e2[2]
        nz = e1[0] * e2[1] - e1[1] * e2[0]

        for idx in (i0, i1, i2):
            normals[idx][0] += nx
            normals[idx][1] += ny
            normals[idx][2] += nz

    # Normalize
    for n in normals:
        mag = math.sqrt(n[0] ** 2 + n[1] ** 2 + n[2] ** 2)
        if mag > 1e-8:
            n[0] /= mag
            n[1] /= mag
            n[2] /= mag

    return normals


def find_nearest_joint(pos, joints):
    """Find the nearest joint to a vertex position."""
    best_idx = 0
    best_dist = float("inf")
    for i, (_, _, jp) in enumerate(joints):
        dx = pos[0] - jp[0]
        dy = pos[1] - jp[1]
        dz = pos[2] - jp[2]
        dist = dx * dx + dy * dy + dz * dz
        if dist < best_dist:
            best_dist = dist
            best_idx = i
    return best_idx


def build_avatar_mesh():
    """Build a simple humanoid mesh with body parts."""
    all_positions = []
    all_indices = []

    parts = []

    # Head (sphere)
    v, i = generate_sphere_vertices(0, 0.65, 0, 0.09, segments=10, rings=8)
    parts.append(("head", v, i))

    # Torso (box)
    v, i = generate_box_vertices(0, 0.35, 0, 0.3, 0.35, 0.15)
    parts.append(("spine", v, i))

    # Right upper arm
    v, i = generate_cylinder(0.28, 0.3, 0, 0.035, 0.2)
    parts.append(("right_shoulder", v, i))

    # Right forearm
    v, i = generate_cylinder(0.4, 0.08, 0, 0.03, 0.2)
    parts.append(("right_elbow", v, i))

    # Right hand (box)
    v, i = generate_box_vertices(0.45, -0.07, 0, 0.06, 0.08, 0.03)
    parts.append(("right_wrist", v, i))

    # Left upper arm
    v, i = generate_cylinder(-0.28, 0.3, 0, 0.035, 0.2)
    parts.append(("left_shoulder", v, i))

    # Left forearm
    v, i = generate_cylinder(-0.4, 0.08, 0, 0.03, 0.2)
    parts.append(("left_elbow", v, i))

    # Left hand (box)
    v, i = generate_box_vertices(-0.45, -0.07, 0, 0.06, 0.08, 0.03)
    parts.append(("left_wrist", v, i))

    # Merge all parts, assigning joints by part name
    joint_name_to_idx = {name: idx for idx, (name, _, _) in enumerate(JOINTS)}

    for part_name, verts, inds in parts:
        base_idx = len(all_positions)
        all_positions.extend(verts)
        all_indices.extend(idx + base_idx for idx in inds)

    # Compute normals
    all_normals = compute_normals(all_positions, all_indices)

    # Assign joint weights
    # Simple: each vertex weighted to nearest joint
    joint_indices_list = []
    weight_list = []

    # Track which part each vertex belongs to for better joint assignment
    vert_part_joint = []
    for part_name, verts, _ in parts:
        joint_idx = joint_name_to_idx.get(part_name, 46)  # default to spine
        for _ in verts:
            vert_part_joint.append(joint_idx)

    for i, pos in enumerate(all_positions):
        primary_joint = vert_part_joint[i]
        joint_indices_list.append((primary_joint, 0, 0, 0))
        weight_list.append((1.0, 0.0, 0.0, 0.0))

    return all_positions, all_normals, all_indices, joint_indices_list, weight_list


def pack_glb(positions, normals, indices, joint_indices, weights):
    """Pack everything into a GLB binary file."""

    num_verts = len(positions)
    num_indices = len(indices)

    # ── Binary buffer ────────────────────────────────────────────────
    bin_data = bytearray()

    # Accessor 0: positions (VEC3, FLOAT)
    pos_offset = len(bin_data)
    min_pos = [float("inf")] * 3
    max_pos = [float("-inf")] * 3
    for p in positions:
        for c in range(3):
            min_pos[c] = min(min_pos[c], p[c])
            max_pos[c] = max(max_pos[c], p[c])
        bin_data += struct.pack("<3f", *p)
    pos_length = len(bin_data) - pos_offset

    # Accessor 1: normals (VEC3, FLOAT)
    norm_offset = len(bin_data)
    for n in normals:
        bin_data += struct.pack("<3f", *n)
    norm_length = len(bin_data) - norm_offset

    # Accessor 2: joints (VEC4, UNSIGNED_BYTE)
    joint_offset = len(bin_data)
    for j in joint_indices:
        bin_data += struct.pack("<4B", *j)
    joint_length = len(bin_data) - joint_offset

    # Accessor 3: weights (VEC4, FLOAT)
    weight_offset = len(bin_data)
    for w in weights:
        bin_data += struct.pack("<4f", *w)
    weight_length = len(bin_data) - weight_offset

    # Accessor 4: indices (SCALAR, UNSIGNED_SHORT)
    idx_offset = len(bin_data)
    for idx in indices:
        bin_data += struct.pack("<H", idx)
    idx_length = len(bin_data) - idx_offset

    # Accessor 5: inverse bind matrices (MAT4, FLOAT) — 48 matrices
    ibm_offset = len(bin_data)
    for _, _, pos in JOINTS:
        mat = make_translation_matrix(*pos)
        inv = invert_translation_matrix(mat)
        for val in inv:
            bin_data += struct.pack("<f", val)
    ibm_length = len(bin_data) - ibm_offset

    # Pad to 4-byte alignment
    while len(bin_data) % 4 != 0:
        bin_data += b"\x00"

    # ── GLTF JSON ────────────────────────────────────────────────────
    gltf = {
        "asset": {"version": "2.0", "generator": "SignBridge avatar generator"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [],
        "meshes": [
            {
                "name": "avatar_mesh",
                "primitives": [
                    {
                        "attributes": {
                            "POSITION": 0,
                            "NORMAL": 1,
                            "JOINTS_0": 2,
                            "WEIGHTS_0": 3,
                        },
                        "indices": 4,
                    }
                ],
            }
        ],
        "skins": [
            {
                "inverseBindMatrices": 5,
                "joints": list(range(1, 48 + 1)),  # node indices 1-48
            }
        ],
        "accessors": [
            {  # 0: positions
                "bufferView": 0, "componentType": 5126, "count": num_verts,
                "type": "VEC3", "min": min_pos, "max": max_pos,
            },
            {  # 1: normals
                "bufferView": 1, "componentType": 5126, "count": num_verts,
                "type": "VEC3",
            },
            {  # 2: joints
                "bufferView": 2, "componentType": 5121, "count": num_verts,
                "type": "VEC4",
            },
            {  # 3: weights
                "bufferView": 3, "componentType": 5126, "count": num_verts,
                "type": "VEC4",
            },
            {  # 4: indices
                "bufferView": 4, "componentType": 5123, "count": num_indices,
                "type": "SCALAR",
            },
            {  # 5: inverse bind matrices
                "bufferView": 5, "componentType": 5126, "count": 48,
                "type": "MAT4",
            },
        ],
        "bufferViews": [
            {"buffer": 0, "byteOffset": pos_offset, "byteLength": pos_length, "target": 34962},
            {"buffer": 0, "byteOffset": norm_offset, "byteLength": norm_length, "target": 34962},
            {"buffer": 0, "byteOffset": joint_offset, "byteLength": joint_length, "target": 34962},
            {"buffer": 0, "byteOffset": weight_offset, "byteLength": weight_length, "target": 34962},
            {"buffer": 0, "byteOffset": idx_offset, "byteLength": idx_length, "target": 34963},
            {"buffer": 0, "byteOffset": ibm_offset, "byteLength": ibm_length},
        ],
        "buffers": [{"byteLength": len(bin_data)}],
    }

    # Node 0: mesh + skin
    gltf["nodes"].append({
        "name": "avatar",
        "mesh": 0,
        "skin": 0,
        "children": [1, 4, 47],  # right_shoulder, left_shoulder, spine root nodes
    })

    # Nodes 1-48: joints
    for i, (name, parent_idx, pos) in enumerate(JOINTS):
        node = {"name": name, "translation": list(pos)}
        # Build children list
        children = [j + 1 for j, (_, pidx, _) in enumerate(JOINTS) if pidx == i]
        if children:
            node["children"] = children
        gltf["nodes"].append(node)

    # ── Pack GLB ─────────────────────────────────────────────────────
    json_str = json.dumps(gltf, separators=(",", ":"))
    # Pad JSON to 4-byte alignment with spaces
    while len(json_str) % 4 != 0:
        json_str += " "
    json_bytes = json_str.encode("utf-8")

    # GLB header: magic + version + total_length
    total_length = 12 + 8 + len(json_bytes) + 8 + len(bin_data)

    glb = bytearray()
    glb += struct.pack("<III", 0x46546C67, 2, total_length)  # header
    glb += struct.pack("<II", len(json_bytes), 0x4E4F534A)   # JSON chunk header
    glb += json_bytes
    glb += struct.pack("<II", len(bin_data), 0x004E4942)     # BIN chunk header
    glb += bin_data

    return bytes(glb)


def main():
    print("Generating avatar mesh...")
    positions, normals, indices, joint_indices, weights = build_avatar_mesh()
    print(f"  {len(positions)} vertices, {len(indices)} indices")

    print("Packing GLB...")
    glb_data = pack_glb(positions, normals, indices, joint_indices, weights)
    print(f"  GLB size: {len(glb_data)} bytes ({len(glb_data) / 1024:.1f} KB)")

    out_path = Path("app/src/main/assets/models/avatar.glb")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "wb") as f:
        f.write(glb_data)
    print(f"  Written to: {out_path}")

    # Verify joint count
    print(f"  Joints: {len(JOINTS)}")
    for i, (name, parent, pos) in enumerate(JOINTS):
        parent_name = JOINTS[parent][0] if parent >= 0 else "root"
        print(f"    [{i:2d}] {name} (parent: {parent_name})")


if __name__ == "__main__":
    main()
