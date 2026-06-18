import { useState } from 'react'
import {
  Button, Form, Input, Card,
  Typography, Alert, Space, Tag, Divider, Slider,
} from 'antd'
import {
  ApiOutlined, CheckCircleOutlined, CloseCircleOutlined,
  RobotOutlined, SaveOutlined,
} from '@ant-design/icons'
import { useAppStore, type LLMConfig } from '../store'
import { testLlm } from '../api'

const PRESETS: Array<{ label: string; base_url: string; model: string }> = [
  { label: 'OpenAI', base_url: 'https://api.openai.com/v1', model: 'gpt-4o' },
  { label: 'DeepSeek', base_url: 'https://api.deepseek.com/v1', model: 'deepseek-chat' },
  { label: 'OpenRouter', base_url: 'https://openrouter.ai/api/v1', model: 'openai/gpt-4o' },
  { label: 'Ollama (local)', base_url: 'http://localhost:11434/v1', model: 'llama3' },
  { label: 'LM Studio', base_url: 'http://localhost:1234/v1', model: 'local-model' },
  { label: 'Azure OpenAI', base_url: 'https://your-resource.openai.azure.com/v1', model: 'gpt-4o' },
]

interface FormValues {
  base_url: string
  api_key: string
  model: string
  temperature: number
}

export default function AiConfigPanel() {
  const { aiConfig, setAiConfig } = useAppStore()
  const [form] = Form.useForm<FormValues>()
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState<{ ok: boolean; msg: string } | null>(null)

  const initialValues: FormValues = aiConfig ?? {
    base_url: 'https://api.openai.com/v1',
    api_key: '',
    model: 'gpt-4o',
    temperature: 0.7,
  }

  function applyPreset(base_url: string, model: string) {
    form.setFieldsValue({ base_url, model })
    setTestResult(null)
  }

  async function handleTest() {
    let values: FormValues
    try {
      values = await form.validateFields()
    } catch {
      return
    }
    setTesting(true)
    setTestResult(null)
    try {
      const res = await testLlm(values)
      if (res.reachable) {
        setTestResult({ ok: true, msg: `${res.base_url} — 可达` })
      } else {
        setTestResult({ ok: false, msg: `${res.base_url} — 不可达（检查 URL 或服务是否启动）` })
      }
    } catch (e: unknown) {
      setTestResult({ ok: false, msg: e instanceof Error ? e.message : String(e) })
    } finally {
      setTesting(false)
    }
  }

  function handleSave() {
    form.validateFields().then((values) => {
      const cfg: LLMConfig = { ...values }
      setAiConfig(cfg)
      setTestResult({ ok: true, msg: 'AI 配置已保存，Generate 页面可启用 AI 增强生成' })
    })
  }

  return (
    <div style={{ maxWidth: 640, display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <Typography.Text strong>
          <RobotOutlined /> AI 增强生成配置
        </Typography.Text>
        {aiConfig && <Tag color="green">已配置 · {aiConfig.model}</Tag>}
      </div>

      <Typography.Text type="secondary" style={{ fontSize: 12 }}>
        支持任何兼容 OpenAI API 的服务（OpenAI / DeepSeek / OpenRouter / Ollama / LM Studio / Azure）。
        配置保存后，在 Generate 页面可选择 AI 增强模式生成更真实的测试数据。
      </Typography.Text>

      {/* Provider presets */}
      <Card size="small" title="快速选择服务商">
        <Space wrap>
          {PRESETS.map((p) => (
            <Button
              key={p.label}
              size="small"
              onClick={() => applyPreset(p.base_url, p.model)}
            >
              {p.label}
            </Button>
          ))}
        </Space>
      </Card>

      <Form
        form={form}
        initialValues={initialValues}
        layout="vertical"
        style={{ gap: 0 }}
      >
        <Form.Item
          name="base_url"
          label="Base URL"
          rules={[
            { required: true, message: '请填写 Base URL' },
            { pattern: /^https?:\/\//, message: '必须以 http:// 或 https:// 开头' },
          ]}
        >
          <Input placeholder="https://api.openai.com/v1" />
        </Form.Item>

        <Form.Item
          name="api_key"
          label="API Key"
          rules={[{ required: true, message: '请填写 API Key' }]}
        >
          <Input.Password placeholder="sk-..." />
        </Form.Item>

        <Form.Item
          name="model"
          label="Model"
          rules={[{ required: true, message: '请填写模型名称' }]}
        >
          <Input placeholder="gpt-4o" />
        </Form.Item>

        <Form.Item name="temperature" label={`Temperature: ${form.getFieldValue('temperature') ?? 0.7}`}>
          <Slider min={0} max={2} step={0.1} style={{ width: 320 }} />
        </Form.Item>
      </Form>

      {testResult && (
        <Alert
          type={testResult.ok ? 'success' : 'warning'}
          icon={testResult.ok ? <CheckCircleOutlined /> : <CloseCircleOutlined />}
          message={testResult.msg}
          showIcon
          closable
          onClose={() => setTestResult(null)}
        />
      )}

      <Space>
        <Button
          icon={<ApiOutlined />}
          loading={testing}
          onClick={handleTest}
        >
          测试连通性
        </Button>
        <Button
          type="primary"
          icon={<SaveOutlined />}
          onClick={handleSave}
        >
          保存配置
        </Button>
      </Space>

      <Divider style={{ margin: '8px 0' }} />

      <Typography.Text type="secondary" style={{ fontSize: 11 }}>
        注意：AI 增强生成会调用 LLM API，消耗 Token。
        API Key 仅在浏览器内存中保存，不会发送到后端持久化存储。
      </Typography.Text>
    </div>
  )
}
