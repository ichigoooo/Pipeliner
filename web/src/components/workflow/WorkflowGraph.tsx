'use client';

import { useCallback, useEffect } from 'react';
import {
    ReactFlow,
    MiniMap,
    Controls,
    Background,
    useNodesState,
    useEdgesState,
    addEdge,
    Connection,
    Edge,
    Node,
    BackgroundVariant
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

interface WorkflowGraphProps {
    initialNodes: Node[];
    initialEdges: Edge[];
    onNodeClick?: (event: React.MouseEvent, node: Node) => void;
    onPaneClick?: (event: React.MouseEvent) => void;
}

export function WorkflowGraph({
    initialNodes,
    initialEdges,
    onNodeClick,
    onPaneClick
}: WorkflowGraphProps) {
    const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
    const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

    useEffect(() => {
        setNodes(initialNodes);
        setEdges(initialEdges);
    }, [initialNodes, initialEdges, setNodes, setEdges]);

    const onConnect = useCallback(
        (params: Edge | Connection) => setEdges((eds) => addEdge(params, eds)),
        [setEdges],
    );

    return (
        <div style={{ width: '100%', height: '100%' }}>
            <ReactFlow
                nodes={nodes}
                edges={edges}
                onNodesChange={onNodesChange}
                onEdgesChange={onEdgesChange}
                onConnect={onConnect}
                onNodeClick={onNodeClick}
                onPaneClick={onPaneClick}
                fitView
            >
                <Controls />
                <MiniMap />
                <Background variant={BackgroundVariant.Dots} gap={12} size={1} />
            </ReactFlow>
        </div>
    );
}
