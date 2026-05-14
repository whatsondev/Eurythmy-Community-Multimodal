import React from 'react';
import { Handle, Position, type NodeProps } from 'reactflow';
import { User, Zap, AlertCircle, Package, Map } from 'lucide-react';
import type { NodeType } from '../../types/graph';

interface CustomNodeData {
    label: string;
    type: NodeType;
    isSelected?: boolean;
    isHighlighted?: boolean;
    [key: string]: any;
}

const getNodeIcon = (type: NodeType) => {
    const iconProps = { size: 16, className: "inline mr-2" };

    switch (type) {
        case 'Practitioner':
            return <User {...iconProps} />;
        case 'Specialism':
            return <Zap {...iconProps} />;
        case 'Seek':
            return <AlertCircle {...iconProps} />;
        case 'Material':
            return <Package {...iconProps} />;
        case 'Venue':
            return <Map {...iconProps} />;
        default:
            return null;
    }
};

const getNodeColor = (type: NodeType, isSelected: boolean, isHighlighted: boolean) => {
    if (isSelected) return '#00f5ff';
    if (isHighlighted) return '#00f5ff88';

    switch (type) {
        case 'Practitioner':
            return '#4ade80'; // Green
        case 'Specialism':
            return '#fbbf24'; // Amber
        case 'Seek':
            return '#f87171'; // Red
        case 'Material':
            return '#60a5fa'; // Blue
        case 'Venue':
            return '#a78bfa'; // Purple
        default:
            return '#6b7280'; // Gray
    }
};

export const CustomNode: React.FC<NodeProps<CustomNodeData>> = ({ data }) => {
    const { label, type, isSelected = false, isHighlighted = false } = data;
    const nodeColor = getNodeColor(type, isSelected, isHighlighted);

    return (
        <div
            className="px-4 py-2 rounded-lg border-2 shadow-lg min-w-[120px] transition-all duration-200"
            style={{
                background: isHighlighted ? '#1a1a2e' : '#0f0f23',
                borderColor: isSelected ? '#00f5ff' : nodeColor,
                borderWidth: isSelected ? '2px' : '1px',
                boxShadow: isSelected || isHighlighted
                    ? `0 0 20px ${nodeColor}40`
                    : `0 0 10px ${nodeColor}20`,
            }}
        >
            <Handle type="target" position={Position.Top} className="w-2 h-2" />

            <div className="flex items-center text-white text-sm font-medium">
                <span style={{ color: nodeColor }}>
                    {getNodeIcon(type)}
                </span>
                <span className="truncate max-w-[150px]">{label}</span>
            </div>

            {data.role && (
                <div className="text-xs text-gray-400 mt-1 truncate">
                    {data.role}
                </div>
            )}

            <Handle type="source" position={Position.Bottom} className="w-2 h-2" />
        </div>
    );
};
