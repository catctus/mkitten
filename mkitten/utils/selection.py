"""Selection utilities - vertex selection and soft selection with falloff."""

import maya.cmds as cmds
import maya.api.OpenMaya as om2


def get_mesh_from_selection():
    """Get the mesh transform from the current selection.

    Works whether the user has selected the mesh, components, or
    vertices.

    Returns:
        The mesh transform name, or None if no mesh is selected.
    """
    sel = cmds.ls(selection=True, objectsOnly=True, long=True)
    if not sel:
        # Try getting mesh from component selection
        sel = cmds.ls(selection=True, long=True)
        if sel:
            mesh = sel[0].split(".")[0]
            if cmds.objectType(cmds.listRelatives(mesh, shapes=True)[0]) == "mesh":
                return mesh
        return None

    obj = sel[0]
    shapes = cmds.listRelatives(obj, shapes=True, type="mesh") or []
    if shapes:
        return obj
    return None


def get_selected_vertices():
    """Get vertex indices from the current selection.

    Handles vertex, edge, and face selections by converting to vertices.

    Returns:
        Tuple of (mesh_transform, list_of_vertex_indices) or (None, [])
        if no valid selection.
    """
    sel = cmds.ls(selection=True, flatten=True)
    if not sel:
        return None, []

    # Convert any component selection to vertices
    verts = cmds.polyListComponentConversion(sel, toVertex=True) or []
    verts = cmds.filterExpand(verts, selectionMask=31) or []  # 31 = poly vertex

    if not verts:
        return None, []

    mesh = verts[0].split(".")[0]

    indices = []
    for v in verts:
        # Parse "mesh.vtx[123]"
        idx = int(v.split("[")[-1].rstrip("]"))
        indices.append(idx)

    return mesh, sorted(set(indices))


def get_soft_selection():
    """Get soft selection data including falloff values.

    Returns:
        Tuple of (mesh_transform, dict of {vertex_index: falloff_weight})
        where falloff_weight is 0.0 to 1.0.
        Returns (None, {}) if soft selection is off or nothing selected.
    """
    # Check if soft selection is active
    if not cmds.softSelect(query=True, softSelectEnabled=True):
        return None, {}

    rich_sel = om2.MGlobal.getRichSelection()
    rich_selection = rich_sel.getSelection()

    if rich_selection.isEmpty():
        return None, {}

    result = {}
    mesh = None

    iter_sel = om2.MItSelectionList(rich_selection)
    while not iter_sel.isDone():
        dag_path, component = iter_sel.getComponent()

        if component.isNull():
            iter_sel.next()
            continue

        if mesh is None:
            transform = cmds.listRelatives(
                dag_path.fullPathName(), parent=True, fullPath=True
            )
            mesh = transform[0] if transform else dag_path.fullPathName()

        if component.apiType() == om2.MFn.kMeshVertComponent:
            vert_fn = om2.MFnSingleIndexedComponent(component)
            for i in range(vert_fn.elementCount):
                idx = vert_fn.element(i)
                weight = vert_fn.weight(i).influence
                result[idx] = weight

        iter_sel.next()

    # Also check the symmetric selection if present
    try:
        sym_selection = rich_sel.getSymmetry()
        if not sym_selection.isEmpty():
            iter_sym = om2.MItSelectionList(sym_selection)
            while not iter_sym.isDone():
                dag_path, component = iter_sym.getComponent()
                if not component.isNull() and component.apiType() == om2.MFn.kMeshVertComponent:
                    vert_fn = om2.MFnSingleIndexedComponent(component)
                    for i in range(vert_fn.elementCount):
                        idx = vert_fn.element(i)
                        weight = vert_fn.weight(i).influence
                        if idx not in result:
                            result[idx] = weight
                iter_sym.next()
    except Exception:
        pass

    return mesh, result


def get_vertices_with_falloff():
    """Get selected vertices with their falloff values.

    If soft selection is on, returns vertices with their soft selection
    falloff. If soft selection is off, returns hard-selected vertices
    with falloff of 1.0.

    Returns:
        Tuple of (mesh_transform, dict of {vertex_index: falloff_weight}).
        Returns (None, {}) if nothing is selected.
    """
    # Try soft selection first
    if cmds.softSelect(query=True, softSelectEnabled=True):
        mesh, falloff = get_soft_selection()
        if mesh and falloff:
            return mesh, falloff

    # Fall back to hard selection
    mesh, indices = get_selected_vertices()
    if mesh and indices:
        falloff = {idx: 1.0 for idx in indices}
        return mesh, falloff

    return None, {}
