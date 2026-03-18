'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
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
    BackgroundVariant,
    ReactFlowInstance
} from '@xyflow/react';

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
    const wrapperRef = useRef<HTMLDivElement | null>(null);
    const [canvasHeight, setCanvasHeight] = useState(352);
    const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
    const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);
    const [flowInstance, setFlowInstance] = useState<ReactFlowInstance<Node, Edge> | null>(null);

    useEffect(() => {
        setNodes(initialNodes);
        setEdges(initialEdges);
    }, [initialNodes, initialEdges, setNodes, setEdges]);

    const onConnect = useCallback(
        (params: Edge | Connection) => setEdges((eds) => addEdge(params, eds)),
        [setEdges],
    );

    useEffect(() => {
        if (!flowInstance || initialNodes.length === 0) {
            return;
        }

        const fit = () => {
            flowInstance.fitView({
                padding: 0.2,
                minZoom: 0.4,
                maxZoom: 1.2,
                duration: 0,
            });
        };

        const frameId = window.requestAnimationFrame(fit);
        const timeoutId = window.setTimeout(fit, 120);

        return () => {
            window.cancelAnimationFrame(frameId);
            window.clearTimeout(timeoutId);
        };
    }, [flowInstance, initialNodes, initialEdges]);

    useEffect(() => {
        if (!flowInstance || !wrapperRef.current || typeof ResizeObserver === 'undefined') {
            return;
        }

        const observer = new ResizeObserver(() => {
            flowInstance.fitView({
                padding: 0.2,
                minZoom: 0.4,
                maxZoom: 1.2,
                duration: 0,
            });
        });
        observer.observe(wrapperRef.current);
        return () => observer.disconnect();
    }, [flowInstance]);

    useEffect(() => {
        const wrapper = wrapperRef.current;
        if (!wrapper || typeof ResizeObserver === 'undefined') {
            return;
        }
        const parent = wrapper.parentElement;
        if (!parent) {
            return;
        }
        const updateHeight = () => {
            const nextHeight = Math.max(Math.round(parent.getBoundingClientRect().height), 352);
            setCanvasHeight((current) => (current === nextHeight ? current : nextHeight));
        };
        updateHeight();
        const observer = new ResizeObserver(updateHeight);
        observer.observe(parent);
        return () => observer.disconnect();
    }, []);

    return (
        <div ref={wrapperRef} style={{ width: '100%', height: `${canvasHeight}px` }}>
            <ReactFlow
                nodes={nodes}
                edges={edges}
                onNodesChange={onNodesChange}
                onEdgesChange={onEdgesChange}
                onConnect={onConnect}
                onNodeClick={onNodeClick}
                onPaneClick={onPaneClick}
                onInit={setFlowInstance}
                fitView
            >
                <Controls />
                <MiniMap />
                <Background variant={BackgroundVariant.Dots} gap={12} size={1} />
            </ReactFlow>
        </div>
    );
}
