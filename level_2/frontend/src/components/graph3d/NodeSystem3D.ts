import * as THREE from 'three';
import { SPACE_THEME } from '../../theme/spaceTheme';
import type { GraphNode, NodeType } from '../../types/graph';
// BUG FIX 1: SurvivorNode import removed — the type is now PractitionerNode.
//            Importing a non-existent type causes a TypeScript compile error.
import type { PractitionerNode } from '../../types/graph';
// import { lowPolyPlanetVertex, lowPolyPlanetFragment } from './Shaders';

interface Node3DStyle {
    geometry: string;
    detailLevel: number;
    baseColor: number;
    accentColor: number;
    emissiveIntensity: number;
    hasAvatarFrame: boolean;
    hasCrystalSpikes?: boolean;
    orbitAnimation: string;
}

// BUG FIX 2: All five keys were old codelab names ('Survivor', 'Skill', 'Need',
// 'Resource', 'Biome'). The backend now returns eurythmy NodeType values
// ('Practitioner', 'Specialism', 'Seek', 'Material', 'Venue').
// When node.type didn't match any key, NODE_3D_CONFIG[node.type] returned
// undefined, and config.geometry immediately threw:
//   TypeError: Cannot read properties of undefined (reading 'geometry')
const NODE_3D_CONFIG: Record<NodeType, Node3DStyle> = {
    'Practitioner': {
        // Icosahedron — people, presence, warmth
        geometry: 'icosahedron',
        detailLevel: 1,
        baseColor: 0xa08888,   // Dusty rose
        accentColor: 0xc07050,
        emissiveIntensity: 0.1,
        hasAvatarFrame: true,
        orbitAnimation: 'gentle-bob',
    },
    'Specialism': {
        // Octahedron — crystalline, knowledge, radiant
        geometry: 'octahedron',
        detailLevel: 0,
        baseColor: 0xffd700,   // Gold
        accentColor: 0xffaa00,
        emissiveIntensity: 0.4,
        hasAvatarFrame: false,
        orbitAnimation: 'slow-spin',
    },
    'Seek': {
        // Tetrahedron — directional, seeking, need
        geometry: 'tetrahedron',
        detailLevel: 0,
        baseColor: 0xf87171,   // Soft red
        accentColor: 0xff4444,
        emissiveIntensity: 0.5,
        hasAvatarFrame: false,
        orbitAnimation: 'pulse',
    },
    'Material': {
        // Dodecahedron — grounded, material substance
        geometry: 'dodecahedron',
        detailLevel: 1,
        baseColor: 0x5a9a8a,   // Teal
        accentColor: 0x4a8a7a,
        emissiveIntensity: 0.2,
        hasAvatarFrame: false,
        orbitAnimation: 'float',
    },
    'Venue': {
        // Icosahedron with crystal spikes — place, containing, architectural
        geometry: 'icosahedron',
        detailLevel: 2,
        baseColor: 0x806070,   // Mauve
        accentColor: 0xa08090,
        emissiveIntensity: 0.05,
        hasAvatarFrame: false,
        hasCrystalSpikes: true,
        orbitAnimation: 'slow-rotate',
    },
};

export class NodeSystem3D {
    private parent: THREE.Object3D;
    private nodeMeshes: Map<string, THREE.Group> = new Map();

    constructor(parent: THREE.Object3D) {
        this.parent = parent;
    }

    public updateNodes(nodes: GraphNode[]) {
        // Simple diffing: remove missing, add new, update existing
        const currentIds = new Set(nodes.map(n => n.id));

        // Remove old
        for (const [id, group] of this.nodeMeshes) {
            if (!currentIds.has(id)) {
                this.parent.remove(group);
                this.nodeMeshes.delete(id);
            }
        }

        // Add/Update
        nodes.forEach(node => {
            if (this.nodeMeshes.has(node.id)) {
                const group = this.nodeMeshes.get(node.id)!;
                if (node.position) {
                    group.position.set(node.position.x, node.position.y, 0);
                }
            } else {
                // BUG FIX 3: Added guard so unknown node types fall back to a
                // default config rather than crashing. Defensive against any
                // future type added to the backend before the frontend is updated.
                if (!NODE_3D_CONFIG[node.type]) {
                    console.warn(`NodeSystem3D: unknown node type "${node.type}", using Specialism fallback.`);
                    (node as any)._resolvedType = 'Specialism';
                } else {
                    (node as any)._resolvedType = node.type;
                }

                const group = this.createNode(node);
                if (node.position) {
                    group.position.set(node.position.x / 2, -node.position.y / 2, 0);
                }
                this.nodeMeshes.set(node.id, group);
                this.parent.add(group);
            }
        });
    }

    private createNode(node: GraphNode): THREE.Group {
        // BUG FIX 4: Use _resolvedType so the fallback from updateNodes is honoured.
        const resolvedType: NodeType = (node as any)._resolvedType ?? node.type;
        const config = NODE_3D_CONFIG[resolvedType];
        const group = new THREE.Group();
        group.userData = { id: node.id, type: node.type };

        // Main Geometry
        let geometry: THREE.BufferGeometry;
        switch (config.geometry) {
            case 'icosahedron':  geometry = new THREE.IcosahedronGeometry(10, config.detailLevel); break;
            case 'octahedron':   geometry = new THREE.OctahedronGeometry(8,  config.detailLevel); break;
            case 'tetrahedron':  geometry = new THREE.TetrahedronGeometry(8,  config.detailLevel); break;
            case 'dodecahedron': geometry = new THREE.DodecahedronGeometry(9, config.detailLevel); break;
            default:             geometry = new THREE.IcosahedronGeometry(10, 1);
        }

        const material = new THREE.MeshStandardMaterial({
            color: config.baseColor,
            metalness: 0.1,
            roughness: 0.8,
            flatShading: true,
            emissive: config.accentColor,
            emissiveIntensity: config.emissiveIntensity,
        });

        const mesh = new THREE.Mesh(geometry, material);
        group.add(mesh);

        // BUG FIX 5: Avatar frame check was 'Survivor' — updated to 'Practitioner'.
        if (config.hasAvatarFrame && node.type === 'Practitioner') {
            this.addAvatarFrame(group, node as PractitionerNode);
        }

        if (config.hasCrystalSpikes) {
            this.addCrystalSpikes(group);
        }

        return group;
    }

    // BUG FIX 6: Parameter type was SurvivorNode — updated to PractitionerNode.
    private addAvatarFrame(group: THREE.Group, _node: PractitionerNode) {
        const frameGeom = new THREE.TorusGeometry(14, 1.5, 8, 32);
        const frameMat = new THREE.MeshStandardMaterial({
            color: 0xffffff, emissive: 0xffffff, emissiveIntensity: 0.2, flatShading: true
        });
        const frame = new THREE.Mesh(frameGeom, frameMat);
        group.add(frame);

        const disc = new THREE.Mesh(
            new THREE.CircleGeometry(11, 32),
            new THREE.MeshBasicMaterial({ color: 0xcccccc })
        );
        disc.position.z = 0.5;
        group.add(disc);
    }

    private addCrystalSpikes(group: THREE.Group) {
        for (let i = 0; i < 6; i++) {
            const spike = new THREE.Mesh(
                new THREE.ConeGeometry(2, 8, 4),
                new THREE.MeshStandardMaterial({ color: SPACE_THEME.colors.crystal.teal, flatShading: true })
            );
            const u = Math.random();
            const v = Math.random();
            const theta = 2 * Math.PI * u;
            const phi = Math.acos(2 * v - 1);
            const x = 10 * Math.sin(phi) * Math.cos(theta);
            const y = 10 * Math.sin(phi) * Math.sin(theta);
            const z = 10 * Math.cos(phi);

            spike.position.set(x, y, z);
            spike.lookAt(0, 0, 0);
            spike.rotateX(Math.PI);
            group.add(spike);
        }
    }

    public getNodeMesh(id: string): THREE.Group | undefined {
        return this.nodeMeshes.get(id);
    }

    public highlightNodes(_ids: string[]) {
        // Implement highlighting (e.g. scale up, brighten emissive)
    }

    public animate(_time: number) {
        // No shader animations needed with standard materials
    }
}
