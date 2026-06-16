import { useState } from 'react'
import {
  Button, InputNumber, Table, Alert, Typography,
  Statistic, Row, Col, Tag, Space, Divider,
} from 'antd'
import { ThunderboltOutlined, CheckCircleOutlined } from '@ant-design/icons'
import { useAppStore } from '../store'
import { generateData } from '../api'

export default function GeneratePanel() {
  const {
    parsedSchema, rowCounts, setRowCount,
    generationResult, setGenerationResult,
  } = useAppStore()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleGenerate() {
    if (!parsedSchema) return
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
    { title: 'Table', dataIndex: 'name', key: 'name', render: (v: string) => <Typography.Text strong>{v}</Typography.Text> },
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

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center gap-3">
        <Typography.Text strong>
          <ThunderboltOutlined /> Generate Data
        </Typography.Text>
        <Button
          type="primary"
          loading={loading}
          onClick={handleGenerate}
          disabled={totalRows === 0}
        >
          Generate {totalRows > 0 ? `(${totalRows} rows)` : ''}
        </Button>
      </div>

      {error && <Alert type="error" message={error} showIcon closable onClose={() => setError(null)} />}

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
                <Statistic title={tbl} value={meta.generated} suffix="rows" valueStyle={{ color: '#52c41a' }} />
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
