from services.graph_service import GraphService
from services.spanner_service import SpannerService
from models.graph import EdgeType, NodeType
import asyncio

async def get_Practitioners_with_specialism(specialism_name: str) -> str:
    """
    Finds practitioners who hold a specific specialism.
 
    Args:
        specialism_name: The name of the specialism to search for
                         (e.g. "Speech Eurythmy", "Therapeutic Eurythmy").
 
    Returns:
        A formatted string listing the practitioners with that specialism.
    """
    try:
        spanner       = SpannerService()
        graph_service = GraphService(spanner)
 
        graph_data = await graph_service.get_full_graph()
 
        target_specialism_ids = []
        specialism_names_found = []
        for node in graph_data.nodes:
            if node.type == NodeType.SPECIALISM and specialism_name.lower() in node.label.lower():
                target_specialism_ids.append(node.id)
                specialism_names_found.append(node.label)
 
        if not target_specialism_ids:
            return f"No specialism found matching '{specialism_name}'. Specialism names may differ — try a broader term."
 
    
        practitioners = []
        seen_practitioners = set()
        for edge in graph_data.edges:
            if edge.type == EdgeType.HAS_SPECIALISM and edge.target in target_specialism_ids:
                practitioner_node = next(
                    (n for n in graph_data.nodes if n.id == edge.source), None
                )
                if practitioner_node and practitioner_node.type == NodeType.PRACTITIONER:
                    if practitioner_node.id not in seen_practitioners:
                        practitioners.append(practitioner_node.label)
                        seen_practitioners.add(practitioner_node.id)
 
        if not practitioners:
            return (
                f"No practitioners found with the specialism '{specialism_name}' "
                f"(matched: {', '.join(specialism_names_found)})."
            )
 
        return (
            f"Practitioners with specialism matching '{specialism_name}' "
            f"({', '.join(specialism_names_found)}): {', '.join(practitioners)}"
        )
 
    except Exception as e:
        print(f"Error in get_practitioners_with_specialism: {e}")
        import traceback
        traceback.print_exc()
        return f"Error searching for practitioners: {str(e)}"
 
 
async def get_all_practitioners() -> str:
    """
    List all practitioners and their venues.
 
    Returns:
        A formatted string listing all practitioners and their venues.
    """
    try:
        spanner       = SpannerService()
        graph_service = GraphService(spanner)
 
        graph_data = await graph_service.get_full_graph()
 
        # BUG FIX 4: Was NodeType.SURVIVOR — renamed to NodeType.PRACTITIONER.
        practitioners_info = []
        for node in graph_data.nodes:
            if node.type == NodeType.PRACTITIONER:
                # 'biome' attribute renamed to 'venue' in the eurythmy schema.
                # BUG FIX 5: Was node.biome — renamed to node.venue (check your
                #            Node model; if still 'biome' update models/graph.py).
                venue = getattr(node, "venue", None) or "Unknown Venue"
                practitioners_info.append(f"{node.label} (Venue: {venue})")
 
        if not practitioners_info:
            return "No practitioners found in the network."
 
        return "All Practitioners:\n- " + "\n- ".join(practitioners_info)
 
    except Exception as e:
        print(f"Error in get_all_practitioners: {e}")
        import traceback
        traceback.print_exc()
        return f"Error listing practitioners: {str(e)}"
 
 
async def get_active_seeks() -> str:
    """
    Finds and lists active Seeks (needs) currently associated with participants.
 
    Returns:
        A formatted string listing active Seeks and the associated practitioners.
    """
    try:
        spanner       = SpannerService()
        graph_service = GraphService(spanner)
 
        graph_data = await graph_service.get_full_graph()
 
        active_seeks = []
 
        for edge in graph_data.edges:
            # BUG FIX 6: Was EdgeType.HAS_NEED — renamed to EdgeType.PARTICIPANT_SEEKS.
            if edge.type == EdgeType.PARTICIPANT_SEEKS:
                is_active = False
                status = edge.properties.get("status", "").lower()
 
                if status in ["active", "current", "open"]:
                    is_active = True
 
                # Also check target node properties
                if not is_active:
                    target_node = next(
                        (n for n in graph_data.nodes if n.id == edge.target), None
                    )
                    if target_node and target_node.type == NodeType.NEED:
                        urgency = str(target_node.properties.get("urgency", "")).lower()
                        if urgency in ["high", "critical", "extreme"]:
                            is_active = True
 
                if is_active:
                    # BUG FIX 7: Was NodeType.SURVIVOR — renamed to NodeType.PRACTITIONER.
                    practitioner_node = next(
                        (n for n in graph_data.nodes if n.id == edge.source), None
                    )
                    need_node = next(
                        (n for n in graph_data.nodes if n.id == edge.target), None
                    )
 
                    if practitioner_node and need_node:
                        active_seeks.append(
                            f"{need_node.label} (Participant: {practitioner_node.label})"
                        )
 
        if not active_seeks:
            return "No active Seeks detected at this time."
 
        return "Active Seeks:\n- " + "\n- ".join(active_seeks)
 
    except Exception as e:
        print(f"Error in get_active_seeks: {e}")
        import traceback
        traceback.print_exc()
        return f"Error searching for active Seeks: {str(e)}"
 
 
# ---------------------------------------------------------------------------
# Legacy aliases — keep while other modules still import the old names.
# Remove once all call-sites are updated.
# ---------------------------------------------------------------------------
get_Practitioners_with_skill = get_practitioners_with_specialism
get_all_Practitioners        = get_all_practitioners
get_urgent_Seeks             = get_active_seeks
