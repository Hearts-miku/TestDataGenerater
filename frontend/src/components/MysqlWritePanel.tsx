import { useState } from 'react'
import {
  Button, Form, Input, InputNumber, Switch, Alert,
  Typography, Table, Tag, Space, Divider, Card, Badge,
} from 'antd'
import {
  DatabaseOutlined, ApiOutlined, ThunderboltOutlined,
  CheckCircleOutlined, CloseCircleOutlined,
} from '@ant-design/icons'
import { useAppStore } from '../store'

interface ConnForm {
  host: string
  port: number
  database: string
  user: string
  password: string
  create_tables: boolean
  truncate_before_insert: boolean
}

interface TableResult {
  name: string
  inserted: number
  error: string | null
}

const DEFAULT: ConnForm = {
  host: '127.0.0.1',
  port: 3306,
  database: '',
  user: 'root',
  password: '',
  create_tables: true,
  truncate_before_insert: false,
}

export default function MysqlWritePanel() {
  const { parsedSchema, generationResult, mysqlConfig } = useAppStore()

  // Pre-fill connection fields from saved config; options keep their defaults
  const initialValues: ConnForm = mysqlConfig
    ? { ...DEFAULT, ...mysqlConfig }
    : DEFAULT

  const [form] = Form.useForm<ConnForm>()
  const [pinging, setPinging] = useState(false)
  const [writing, setWriting] = useState(false)
  const [pingStatus, setPingStatus] = useState<{ ok: boolean; msg: string } | null>(null)
  const [writeResults, setWriteResults] = useState<TableResult[] | null>(null)
  const [writeError, setWriteError] = useState<string | null>(null)

  function connBody() {
    const v = form.getFieldsValue()
    return { host: v.host, port: v.port, database: v.database, user: v.user, password: v.password }
  }

  async function handlePing() {
    await form.validateFields(['host', 'port', 'database', 'user'])
    setPinging(true)
    setPingStatus(null)
    try {
      const res = await fetch('/api/mysql/ping', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(connBody()),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail ?? `HTTP ${res.status}`)
      setPingStatus({ ok: true, msg: `连接成功 · MySQL ${data.version}` })
    } catch (e: unknown) {
      setPingStatus({ ok: false, msg: e instanceof Error ? e.message : String(e) })
    } finally {
      setPinging(false)
    }
  }

  async function handleWrite() {
    if (!parsedSchema) return
    await form.validateFields()
    const v = form.getFieldsValue()
    setWriting(true)
    setWriteError(null)
    setWriteResults(null)
    try {
      const res = await fetch('/api/mysql/write', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...connBody(),
          schema_id: parsedSchema.schema_id,
          create_tables: v.create_tables,
          truncate_before_insert: v.truncate_before_insert,
        }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail ?? `HTTP ${res.status}`)
      const rows: TableResult[] = Object.entries(
        data.tables as Record<string, { inserted: number; error: string | null }>
      ).map(([name, r]) => ({ name, inserted: r.inserted, error: r.error }))
      setWriteResults(rows)
    } catch (e: unknown) {
      setWriteError(e instanceof Error ? e.message : String(e))
    } finally {
      setWriting(false)
    }
  }

  const totalInserted = writeResults?.reduce((s, r) => s + r.inserted, 0) ?? 0
  const hasFailure = writeResults?.some((r) => r.error) ?? false
  const canWrite = !!parsedSchema && !!generationResult

  if (!parsedSchema) {
    return (
      <div style={{ textAlign: 'center', padding: 48, color: '#999' }}>
        <DatabaseOutlined style={{ fontSize: 32, marginBottom: 12 }} />
        <br />
        先在「Schema」标签页解析 DDL 并生成数据，再写入 MySQL
      </div>
    )
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16, maxWidth: 640 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
        <Typography.Text strong>
          <DatabaseOutlined /> 写入 MySQL
        </Typography.Text>
        <Tag color="blue">{parsedSchema.tables.length} 张表</Tag>
        {generationResult && (
          <Tag color="green">
            {Object.values(generationResult.tables).reduce((s, v) => s + v.generated, 0)} 行已生成
          </Tag>
        )}
        {!generationResult && (
          <Tag color="orange">请先生成数据</Tag>
        )}
        {mysqlConfig && (
          <Tag color="cyan" icon={<CheckCircleOutlined />}>
            已用保存配置 · {mysqlConfig.user}@{mysqlConfig.host}/{mysqlConfig.database}
          </Tag>
        )}
      </div>

      {/* Connection form */}
      <Card size="small" title={<span><ApiOutlined /> 数据库连接</span>}>
        <Form
          form={form}
          initialValues={initialValues}
          layout="inline"
          style={{ gap: 8, flexWrap: 'wrap' }}
        >
          <Form.Item name="host" label="Host" rules={[{ required: true }]} style={{ marginBottom: 8 }}>
            <Input placeholder="127.0.0.1" style={{ width: 140 }} />
          </Form.Item>
          <Form.Item name="port" label="Port" rules={[{ required: true }]} style={{ marginBottom: 8 }}>
            <InputNumber min={1} max={65535} style={{ width: 80 }} />
          </Form.Item>
          <Form.Item name="database" label="Database" rules={[{ required: true, message: '请填写数据库名' }]} style={{ marginBottom: 8 }}>
            <Input placeholder="mydb" style={{ width: 120 }} />
          </Form.Item>
          <Form.Item name="user" label="User" rules={[{ required: true }]} style={{ marginBottom: 8 }}>
            <Input placeholder="root" style={{ width: 100 }} />
          </Form.Item>
          <Form.Item name="password" label="Password" style={{ marginBottom: 8 }}>
            <Input.Password placeholder="(empty)" style={{ width: 140 }} />
          </Form.Item>
        </Form>

        <div style={{ marginTop: 8, display: 'flex', alignItems: 'center', gap: 12 }}>
          <Button
            icon={<ApiOutlined />}
            size="small"
            loading={pinging}
            onClick={handlePing}
          >
            测试连接
          </Button>
          {pingStatus && (
            <Space size={4}>
              {pingStatus.ok
                ? <CheckCircleOutlined style={{ color: '#52c41a' }} />
                : <CloseCircleOutlined style={{ color: '#ff4d4f' }} />}
              <Typography.Text
                type={pingStatus.ok ? 'success' : 'danger'}
                style={{ fontSize: 12 }}
              >
                {pingStatus.msg}
              </Typography.Text>
            </Space>
          )}
        </div>
      </Card>

      {/* Options */}
      <Card size="small" title="写入选项">
        <Form form={form} layout="horizontal">
          <Form.Item
            name="create_tables"
            label="自动建表"
            valuePropName="checked"
            extra="目标库中不存在的表自动 CREATE TABLE"
          >
            <Switch />
          </Form.Item>
          <Form.Item
            name="truncate_before_insert"
            label="写入前清空"
            valuePropName="checked"
            extra="INSERT 前对每张表执行 TRUNCATE（危险）"
          >
            <Switch />
          </Form.Item>
        </Form>
      </Card>

      {writeError && (
        <Alert type="error" message={writeError} showIcon closable onClose={() => setWriteError(null)} />
      )}

      <Button
        type="primary"
        size="large"
        icon={<ThunderboltOutlined />}
        loading={writing}
        disabled={!canWrite}
        onClick={handleWrite}
      >
        写入 MySQL
      </Button>

      {!canWrite && parsedSchema && !generationResult && (
        <Typography.Text type="secondary" style={{ fontSize: 12 }}>
          请先在「Generate」标签页生成数据
        </Typography.Text>
      )}

      {/* Results */}
      {writeResults && (
        <>
          <Divider style={{ margin: '4px 0' }} />
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Badge
              status={hasFailure ? 'error' : 'success'}
              text={
                hasFailure
                  ? `部分失败 · ${totalInserted} 行已写入`
                  : `写入完成 · ${totalInserted} 行`
              }
            />
          </div>
          <Table
            size="small"
            dataSource={writeResults}
            rowKey="name"
            pagination={false}
            columns={[
              { title: '表名', dataIndex: 'name', key: 'name', render: (v) => <code>{v}</code> },
              {
                title: '写入行数',
                dataIndex: 'inserted',
                key: 'inserted',
                align: 'right',
                render: (v) => <Tag color={v > 0 ? 'green' : 'default'}>{v}</Tag>,
              },
              {
                title: '状态',
                dataIndex: 'error',
                key: 'error',
                render: (err) =>
                  err
                    ? <Typography.Text type="danger" style={{ fontSize: 11 }}>{err}</Typography.Text>
                    : <CheckCircleOutlined style={{ color: '#52c41a' }} />,
              },
            ]}
          />
        </>
      )}
    </div>
  )
}
