import { useState } from 'react'
import { Button, Alert, Typography, Table, Tag, Space } from 'antd'
import { PlayCircleOutlined, DatabaseOutlined } from '@ant-design/icons'
import Editor from '@monaco-editor/react'
import { useAppStore } from '../store'
import { runSql } from '../api'

export default function SqlExplorer() {
  const { sqlQuery, setSqlQuery, queryResult, setQueryResult, queryError, setQueryError } = useAppStore()
  const [loading, setLoading] = useState(false)

  async function handleRun() {
    setLoading(true)
    setQueryError(null)
    try {
      const result = await runSql(sqlQuery)
      setQueryResult(result)
    } catch (e: unknown) {
      setQueryError(e instanceof Error ? e.message : String(e))
      setQueryResult(null)
    } finally {
      setLoading(false)
    }
  }

  const colKeys = queryResult && queryResult.rows.length > 0
    ? Object.keys(queryResult.rows[0])
    : []

  const columns = colKeys.map((col) => ({
    title: col,
    dataIndex: col,
    key: col,
    ellipsis: true,
    render: (v: unknown) => {
      if (v === null || v === undefined) return <span className="text-gray-400 italic">NULL</span>
      if (typeof v === 'boolean') return <Tag color={v ? 'green' : 'red'}>{String(v)}</Tag>
      return String(v)
    },
  }))

  const rows = queryResult
    ? queryResult.rows.map((row, i) => ({ key: i, ...row }))
    : []

  return (
    <div className="flex flex-col gap-4 h-full">
      <div className="flex items-center gap-3">
        <Typography.Text strong>
          <DatabaseOutlined /> SQL Explorer
        </Typography.Text>
        <Button
          type="primary"
          size="small"
          icon={<PlayCircleOutlined />}
          loading={loading}
          onClick={handleRun}
        >
          Run
        </Button>
        {queryResult && (
          <Space size={4}>
            <Tag color="blue">{queryResult.count} rows</Tag>
          </Space>
        )}
      </div>

      <div className="border border-gray-200 rounded overflow-hidden" style={{ height: 180 }}>
        <Editor
          defaultLanguage="sql"
          value={sqlQuery}
          onChange={(v) => setSqlQuery(v ?? '')}
          theme="vs-dark"
          options={{
            minimap: { enabled: false },
            fontSize: 13,
            lineNumbers: 'off',
            scrollBeyondLastLine: false,
            wordWrap: 'on',
          }}
        />
      </div>

      {queryError && (
        <Alert type="error" message={queryError} showIcon closable onClose={() => setQueryError(null)} />
      )}

      {queryResult && (
        <Table
          dataSource={rows}
          columns={columns}
          pagination={{ pageSize: 50, showSizeChanger: true }}
          size="small"
          bordered
          scroll={{ x: 'max-content' }}
          locale={{ emptyText: 'No rows returned' }}
        />
      )}
    </div>
  )
}
