import { useState } from 'react'
import { Select, Button, Table, Typography, Space, Tag, Alert, Empty } from 'antd'
import { EyeOutlined, ReloadOutlined } from '@ant-design/icons'
import { useAppStore } from '../store'
import { runSql } from '../api'

const PAGE_SIZE = 50

export default function DataPreview() {
  const { parsedSchema, generationResult } = useAppStore()
  const [selectedTable, setSelectedTable] = useState<string | null>(null)
  const [rows, setRows] = useState<Record<string, unknown>[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const tableNames = parsedSchema?.tables.map((t) => t.name) ?? []

  async function fetchData(table: string) {
    setLoading(true)
    setError(null)
    try {
      const result = await runSql(`SELECT * FROM "${table}" LIMIT ${PAGE_SIZE}`)
      setRows(result.rows)
      setTotal(result.count)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e))
      setRows([])
    } finally {
      setLoading(false)
    }
  }

  function handleTableChange(name: string) {
    setSelectedTable(name)
    fetchData(name)
  }

  const columns = rows.length > 0
    ? Object.keys(rows[0]).map((col) => ({
        title: col,
        dataIndex: col,
        key: col,
        ellipsis: true,
        width: 140,
        render: (v: unknown) => {
          if (v === null || v === undefined) return <span className="text-gray-400 italic text-xs">NULL</span>
          if (typeof v === 'boolean') return <Tag color={v ? 'green' : 'red'}>{String(v)}</Tag>
          return <span className="text-xs">{String(v)}</span>
        },
      }))
    : []

  const dataSource = rows.map((r, i) => ({ key: i, ...r }))

  if (!parsedSchema) {
    return <Empty description="先解析 DDL 再生成数据，然后在此预览" style={{ padding: 48 }} />
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center gap-3">
        <Typography.Text strong><EyeOutlined /> 数据预览</Typography.Text>
        <Select
          placeholder="选择表"
          value={selectedTable}
          onChange={handleTableChange}
          style={{ width: 180 }}
          options={tableNames.map((n) => ({
            label: (
              <Space size={4}>
                {n}
                {generationResult?.tables[n] && (
                  <Tag color="green" style={{ fontSize: 10 }}>
                    {generationResult.tables[n].generated}行
                  </Tag>
                )}
              </Space>
            ),
            value: n,
          }))}
        />
        {selectedTable && (
          <Button
            size="small"
            icon={<ReloadOutlined />}
            onClick={() => fetchData(selectedTable)}
            loading={loading}
          >
            刷新
          </Button>
        )}
        {total > 0 && (
          <Typography.Text type="secondary" style={{ fontSize: 12 }}>
            显示前 {rows.length} 行，共 {total} 行
          </Typography.Text>
        )}
      </div>

      {error && <Alert type="error" message={error} showIcon closable />}

      {selectedTable ? (
        <Table
          dataSource={dataSource}
          columns={columns}
          pagination={{ pageSize: PAGE_SIZE, showSizeChanger: false, showTotal: (t) => `共 ${t} 行` }}
          size="small"
          bordered
          loading={loading}
          scroll={{ x: 'max-content', y: 400 }}
          locale={{ emptyText: '暂无数据，请先生成' }}
        />
      ) : (
        <Empty description="从上方选择表以预览数据" style={{ padding: 32 }} />
      )}
    </div>
  )
}
