import { useEffect, useMemo } from 'react'
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
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import dagre from 'dagre'
import { Typography, Empty, Tag } from 'antd'
import { KeyOutlined, LinkOutlined } from '@ant-design/icons'
import { useAppStore } from '../store'

// ── Custom table node ─────────────────────────────────────────────────────────

function TableNode({ data }: { data: {
  label: string
  columns: { name: string; type_category: string; primary_key: boolean; foreign_key: boolean }[]
} }) {
  return (
    <div
      style={{
        background: '#fff',
        border: '2px solid #1890ff',
        borderRadius: 8,
        minWidth: 200,
        boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
        fontSize: 12,
      }}
    >
      <Handle type="target" position={Position.Left} style={{ background: '#1890ff' }} />
      <div
        style={{
          background: '#1890ff',
          color: '#fff',
          padding: '6px 10px',
          borderRadius: '6px 6px 0 0',
          fontWeight: 600,
          fontSize: 13,
        }}
      >
        {data.label}
      </div>
      <div style={{ padding: '4px 0' }}>
        {data.columns.map((col) => (
          <div
            key={col.name}
            style={{
              padding: '2px 10px',
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              borderBottom: '1px solid #f0f0f0',
            }}
          >
            {col.primary_key && <KeyOutlined style={{ color: '#faad14', fontSize: 10 }} />}
            {col.foreign_key && <LinkOutlined style={{ color: '#52c41a', fontSize: 10 }} />}
            <span style={{ flex: 1 }}>{col.name}</span>
            <span style={{ color: '#999', fontSize: 10 }}>{col.type_category}</span>
          </div>
        ))}
      </div>
      <Handle type="source" position={Position.Right} style={{ background: '#52c41a' }} />
    </div>
  )
}

const nodeTypes = { tableNode: TableNode }

// ── Dagre auto-layout ─────────────────────────────────────────────────────────

function layoutNodes(nodes: Node[], edges: Edge[]) {
  const g = new dagre.graphlib.Graph()
  g.setDefaultEdgeLabel(() => ({}))
  g.setGraph({ rankdir: 'LR', ranksep: 100, nodesep: 50 })

  nodes.forEach((n) => g.setNode(n.id, { width: 220, height: Math.max(80, 30 + (n.data as {columns: unknown[]}).columns.length * 22) }))
  edges.forEach((e) => g.setEdge(e.source, e.target))

  dagre.layout(g)

  return nodes.map((n) => {
    const pos = g.node(n.id)
    return { ...n, position: { x: pos.x - 110, y: pos.y - pos.height / 2 } }
  })
}

// ── Main component ────────────────────────────────────────────────────────────

export default function ErDiagram() {
  const { parsedSchema } = useAppStore()
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([])
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([])

  const fkSet = useMemo(() => {
    const s = new Set<string>()
    parsedSchema?.tables.forEach((t) => t.foreign_keys.forEach((fk) => s.add(`${t.name}.${fk.column}`)))
    return s
  }, [parsedSchema])

  useEffect(() => {
    if (!parsedSchema) return

    const rawNodes: Node[] = parsedSchema.tables.map((t) => ({
      id: t.name,
      type: 'tableNode',
      position: { x: 0, y: 0 },
      data: {
        label: t.name,
        columns: t.columns.map((c) => ({
          name: c.name,
          type_category: c.type_category,
          primary_key: c.primary_key,
          foreign_key: fkSet.has(`${t.name}.${c.name}`),
        })),
      },
    }))

    const rawEdges: Edge[] = []
    parsedSchema.tables.forEach((t) => {
      t.foreign_keys.forEach((fk) => {
        rawEdges.push({
          id: `${t.name}.${fk.column}->${fk.ref_table}`,
          source: t.name,
          target: fk.ref_table,
          label: `${fk.column} → ${fk.ref_column}`,
          type: 'smoothstep',
          animated: false,
          style: { stroke: '#52c41a' },
          labelStyle: { fontSize: 10, fill: '#666' },
        })
      })
    })

    const laidOut = layoutNodes(rawNodes, rawEdges)
    setNodes(laidOut)
    setEdges(rawEdges)
  }, [parsedSchema, fkSet, setNodes, setEdges])

  if (!parsedSchema) {
    return (
      <Empty
        description="先在 Schema 标签页解析 DDL，ER 图将在此自动渲染"
        style={{ padding: 48 }}
      />
    )
  }

  return (
    <div className="flex flex-col gap-2 h-full">
      <div className="flex items-center gap-3">
        <Typography.Text strong>ER 图</Typography.Text>
        <Tag color="blue">{parsedSchema.tables.length} tables</Tag>
        <Tag color="green">
          {parsedSchema.tables.reduce((n, t) => n + t.foreign_keys.length, 0)} FK edges
        </Tag>
        <Typography.Text type="secondary" style={{ fontSize: 12 }}>
          <KeyOutlined style={{ color: '#faad14' }} /> 主键 &nbsp;
          <LinkOutlined style={{ color: '#52c41a' }} /> 外键列
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
          <MiniMap nodeColor="#1890ff" />
        </ReactFlow>
      </div>
    </div>
  )
}
