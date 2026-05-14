// -----------------------------
// NODE TYPES (UPDATED)
// -----------------------------

export type NodeType =
  | 'Practitioner'
  | 'Specialism'
  | 'Seek'
  | 'Material'
  | 'Venue';

// -----------------------------
// EDGE TYPES (UPDATED)
// -----------------------------

export type EdgeType =
  | 'HAS_SPECIALISM'
  | 'HAS_SEEKS'
  | 'FOUND_MATERIAL'
  | 'AT_VENUE'
  | 'CAN_SUPPORT'
  | 'TREATS';

// -----------------------------
// BASE NODE
// -----------------------------

export interface GraphNode {
  id: string;
  type: NodeType;
  label: string;
  properties: Record<string, any>;
  position?: { x: number; y: number };
}

// -----------------------------
// PRACTITIONER NODE
// -----------------------------

export interface PractitionerNode extends GraphNode {
  type: 'Practitioner';
  properties: {
    name: string;
    callsign?: string;
    role?: string;
    pillar?: string;
    bio?: string;
    venue_id?: string;
    notes?: string;
    status?: string;
    created_at?: string;
  };
}

// -----------------------------
// SPECIALISM NODE
// -----------------------------

export interface SpecialismNode extends GraphNode {
  type: 'Specialism';
  properties: {
    name: string;
    category?: string;
    description?: string;
    pillar?: string;
  };
}

// -----------------------------
// SEEK NODE (Need renamed → Seek)
// -----------------------------

export interface SeekNode extends GraphNode {
  type: 'Seek';
  properties: {
    name: string;
    category?: string;
    description?: string;
  };
}

// -----------------------------
// MATERIAL NODE
// -----------------------------

export interface MaterialNode extends GraphNode {
  type: 'Material';
  properties: {
    name: string;
    type?: string;
    icon?: string;
    venue?: string;
    description?: string;
  };
}

export interface VenueNode extends GraphNode {
  type: 'Venue';
  properties: {
    name: string;
    type?: string;
    pillar?: string;
    description?: string;
    location?: string;
    notes?: string;
  };
  };


// -----------------------------
// EDGE
// -----------------------------

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  type: EdgeType;
  label?: string;
  properties?: Record<string, any>;
}

// -----------------------------
// GRAPH
// -----------------------------

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}