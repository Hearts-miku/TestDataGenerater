import { useState } from 'react'
import { Button, Alert, Typography, Card, Space, Tag, Divider } from 'antd'
import { DownloadOutlined, FileTextOutlined, FileZipOutlined, FileOutlined } from '@ant-design/icons'
import { useAppStore } from '../store'

type Format = 'sql' | 'csv' | 'json'

const FORMAT_OPTIONS: { label: string; value: Format; icon: React.ReactNode; desc: string; contentType: string; ext: string }[] = [
  {
    label: 'SQL INSERT',
    value: 'sql',
    icon: <FileTextOutlined />,
    desc: '带事务的批量 INSERT 脚本',
    contentType: 'text/plain',
    ext: 'sql',
  },
  {
    label: 'CSV (ZIP)',
    value: 'csv',
    icon: <FileZipOutlined />,
    desc: '每表一个 CSV，打包为 ZIP（UTF-8 BOM）',
    contentType: 'application/zip',
    ext: 'zip',
  },
  {
    label: 'JSON',
    value: 'json',
    icon: <FileOutlined />,
    desc: '按表分组的 JSON 对象',
    contentType: 'application/json',
    ext: 'json',
  },
]

export default function ExportPanel() {
  const { parsedSchema, generationResult } = useAppStore()
  const [format, setFormat] = useState<Format>('sql')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleDownload() {
    if (!parsedSchema) return
    setLoading(true)
    setError(null)
    try {
      const resp = await fetch('/api/export', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ schema_id: parsedSchema.schema_id, format }),
      })
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({ detail: `HTTP ${resp.status}` }))
        throw new Error(err.detail ?? `HTTP ${resp.status}`)
      }
      const blob = await resp.blob()
      const opt = FORMAT_OPTIONS.find((o) => o.value === format)!
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `dataforge_export.${opt.ext}`
      a.click()
      URL.revokeObjectURL(url)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setLoading(false)
    }
  }

  const totalGenerated = generationResult
    ? Object.values(generationResult.tables).reduce((s, v) => s + v.generated, 0)
    : 0

  if (!parsedSchema) {
    return (
      <div className="flex items-center justify-center h-32 text-gray-400">
        先解析 DDL 并生成数据，再进行导出
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center gap-2">
        <Typography.Text strong><DownloadOutlined /> 导出数据</Typography.Text>
        {generationResult && (
          <Tag color="blue">{totalGenerated} 行已生成</Tag>
        )}
      </div>

      {error && <Alert type="error" message={error} showIcon closable onClose={() => setError(null)} />}

      <div className="grid grid-cols-3 gap-3">
        {FORMAT_OPTIONS.map((opt) => (
          <Card
            key={opt.value}
            size="small"
            hoverable
            onClick={() => setFormat(opt.value)}
            style={{
              cursor: 'pointer',
              border: format === opt.value ? '2px solid #1890ff' : '1px solid #d9d9d9',
              background: format === opt.value ? '#e6f4ff' : '#fff',
            }}
          >
            <Space direction="vertical" size={2}>
              <Space>
                {opt.icon}
                <Typography.Text strong style={{ fontSize: 13 }}>{opt.label}</Typography.Text>
              </Space>
              <Typography.Text type="secondary" style={{ fontSize: 11 }}>{opt.desc}</Typography.Text>
            </Space>
          </Card>
        ))}
      </div>

      <Divider style={{ margin: '8px 0' }} />

      {generationResult && (
        <div className="flex gap-2 flex-wrap mb-1">
          {Object.entries(generationResult.tables).map(([tbl, meta]) => (
            <Tag key={tbl} color={meta.generated > 0 ? 'green' : 'default'}>
              {tbl}: {meta.generated}行
            </Tag>
          ))}
        </div>
      )}

      <Button
        type="primary"
        icon={<DownloadOutlined />}
        loading={loading}
        onClick={handleDownload}
        disabled={!generationResult || totalGenerated === 0}
        size="large"
      >
        下载 {FORMAT_OPTIONS.find((o) => o.value === format)?.label}
      </Button>

      {!generationResult && (
        <Typography.Text type="secondary" style={{ fontSize: 12 }}>
          请先在「Generate」标签页生成数据后再导出
        </Typography.Text>
      )}
    </div>
  )
}
