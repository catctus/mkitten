"""Skin cluster utilities - finding, reading and writing skin weights."""

import maya.cmds as cmds
import maya.api.OpenMaya as om2
import maya.api.OpenMayaAnim as oma2


def get_skin_cluster(mesh):
    """Find the skin cluster deforming a mesh.

    Args:
        mesh: Mesh transform or shape name.

    Returns:
        The skin cluster node name, or None if not found.
    """
    if not mesh:
        return None

    history = cmds.listHistory(mesh, pruneDagObjects=True) or []
    for node in history:
        if cmds.nodeType(node) == "skinCluster":
            return node
    return None


def _get_skin_fn(skin_cluster):
    """Return an MFnSkinCluster for the given skin cluster node."""
    sel = om2.MSelectionList()
    sel.add(skin_cluster)
    skin_obj = sel.getDependNode(0)
    return oma2.MFnSkinCluster(skin_obj)


def _get_mesh_dag(skin_cluster):
    """Return the MDagPath for the mesh deformed by the skin cluster."""
    skin_fn = _get_skin_fn(skin_cluster)
    # The output geometry at index 0
    out_geo = skin_fn.getOutputGeometry()
    if not out_geo:
        return None
    sel = om2.MSelectionList()
    sel.add(cmds.listRelatives(
        cmds.deformableShape(str(out_geo[0]), og=True)[0],
        parent=True, fullPath=True
    )[0] if False else "")
    # Simpler approach: get the mesh shape from the skinCluster
    shapes = cmds.skinCluster(skin_cluster, query=True, geometry=True) or []
    if not shapes:
        return None
    sel = om2.MSelectionList()
    sel.add(shapes[0])
    return sel.getDagPath(0)


def get_influence_names(skin_cluster):
    """Return a list of influence (joint) names for a skin cluster.

    Args:
        skin_cluster: Name of the skin cluster node.

    Returns:
        List of influence names in index order.
    """
    return cmds.skinCluster(skin_cluster, query=True, influence=True) or []


def get_vertex_weights(skin_cluster, vertex_indices):
    """Get skin weights for specific vertices.

    Args:
        skin_cluster: Name of the skin cluster node.
        vertex_indices: List of integer vertex indices.

    Returns:
        Dict mapping vertex index -> dict of {influence_index: weight}.
        Only includes influences with non-zero weights.
    """
    skin_fn = _get_skin_fn(skin_cluster)

    shapes = cmds.skinCluster(skin_cluster, query=True, geometry=True) or []
    if not shapes:
        return {}

    sel = om2.MSelectionList()
    sel.add(shapes[0])
    mesh_dag = sel.getDagPath(0)

    # Build single-component MObject for all requested verts
    vert_fn = om2.MFnSingleIndexedComponent()
    vert_comp = vert_fn.create(om2.MFn.kMeshVertComponent)
    for vi in vertex_indices:
        vert_fn.addElement(vi)

    weights, num_influences = skin_fn.getWeights(mesh_dag, vert_comp)

    result = {}
    for i, vi in enumerate(vertex_indices):
        vert_weights = {}
        for inf_idx in range(num_influences):
            w = weights[i * num_influences + inf_idx]
            if w > 0.0:
                vert_weights[inf_idx] = w
        result[vi] = vert_weights

    return result


def set_vertex_weights(skin_cluster, vertex_weights):
    """Set skin weights for specific vertices.

    Args:
        skin_cluster: Name of the skin cluster node.
        vertex_weights: Dict mapping vertex index -> dict of
            {influence_index: weight}.
    """
    if not vertex_weights:
        return

    skin_fn = _get_skin_fn(skin_cluster)
    influences = get_influence_names(skin_cluster)
    num_influences = len(influences)

    shapes = cmds.skinCluster(skin_cluster, query=True, geometry=True) or []
    if not shapes:
        return

    sel = om2.MSelectionList()
    sel.add(shapes[0])
    mesh_dag = sel.getDagPath(0)

    vertex_indices = sorted(vertex_weights.keys())

    # Build component
    vert_fn = om2.MFnSingleIndexedComponent()
    vert_comp = vert_fn.create(om2.MFn.kMeshVertComponent)
    for vi in vertex_indices:
        vert_fn.addElement(vi)

    # Build influence index array
    inf_indices = om2.MIntArray(range(num_influences))

    # Build flat weight array, normalizing per vertex to avoid Maya warnings
    flat_weights = om2.MDoubleArray(len(vertex_indices) * num_influences, 0.0)
    for i, vi in enumerate(vertex_indices):
        weights = vertex_weights[vi]
        offset = i * num_influences
        total = 0.0
        for inf_idx, w in weights.items():
            flat_weights[offset + inf_idx] = w
            total += w
        # Normalize so weights sum to exactly 1.0
        if total > 0.0 and abs(total - 1.0) > 1e-9:
            for j in range(num_influences):
                flat_weights[offset + j] /= total

    # Temporarily disable the skinCluster's own normalization to avoid warnings
    old_normalize = cmds.getAttr(f"{skin_cluster}.normalizeWeights")
    cmds.setAttr(f"{skin_cluster}.normalizeWeights", 0)
    try:
        skin_fn.setWeights(mesh_dag, vert_comp, inf_indices, flat_weights, normalize=False)
    finally:
        cmds.setAttr(f"{skin_cluster}.normalizeWeights", old_normalize)
