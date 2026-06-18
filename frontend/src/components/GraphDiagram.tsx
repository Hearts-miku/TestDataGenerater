import { useEffect } from 'react'
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  type Node,
  type Edge,
  Position,
  Handle,
  MarkerType,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import dagre from 'dagre'
import { Typography, Empty, Tag } from 'antd'
import { NodeIndexOutlined, PartitionOutlined } from '@ant-design/icons'
import { useAppStore } from '../store'

// ── Graph node component ──────────────────────────────────────────────────────

function GraphNode({ data }: {
  data: { label: string; properties: { name: string; type_category: string }[]; unique: string[] }
}) {
  return (
    <div style={{
      background: '#fff',
      border: '2px solid #722ed1',
      borderRadius: 12,
      minWidth: 160,
      boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
      fontSize: 12,
    }}>
      <Handle type="target" position={Position.Left} style={{ background: '#722ed1' }} />
      <div style={{
        background: '#722ed1',
        color: '#fff',
        padding: '6px 10px',
        borderRadius: '10px 10px 0 0',
        fontWeight: 600,
        fontSize: 13,
        textAlign: 'center',
      }}>
        :{data.label}
      </div>
      <div style={{ padding: '4px 0' }}>
        {data.properties.map((p) => (
          <div key={p.name} style={{
            padding: '2px 10px',
            display: 'flex',
            justifyContent: 'space-between',
            gap: 8,
            borderBottom: '1px solid #f0f0f0',
          }}>
            <span style={{ fontWeight: data.unique.includes(p.name) ? 700 : 400 }}>
              {data.unique.includes(p.name) ? '★ ' : ''}{p.name}
            </span>
            <span style={{ color: '#999', fontSize: 10 }}>{p.type_category}</span>
          </div>
        ))}
        {data.properties.length === 0 && (
          <div style={{ padding: '4px 10px', color: '#bbb', fontStyle: 'italic' }}>no props</div>
        )}
      </div>
      <Handle type="source" position={Position.Right} style={{ background: '#722ed1' }} />
    </div>
  )
}

const nodeTypes = { graphNode: GraphNode }

// ── Dagre layout ──────────────────────────────────────────────────────────────

function layoutNodes(nodes: Node[], edges: Edge[]) {
  const g = new dagre.graphlib.Graph()
  g.setDefaultEdgeLabel(() => ({}))
  g.setGraph({ rankdir: 'LR', ranksep: 120, nodesep: 60 })

  nodes.forEach((n) => {
    const props = (n.data as { properties: unknown[] }).properties
    g.setNode(n.id, { width: 180, height: Math.max(80, 36 + props.length * 22) })
  })
  edges.forEach((e) => g.setEdge(e.source, e.target))
  dagre.layout(g)

  return nodes.map((n) => {
    const pos = g.node(n.id)
    const h = (n.data as { properties: unknown[] }).properties.length * 22
    return { ...n, position: { x: pos.x - 90, y: pos.y - Math.max(40, 18 + h / 2) } }
  })
}

// ── Main component ────────────────────────────────────────────────────────────

export default function GraphDiagram() {
  const { parsedGraphSchema } = useAppStore()
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([])
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([])

  useEffect(() => {
    if (!parsedGraphSchema) return

    const rawNodes: Node[] = parsedGraphSchema.nodes.map((n) => ({
      id: n.label,
      type: 'graphNode',
      position: { x: 0, y: 0 },
      data: {
        label: n.label,
        properties: n.properties,
        unique: n.unique_properties,
      },
    }))

    const rawEdges: Edge[] = parsedGraphSchema.relationships.map((r, i) => ({
      id: `rel-${i}-${r.type}`,
      source: r.from_label,
      target: r.to_label,
      label: r.type,
      type: 'smoothstep',
      animated: true,
      style: { stroke: '#13c2c2' },
      labelStyle: { fontSize: 10, fill: '#13c2c2', fontWeight: 600 },
      markerEnd: { type: MarkerType.ArrowClosed, color: '#13c2c2' },
    }))

    const laidOut = layoutNodes(rawNodes, rawEdges)
    setNodes(laidOut)
    setEdges(rawEdges)
  }, [parsedGraphSchema, setNodes, setEdges])

  if (!parsedGraphSchema) {
    return (
      <Empty
        description="先在 Cypher Schema 标签页解析 Schema，图将在此自动渲染"
        style={{ padding: 48 }}
      />
    )
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <Typography.Text strong>Graph Schema 图</Typography.Text>
        <Tag color="purple" icon={<NodeIndexOutlined />}>
          {parsedGraphSchema.nodes.length} 个节点
        </Tag>
        <Tag color="cyan" icon={<PartitionOutlined />}>
          {parsedGraphSchema.relationships.length} 条关系
        </Tag>
        <Typography.Text type="secondary" style={{ fontSize: 12 }}>
          ★ = unique property
        </Typography.Text>
      </div>
      <div style={{ height: 520, border: '1px solid #e8e8e8', borderRadius: 8, overflow: 'hidden' }}>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          nodeTypes={nodeTypes}
          fitView
          fitViewOptions={{ padding: 0.2 }}
        >
          <Background />
          <Controls />
          <MiniMap nodeColor="#722ed1" />
        </ReactFlow>
      </div>
    </div>
  )
}
