// Extended practitioner-specific types matching the Eurythmy database schema

export type PractitionerRole =
    | 'teacher / performer'
    | 'teacher'
    | 'therapist'
    | 'ensemble / performer'
    | 'student'
    | 'musician'
    | 'scientist'
    | 'artist / researcher'
    | 'practitioner'
    | 'organiser'
    | 'project lead / researcher';

export type Pillar = 'Art' | 'Health' | 'Education' | 'Social' | 'Tools';

export type SpecialismLevel = 'master' | 'qualified' | 'developing';

export type SeekStatus = 'active' | 'inactive' | 'resolved';

export type SpecialismCategory =
    | 'speech'
    | 'tone'
    | 'pedagogical'
    | 'therapeutic'
    | 'performance'
    | 'instrument'
    | 'science';

export type SeekCategory = 'therapeutic' | 'artistic' | 'educational' | 'social';

export type MaterialType = 'power' | 'water' | 'tool' | 'shelter' | 'medical';

export type MaterialVenue = 'CRYO' | 'VOLCANIC' | 'BIOLUMINESCENT' | 'FOSSILIZED';

export interface PractitionerStatus {
    status: 'active' | 'inactive' | 'critical';
    lastSeen?: string;
    health?: number;
}

export interface Connection {
    nodeId: string;
    nodeName: string;
    nodeType: string;
    edgeType: string;
    description?: string;
}

export interface PractitionerConnection extends Connection {
    pillar?: Pillar;
    level?: SpecialismLevel;
    matchScore?: number;
}

export interface SpecialismConnection extends Connection {
    level?: SpecialismLevel;
    category?: SpecialismCategory;
}

export interface SeekConnection extends Connection {
    status?: SeekStatus;
    category?: SeekCategory;
}
