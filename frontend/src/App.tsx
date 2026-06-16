import { Layout, Tabs, Typography } from 'antd'
import { CodeOutlined, ThunderboltOutlined, DatabaseOutlined } from '@ant-design/icons'
import SchemaEditor from './components/SchemaEditor'
import GeneratePanel from './components/GeneratePanel'
import SqlExplorer from './components/SqlExplorer'
import 'antd/dist/reset.css'

const { Header, Content } = Layout

const tabs = [
  {
    key: 'schema',
    label: (
      <span>
        <CodeOutlined /> Schema
      </span>
    ),
    children: <SchemaEditor />,
  },
  {
    key: 'generate',
    label: (
      <span>
        <ThunderboltOutlined /> Generate
      </span>
    ),
    children: <GeneratePanel />,
  },
  {
    key: 'explorer',
    label: (
      <span>
        <DatabaseOutlined /> SQL Explorer
      </span>
    ),
    children: <SqlExplorer />,
  },
]

export default function App() {
  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '0 24px' }}>
        <Typography.Title level={4} style={{ margin: 0, color: '#fff' }}>
          DataForge
        </Typography.Title>
        <Typography.Text style={{ color: 'rgba(255,255,255,0.6)', fontSize: 12 }}>
          Test Data Generator
        </Typography.Text>
      </Header>
      <Content style={{ padding: 24 }}>
        <Tabs items={tabs} destroyInactiveTabPane={false} />
      </Content>
    </Layout>
  )
}
