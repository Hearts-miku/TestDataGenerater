import { useState } from 'react'
import { Button, Alert, Typography, Table, Tag, Statistic, Row, Col, Card } from 'antd'
import { PlayCircleOutlined, NodeIndexOutlined, PartitionOutlined } from '@ant-design/icons'
import Editor from '@monaco-editor/react'
import { useAppStore } from '../store'
import { runCypher, getGraphStats } from '../api'

export default function CypherExplorer() {
  const {
    cypherQuery, setCypherQuery,
    cypherResult, setCypherResult,
    cypherError, setCypherError,
  } = useAppStore()

  const [running, setRunning] = useState(false)
  const [stats, setStats] = useState<{
    node_counts: Record<string, number>
    rel_counts: Record<string, number>
  } | null>(null)
  const [loadingStats, setLoadingStats] = useState(false)

  async function handleRun() {
    setRunning(true)
    setCypherError(null)
    try {
      const result = await runCypher(cypherQuery)
      setCypherResult(result)
    } catch (e: unknown) {
      setCypherError(e instanceof Error ? e.message : String(e))
      setCypherResult(null)
    } finally {
      setRunning(false)
    }
  }

  async function handleStats() {
    setLoadingStats(true)
    try {
      const s = await getGraphStats()
      setStats(s)
    } finally {
      setLoadingStats(false)
    }
  }

  // Build table columns dynamically from result rows
  const columns = cypherResult?.rows.length
    ? Object.keys(cypherResult.rows[0]).map((k) => ({
        title: k,
        dataIndex: k,
        key: k,
        render: (v: unknown) => String(v ?? ''),
      }))
    : []

  const tableData = cypherResult?.rows.map((row, i) => ({ ...row, _key: i })) ?? []

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      {/* Toolbar */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
        <Typography.Text strong>
          <NodeIndexOutlined /> Cypher Explorer
        </Typography.Text>
        <Button
          type="primary"
          size="small"
          icon={<PlayCircleOutlined />}
          loading={running}
          onClick={handleRun}
        >
          Run
        </Button>
        <Button
          size="small"
          icon={<PartitionOutlined />}
          loading={loadingStats}
          onClick={handleStats}
        >
          Refresh Stats
        </Button>
        {cypherResult && (
          <Tag color="blue">{cypherResult.count} row{cypherResult.count !== 1 ? 's' : ''}</Tag>
        )}
      </div>

      {/* Stats row */}
      {stats && (
        <Row gutter={8}>
          {Object.entries(stats.node_counts).map(([label, cnt]) => (
            <Col key={label} span={4} style={{ minWidth: 120 }}>
              <Card size="small" style={{ borderColor: '#722ed1' }}>
                <Statistic
                  title={<span style={{ color: '#722ed1', fontSize: 11 }}>:{label}</span>}
                  value={cnt}
                  valueStyle={{ fontSize: 18 }}
                />
              </Card>
            </Col>
          ))}
          {Object.entries(stats.rel_counts).map(([type, cnt]) => (
            <Col key={type} span={4} style={{ minWidth: 120 }}>
              <Card size="small" style={{ borderColor: '#13c2c2' }}>
                <Statistic
                  title={<span style={{ color: '#13c2c2', fontSize: 11 }}>[:{type}]</span>}
                  value={cnt}
                  valueStyle={{ fontSize: 18 }}
                />
              </Card>
            </Col>
          ))}
        </Row>
      )}

      {cypherError && (
        <Alert
          type="error"
          message={cypherError}
          showIcon
          closable
          onClose={() => setCypherError(null)}
        />
      )}

      <div style={{ display: 'flex', gap: 12 }}>
        {/* Query editor */}
        <div style={{ flex: 1, height: 200, border: '1px solid #d9d9d9', borderRadius: 6, overflow: 'hidden' }}>
          <Editor
            language="cypher"
            value={cypherQuery}
            onChange={(v) => setCypherQuery(v ?? '')}
            theme="vs-dark"
            options={{
              minimap: { enabled: false },
              fontSize: 13,
              lineNumbers: 'off',
              scrollBeyondLastLine: false,
              wordWrap: 'on',
              tabSize: 2,
            }}
          />
        </div>
      </div>

      {/* Results table */}
      {cypherResult && columns.length > 0 && (
        <Table
          size="small"
          dataSource={tableData}
          columns={columns}
          rowKey="_key"
          pagination={{ pageSize: 20, size: 'small', showSizeChanger: false }}
          scroll={{ x: true }}
          style={{ marginTop: 4 }}
        />
      )}

      {cypherResult && columns.length === 0 && (
        <Typography.Text type="secondary">No results returned.</Typography.Text>
      )}
    </div>
  )
}
