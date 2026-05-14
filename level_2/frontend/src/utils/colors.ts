import type { NodeType } from '../types/graph';

/**
 * Color mappings for different node types and states
 */

export const pillarColors: Record<string, string> = {
    Art: '#bf5fff',        // Purple
    Health: '#00ff9d',     // Green
    Education: '#60a5fa',  // Blue
    Social: '#ff5fdc',     // Pink
    Tools: '#fbbf24',      // Amber
};

export const materialVenueColors: Record<string, string> = {
    CRYO: '#60a5fa',           // Ice blue
    VOLCANIC: '#f87171',       // Lava red
    BIOLUMINESCENT: '#a78bfa', // Glowing purple
    FOSSILIZED: '#fbbf24',     // Amber yellow
};

export const urgencyColors: Record<string, string> = {
    low: '#00ff9d',    // Green
    medium: '#ff9f43', // Orange
    high: '#ff4757',   // Red
};

export const specialismCategoryColors: Record<string, string> = {
    speech: '#ef4444',        // Red
    tone: '#3b82f6',          // Blue
    pedagogical: '#10b981',   // Green
    therapeutic: '#8b5cf6',   // Purple
    performance: '#f59e0b',   // Amber
    instrument: '#06b6d4',    // Cyan
    science: '#64748b',       // Slate
};

export const seekCategoryColors: Record<string, string> = {
    therapeutic: '#8b5cf6',  // Purple
    artistic: '#f59e0b',     // Amber
    educational: '#3b82f6',  // Blue
    social: '#10b981',       // Green
};

export const nodeTypeColors: Record<NodeType, string> = {
    Practitioner: '#00f5ff',  // Cyan
    Specialism: '#bf5fff',    // Purple
    Seek: '#ff4757',          // Red
    Material: '#00ff9d',      // Green
    Venue: '#ff5fdc',         // Pink
};

/**
 * Get glow shadow string for a color
 */
export function getGlowShadow(color: string, intensity: 'sm' | 'md' | 'lg' = 'md'): string {
    const sizes = {
        sm: '0 0 10px',
        md: '0 0 20px',
        lg: '0 0 30px',
    };
    const hex = color.replace('#', '');
    const r = parseInt(hex.substring(0, 2), 16);
    const g = parseInt(hex.substring(2, 4), 16);
    const b = parseInt(hex.substring(4, 6), 16);
    return `${sizes[intensity]} rgba(${r}, ${g}, ${b}, 0.5)`;
}

export function getMaterialVenueColor(venue: string): string {
    return materialVenueColors[venue] || materialVenueColors.CRYO;
}

export function getPillarColor(pillar: string): string {
    return pillarColors[pillar] || pillarColors.Art;
}

export function getUrgencyColor(urgency: string): string {
    return urgencyColors[urgency] || urgencyColors.low;
}

export function getspecialismCategoryColor(category: string): string {
    return specialismCategoryColors[category] || specialismCategoryColors.therapeutic;
}

export function getSeekCategoryColor(category: string): string {
    return seekCategoryColors[category] || seekCategoryColors.therapeutic;
}

export function getNodeColor(type: NodeType): string {
    return nodeTypeColors[type] || nodeTypeColors.Practitioner;
}
