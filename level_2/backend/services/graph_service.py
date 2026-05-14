from typing import List, Dict, Any
from models.graph import Node, Edge, GraphData, NodeType, EdgeType
from services.spanner_service import SpannerService

class GraphService:
    def __init__(self, spanner: SpannerService):
        self.spanner = spanner

    async def get_full_graph(self) -> GraphData:
        """
        Fetch all nodes and edges from Google Cloud Spanner.
        Uses direct SQL queries for maximum compatibility.
        """
        try:
            nodes_dict: Dict[str, Node] = {}
            edges_list: List[Edge] = []

            # ==========================================================
            # NODES
            # ==========================================================

            with self.spanner.database.snapshot(multi_use=True) as snapshot:
                # ------------------------------------------------------
                # Practitioners
                # ------------------------------------------------------
                practitioner_query = """
                    SELECT practitioner_id, name, role, bio, pillar, notes
                    FROM Practitioners
                    LIMIT 100
                """
                practitioner_results = list(snapshot.execute_sql(practitioner_query))

                for row in practitioner_results:
                    practitioner_id, name, role, bio, pillar, notes = row

                    nodes_dict[practitioner_id] = Node(
                        id=practitioner_id,
                        type=NodeType.PRACTITIONER,
                        label=name or "",
                        properties={
                            "role": role or "",
                        },
                        bio=bio or None,
                    )

                # ------------------------------------------------------
                # Specialisms
                # ------------------------------------------------------
                specialism_query = """
                    SELECT specialism_id, name, category
                    FROM Specialisms
                    LIMIT 100
                """
                specialism_results = list(snapshot.execute_sql(specialism_query))
                
                for row in specialism_results:
                    specialism_id, name, category = row

                    nodes_dict[specialism_id] = Node(
                        id=specialism_id,
                        type=NodeType.SPECIALISM,
                        label=name or "",
                        properties={
                            "category": category or "",
                        },
                    )

                # ------------------------------------------------------
                # Seeks
                # ------------------------------------------------------
                seek_query = """
                    SELECT seek_id, name, category, description
                    FROM Seeks
                    LIMIT 100
                """
                seek_results = list(snapshot.execute_sql(seek_query))

                for row in seek_results:
                    seek_id, name, category, description = row

                    nodes_dict[seek_id] = Node(
                        id=seek_id,
                        type=NodeType.SEEK,
                        label=name or description or "",
                        properties={
                            "category": category or "",
                            "description": description or "",
                        },
                    )

                # ------------------------------------------------------
                # Venues
                # ------------------------------------------------------
                venue_query = """
                    SELECT venue_id, name, type, location
                    FROM Venues
                    LIMIT 100
                """
                venue_results = list(snapshot.execute_sql(venue_query))

                for row in venue_results:
                    venue_id, name, venue_type, location = row

                    nodes_dict[venue_id] = Node(
                        id=venue_id,
                        type=NodeType.VENUE,
                        label=name or "",
                        properties={
                            "type": venue_type or "",
                            "location": location or "",
                        },
                    )

                # ------------------------------------------------------
                # Materials
                # ------------------------------------------------------
                material_query = """
                    SELECT material_id, name, type
                    FROM Materials
                    LIMIT 100
                """
                material_results = list(snapshot.execute_sql(material_query))

                for row in material_results:
                    material_id, name, material_type = row

                    nodes_dict[material_id] = Node(
                        id=material_id,
                        type=NodeType.MATERIAL,
                        label=name or "",
                        properties={
                            "type": material_type or "",
                        },
                    )

            # ==========================================================
            # EDGES
            # ==========================================================

            with self.spanner.database.snapshot(multi_use=True) as snapshot:
                # ------------------------------------------------------
                # PractitionerHasSpecialism
                # ------------------------------------------------------
                query = """
                    SELECT practitioner_id, specialism_id, level
                    FROM PractitionerHasSpecialism
                    LIMIT 100
                """
                results = list(snapshot.execute_sql(query))

                for practitioner_id, specialism_id, level in results:
                    edges_list.append(
                        Edge(
                            id=f"{practitioner_id}-{specialism_id}",
                            source=practitioner_id,
                            target=specialism_id,
                            type=EdgeType.HAS_SPECIALISM,
                            properties={
                                "level": level or "",
                            },
                        )
                    )

                # ------------------------------------------------------
                # ParticipantSeeks
                # ------------------------------------------------------
                query = """
                    SELECT practitioner_id, seek_id, status
                    FROM ParticipantSeeks
                    LIMIT 100
                """
                results = list(snapshot.execute_sql(query))

                for practitioner_id, seek_id, status in results:
                    edges_list.append(
                        Edge(
                            id=f"{practitioner_id}-{seek_id}",
                            source=practitioner_id,
                            target=seek_id,
                            type=EdgeType.HAS_SEEK,
                            properties={
                                "status": status or "",
                            },
                        )
                    )

                # ------------------------------------------------------
                # SpecialismTreatsNeed
                # ------------------------------------------------------
                query = """
                    SELECT specialism_id, seek_id, strength, notes
                    FROM SpecialismTreatsNeed
                    LIMIT 100
                """
                results = list(snapshot.execute_sql(query))

                for specialism_id, seek_id, strength, notes in results:
                    edges_list.append(
                        Edge(
                            id=f"{specialism_id}-{seek_id}",
                            source=specialism_id,
                            target=seek_id,
                            type=EdgeType.TREATS,
                            properties={
                                "strength": strength or "",
                                "notes": notes or "",
                            },
                        )
                    )

                # ------------------------------------------------------
                # PractitionerAtVenue
                # ------------------------------------------------------
                query = """
                    SELECT practitioner_id, venue_id
                    FROM PractitionerAtVenue
                    LIMIT 100
                """
                results = list(snapshot.execute_sql(query))

                for practitioner_id, venue_id in results:
                    edges_list.append(
                        Edge(
                            id=f"{practitioner_id}-{venue_id}",
                            source=practitioner_id,
                            target=venue_id,
                            type=EdgeType.AT_VENUE,
                            properties={},
                        )
                    )

                # ------------------------------------------------------
                # PractitionerFoundMaterial
                # ------------------------------------------------------
                query = """
                    SELECT practitioner_id, material_id, found_at
                    FROM PractitionerFoundMaterial
                    LIMIT 100
                """
                results = list(snapshot.execute_sql(query))

                for practitioner_id, material_id, found_at in results:
                    edges_list.append(
                        Edge(
                            id=f"{practitioner_id}-{material_id}",
                            source=practitioner_id,
                            target=material_id,
                            type=EdgeType.FOUND_MATERIAL,
                            properties={
                                "found_at": str(found_at) if found_at else "",
                            },
                        )
                    )

                # ------------------------------------------------------
                # PractitionerCanSupport
                # ------------------------------------------------------
                query = """
                    SELECT helper_id, helpee_id, reason, match_score
                    FROM PractitionerCanSupport
                    LIMIT 100
                """
                results = list(snapshot.execute_sql(query))

                for helper_id, helpee_id, reason, match_score in results:
                    edges_list.append(
                        Edge(
                            id=f"{helper_id}-{helpee_id}",
                            source=helper_id,
                            target=helpee_id,
                            type=EdgeType.CAN_SUPPORT,
                            properties={
                                "reason": reason or "",
                                "match_score": match_score if match_score is not None else 0,
                            },
                        )
                    )

            return GraphData(
                nodes=list(nodes_dict.values()),
                edges=edges_list,
            )

        except Exception as e:
            print(f"Error fetching full graph: {e}")
            import traceback
            traceback.print_exc()

            # Return fallback mock data
            return self._get_mock_data()

    async def query_graph(self, gql_query: str) -> GraphData:
        """
        Execute a custom graph query.
        Currently returns the full graph.
        """
        return await self.get_full_graph()

    def _is_node(self, data: Any) -> bool:
        """Check if a dictionary represents a node."""
        return (
            isinstance(data, dict)
            and "id" in data
            and "type" in data
        )

    def _is_edge(self, data: Any) -> bool:
        """Check if a dictionary represents an edge."""
        return (
            isinstance(data, dict)
            and "id" in data
            and "source" in data
            and "target" in data
        )

    def _parse_node(self, node_data: Any) -> Node | None:
        """Parse node dictionary into Node model."""
        if not isinstance(node_data, dict):
            return None

        try:
            return Node(
                id=node_data.get("id", ""),
                type=node_data.get("type", NodeType.PRACTITIONER),
                label=node_data.get("label", ""),
                properties=node_data.get("properties", {}),
                bio=node_data.get("bio"),
            )
        except Exception as e:
            print(f"Error parsing node: {e}")
            return None

    def _parse_edge(
        self,
        edge_data: Any,
        source_data: Any,
        target_data: Any,
    ) -> Edge | None:
        """Parse edge dictionary into Edge model."""
        if not isinstance(edge_data, dict):
            return None

        try:
            return Edge(
                id=edge_data.get("id", ""),
                source=edge_data.get(
                    "source",
                    source_data.get("id", "") if isinstance(source_data, dict) else "",
                ),
                target=edge_data.get(
                    "target",
                    target_data.get("id", "") if isinstance(target_data, dict) else "",
                ),
                type=edge_data.get("type", EdgeType.HAS_SPECIALISM),
                properties=edge_data.get("properties", {}),
            )
        except Exception as e:
            print(f"Error parsing edge: {e}")
            return None

    def _get_mock_data(self) -> GraphData:
        """Return mock data as fallback."""
        nodes = [
            Node(
                id="n1",
                type=NodeType.PRACTITIONER,
                label="Tomie Ando-Boadman",
                properties={"role": "teacher / performer"},
                bio="Master-level eurythmy performer and teacher.",
            ),
            Node(
                id="n2",
                type=NodeType.PRACTITIONER,
                label="Ursula Werner",
                properties={"role": "therapist"},
                bio="Qualified Eurythmy Therapist.",
            ),
            Node(
                id="n3",
                type=NodeType.SPECIALISM,
                label="Speech Eurythmy",
                properties={"category": "speech"},
            ),
            Node(
                id="n4",
                type=NodeType.SEEK,
                label="Anxiety Support",
                properties={"category": "therapeutic"},
            ),
        ]
 
        edges = [
            Edge(
                id="e1",
                source="n1",
                target="n3",
                type=EdgeType.HAS_SPECIALISM,
                properties={},
            ),
            Edge(
                id="e2",
                source="n2",
                target="n4",
                type=EdgeType.HAS_SEEK,
                properties={},
            ),
            Edge(
                id="e3",
                source="n3",
                target="n4",
                type=EdgeType.TREATS,
                properties={"strength": "primary"},
            ),
        ] 
        return GraphData(nodes=nodes, edges=edges)

