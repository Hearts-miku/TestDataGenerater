import { useRef, useState } from 'react'
import {
  Button, InputNumber, Table, Alert, Typography,
  Statistic, Row, Col, Tag, Space, Divider, Switch,
  Progress, Card, Badge,
} from 'antd'
import {
  ThunderboltOutlined, CheckCircleOutlined, RobotOutlined,
  ApiOutlined,
} from '@ant-design/icons'
import { useAppStore } from '../store'
import { generateData, openGenerateStream, type WsMessage } from '../api'

interface StreamState {
  percent: number
  currentTable: string | null
  log: string[]
  done: boolean
}

export default function GeneratePanel() {
  const {
    parsedSchema, rowCounts, setRowCount,
    generationResult, setGenerationResult,
    aiConfig,
    setWsProgress, wsGenerating, setWsGenerating,
  } = useAppStore()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [streamMode, setStreamMode] = useState(false)
  const [stream, setStream] = useState<StreamState | null>(null)
  const wsRef = useRef<WebSocket | null>(null)

  async function handleGenerate() {
    if (!parsedSchema) return

    if (streamMode) {
      handleGenerateStream()
      return
    }

    setLoading(true)
    setError(null)
    try {
      const result = await generateData(parsedSchema.schema_id, rowCounts)
      setGenerationResult(result)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setLoading(false)
    }
  }

  function handleGenerateStream() {
    if (!parsedSchema) return

    // Close any existing connection
    wsRef.current?.close()
    setStream({ percent: 0, currentTable: null, log: [], done: false })
    setWsGenerating(true)
    setError(null)

    const messages: WsMessage[] = []

    const ws = openGenerateStream(
      parsedSchema.schema_id,
      rowCounts,
      !!aiConfig,
      (msg: WsMessage) => {
        messages.push(msg)
        setWsProgress([...messages])

        if (msg.type === 'progress') {
          setStream((prev) => ({
            percent: msg.percent ?? prev?.percent ?? 0,
            currentTable: msg.table ?? prev?.currentTable ?? null,
            log: [...(prev?.log ?? []), `[${msg.stage ?? ''}] ${msg.table ? msg.table + ' ' : ''}${msg.percent ?? 0}%`],
            done: false,
          }))
        } else if (msg.type === 'done') {
          if (msg.tables) {
            setGenerationResult({
              schema_id: parsedSchema.schema_id,
              tables: msg.tables,
              ai_used: msg.ai_used ?? false,
              generation_meta: { chunk_size: 10000, chunks_total: 1 },
            })
          }
          setStream((prev) => ({
            ...prev!,
            percent: 100,
            done: true,
            log: [...(prev?.log ?? []), '✓ 完成'],
          }))
          setWsGenerating(false)
        } else if (msg.type === 'error') {
          setError(msg.message ?? 'Unknown error')
          setStream((prev) => ({
            ...prev!,
            done: true,
            log: [...(prev?.log ?? []), `✗ ${msg.message}`],
          }))
          setWsGenerating(false)
        }
      },
      () => {
        setWsGenerating(false)
      },
    )
    wsRef.current = ws
  }

  if (!parsedSchema) {
    return (
      <div className="flex items-center justify-center h-48 text-gray-400">
        Parse a DDL schema first to configure generation.
      </div>
    )
  }

  const tableConfig = parsedSchema.tables.map((t) => ({
    key: t.name,
    name: t.name,
    pk: t.primary_key.join(', ') || '—',
    fks: t.foreign_keys.length,
    cols: t.columns.length,
    count: rowCounts[t.name] ?? 10,
  }))

  const columns = [
    {
      title: 'Table',
      dataIndex: 'name',
      key: 'name',
      render: (v: string) => <Typography.Text strong>{v}</Typography.Text>,
    },
    { title: 'PK', dataIndex: 'pk', key: 'pk', width: 100 },
    { title: 'Cols', dataIndex: 'cols', key: 'cols', width: 60 },
    { title: 'FKs', dataIndex: 'fks', key: 'fks', width: 60 },
    {
      title: 'Row count',
      dataIndex: 'count',
      key: 'count',
      width: 130,
      render: (_: number, record: { name: string; count: number }) => (
        <InputNumber
          min={0}
          max={100000}
          value={record.count}
          onChange={(v) => setRowCount(record.name, v ?? 0)}
          size="small"
          style={{ width: 100 }}
        />
      ),
    },
    {
      title: 'Generated',
      key: 'generated',
      width: 100,
      render: (_: unknown, record: { name: string }) => {
        const gen = generationResult?.tables[record.name]
        if (!gen) return <span className="text-gray-300">—</span>
        return (
          <Tag color="green" icon={<CheckCircleOutlined />}>
            {gen.generated}
          </Tag>
        )
      },
    },
  ]

  const totalRows = Object.values(rowCounts).reduce((a, b) => a + b, 0)
  const isGenerating = loading || wsGenerating

  return (
    <div className="flex flex-col gap-4">
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
        <Typography.Text strong>
          <ThunderboltOutlined /> Generate Data
        </Typography.Text>

        <Space size={8}>
          <Typography.Text type="secondary" style={{ fontSize: 12 }}>流式模式</Typography.Text>
          <Switch
            size="small"
            checked={streamMode}
            onChange={setStreamMode}
            checkedChildren={<ApiOutlined />}
          />
          {aiConfig && (
            <Tag color="purple" icon={<RobotOutlined />}>
              AI · {aiConfig.model}
            </Tag>
          )}
        </Space>

        <Button
          type="primary"
          loading={isGenerating}
          onClick={handleGenerate}
          disabled={totalRows === 0}
          icon={streamMode ? <ApiOutlined /> : <ThunderboltOutlined />}
        >
          Generate {totalRows > 0 ? `(${totalRows} rows)` : ''}
        </Button>
      </div>

      {error && (
        <Alert type="error" message={error} showIcon closable onClose={() => setError(null)} />
      )}

      {/* WebSocket streaming progress */}
      {streamMode && stream && (
        <Card
          size="small"
          title={
            <Space>
              {stream.done
                ? <Badge status="success" text="完成" />
                : <Badge status="processing" text={`生成中 · ${stream.currentTable ?? '准备'}`} />}
            </Space>
          }
        >
          <Progress
            percent={stream.percent}
            status={stream.done ? 'success' : 'active'}
            size="small"
          />
          <div
            style={{
              marginTop: 8,
              maxHeight: 80,
              overflowY: 'auto',
              fontFamily: 'monospace',
              fontSize: 11,
              color: '#888',
            }}
          >
            {stream.log.slice(-6).map((line, i) => (
              <div key={i}>{line}</div>
            ))}
          </div>
        </Card>
      )}

      <Table
        dataSource={tableConfig}
        columns={columns}
        pagination={false}
        size="small"
        bordered
      />

      {generationResult && (
        <>
          <Divider />
          <Row gutter={16}>
            {Object.entries(generationResult.tables).map(([tbl, meta]) => (
              <Col key={tbl}>
                <Statistic
                  title={tbl}
                  value={meta.generated}
                  suffix="rows"
                  valueStyle={{ color: '#52c41a' }}
                />
              </Col>
            ))}
          </Row>
          <Space>
            <Tag>ai_used: {String(generationResult.ai_used)}</Tag>
            <Tag>chunk_size: {generationResult.generation_meta.chunk_size}</Tag>
          </Space>
        </>
      )}
    </div>
  )
}
