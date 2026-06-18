import { useEffect, useMemo } from 'react'
import {
  ReactFlow, Background, Controls, MiniMap,
  useNodesState, useEdgesState, type Node, type Edge,
  Position, Handle, MarkerType,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import dagre from 'dagre'
import { Empty } from 'antd'
import type { RelationItem } from '../api'

// ── Table node ────────────────────────────────────────────────────────────────

function TableNode({ data }: { data: { label: string } }) {
  return (
    <div style={{
      background: '#fff',
      border: '2px solid #722ed1',
      borderRadius: 8,
      padding: '6px 10px',
      maxWidth: 220,
      fontSize: 12,
      fontWeight: 600,
      color: '#333',
      textAlign: 'center',
      wordBreak: 'break-all',
      boxShadow: '0 2px 6px rgba(0,0,0,0.12)',
    }}>
      <Handle type="target" position={Position.Left} style={{ background: '#722ed1' }} />
      {data.label}
      <Handle type="source" position={Position.Right} style={{ background: '#722ed1' }} />
    </div>
  )
}

const nodeTypes = { tableNode: TableNode }

const NODE_W = 170
const NODE_H = 40

function layout(nodes: Node[], edges: Edge[]): Node[] {
  const g = new dagre.graphlib.Graph()
  g.setDefaultEdgeLabel(() => ({}))
  g.setGraph({ rankdir: 'LR', ranksep: 160, nodesep: 24 })
  nodes.forEach((n) => g.setNode(n.id, { width: NODE_W, height: NODE_H }))
  edges.forEach((e) => g.setEdge(e.source, e.target))
  dagre.layout(g)
  return nodes.map((n) => {
    const p = g.node(n.id)
    return { ...n, position: { x: p.x - NODE_W / 2, y: p.y - NODE_H / 2 } }
  })
}

// ── Graph ─────────────────────────────────────────────────────────────────────

export default function RelationGraph({ relations }: { relations: RelationItem[] }) {
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([])
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([])

  const valid = useMemo(
    () => relations.filter((r) => r.child_table && r.parent_table),
    [relations],
  )

  useEffect(() => {
    const tableSet = new Set<string>()
    valid.forEach((r) => { tableSet.add(r.child_table); tableSet.add(r.parent_table) })

    const rawNodes: Node[] = [...tableSet].map((t) => ({
      id: t, type: 'tableNode', position: { x: 0, y: 0 }, data: { label: t },
    }))
    const rawEdges: Edge[] = valid.map((r, i) => ({
      id: `e${i}-${r.child_table}-${r.parent_table}-${r.child_col}`,
      source: r.child_table,
      target: r.parent_table,
      label: r.child_col && r.parent_col ? `${r.child_col}→${r.parent_col}` : undefined,
      type: 'smoothstep',
      style: { stroke: '#13c2c2' },
      labelStyle: { fontSize: 9, fill: '#13c2c2' },
      markerEnd: { type: MarkerType.ArrowClosed, color: '#13c2c2' },
    }))

    setNodes(layout(rawNodes, rawEdges))
    setEdges(rawEdges)
  }, [valid, setNodes, setEdges])

  if (!valid.length) {
    return (
      <div style={{
        height: 360, border: '1px solid #e8e8e8', borderRadius: 8,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}>
        <Empty description="暂无关系可视化，识别或导入关系后将在此显示" />
      </div>
    )
  }

  return (
    <div style={{ height: 360, border: '1px solid #e8e8e8', borderRadius: 8, overflow: 'hidden' }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        minZoom={0.1}
      >
        <Background />
        <Controls />
        <MiniMap nodeColor="#722ed1" pannable zoomable />
      </ReactFlow>
    </div>
  )
}
