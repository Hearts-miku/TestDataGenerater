import { useState } from 'react'
import {
  Button, Form, Input, InputNumber, Card,
  Typography, Space, Tag, Divider,
} from 'antd'
import {
  DatabaseOutlined, ApiOutlined, CheckCircleOutlined,
  CloseCircleOutlined, SaveOutlined, DeleteOutlined,
} from '@ant-design/icons'
import { useAppStore, type MysqlConfig } from '../store'

interface FormValues {
  host: string
  port: number
  database: string
  user: string
  password: string
}

const DEFAULT: FormValues = {
  host: '127.0.0.1',
  port: 3306,
  database: '',
  user: 'root',
  password: '',
}

export default function MysqlConfigPanel() {
  const { mysqlConfig, setMysqlConfig } = useAppStore()
  const [form] = Form.useForm<FormValues>()
  const [pinging, setPinging] = useState(false)
  const [pingStatus, setPingStatus] = useState<{ ok: boolean; msg: string } | null>(null)

  // Pre-fill from saved config when it exists
  const initialValues: FormValues = mysqlConfig
    ? { ...mysqlConfig }
    : DEFAULT

  async function handlePing() {
    let values: FormValues
    try {
      values = await form.validateFields(['host', 'port', 'database', 'user'])
    } catch {
      return
    }
    const { password } = form.getFieldsValue()
    setPinging(true)
    setPingStatus(null)
    try {
      const res = await fetch('/api/mysql/ping', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...values, password }),
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

  async function handleSave() {
    let values: FormValues
    try {
      values = await form.validateFields()
    } catch {
      return
    }
    const cfg: MysqlConfig = { ...values }
    setMysqlConfig(cfg)
    setPingStatus({ ok: true, msg: '配置已保存，MySQL 写入页面将自动使用此连接' })
  }

  function handleClear() {
    setMysqlConfig(null)
    form.resetFields()
    setPingStatus(null)
  }

  return (
    <div style={{ maxWidth: 560, display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <Typography.Text strong>
          <DatabaseOutlined /> MySQL 连接配置
        </Typography.Text>
        {mysqlConfig && (
          <Tag color="green" icon={<CheckCircleOutlined />}>
            已配置 · {mysqlConfig.user}@{mysqlConfig.host}:{mysqlConfig.port}/{mysqlConfig.database}
          </Tag>
        )}
      </div>

      <Typography.Text type="secondary" style={{ fontSize: 12 }}>
        保存后，「MySQL 写入」页面会自动使用此连接，无需重复填写。密码仅存储在浏览器内存中，刷新页面后需重新输入。
      </Typography.Text>

      <Card size="small">
        <Form
          form={form}
          initialValues={initialValues}
          layout="vertical"
        >
          <div style={{ display: 'flex', gap: 12 }}>
            <Form.Item
              name="host"
              label="Host"
              rules={[{ required: true, message: '请填写主机地址' }]}
              style={{ flex: 2, marginBottom: 12 }}
            >
              <Input placeholder="127.0.0.1" />
            </Form.Item>
            <Form.Item
              name="port"
              label="Port"
              rules={[{ required: true }]}
              style={{ flex: 1, marginBottom: 12 }}
            >
              <InputNumber min={1} max={65535} style={{ width: '100%' }} />
            </Form.Item>
          </div>

          <Form.Item
            name="database"
            label="Database"
            rules={[{ required: true, message: '请填写数据库名' }]}
            style={{ marginBottom: 12 }}
          >
            <Input placeholder="mydb" />
          </Form.Item>

          <div style={{ display: 'flex', gap: 12 }}>
            <Form.Item
              name="user"
              label="用户名"
              rules={[{ required: true, message: '请填写用户名' }]}
              style={{ flex: 1, marginBottom: 12 }}
            >
              <Input placeholder="root" />
            </Form.Item>
            <Form.Item
              name="password"
              label="密码"
              style={{ flex: 1, marginBottom: 12 }}
            >
              <Input.Password placeholder="(留空则无密码)" />
            </Form.Item>
          </div>
        </Form>

        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 4 }}>
          <Button
            icon={<ApiOutlined />}
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

      <Space>
        <Button
          type="primary"
          icon={<SaveOutlined />}
          onClick={handleSave}
        >
          保存配置
        </Button>
        {mysqlConfig && (
          <Button
            danger
            icon={<DeleteOutlined />}
            onClick={handleClear}
          >
            清除配置
          </Button>
        )}
      </Space>

      {mysqlConfig && (
        <>
          <Divider style={{ margin: '4px 0' }} />
          <Card size="small" title="当前已保存配置" style={{ background: '#fafafa' }}>
            <Space direction="vertical" size={2} style={{ fontSize: 13 }}>
              <span><Typography.Text type="secondary">Host：</Typography.Text>{mysqlConfig.host}:{mysqlConfig.port}</span>
              <span><Typography.Text type="secondary">Database：</Typography.Text>{mysqlConfig.database}</span>
              <span><Typography.Text type="secondary">User：</Typography.Text>{mysqlConfig.user}</span>
              <span><Typography.Text type="secondary">Password：</Typography.Text>
                {mysqlConfig.password ? '●●●●●●' : '（未设置）'}
              </span>
            </Space>
          </Card>
        </>
      )}
    </div>
  )
}
