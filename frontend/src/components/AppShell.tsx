import {
  AppstoreOutlined,
  AuditOutlined,
  ClusterOutlined,
  CommentOutlined,
  ExperimentOutlined,
  FileSearchOutlined,
  FolderOpenOutlined,
  ProfileOutlined,
  SettingOutlined,
} from "@ant-design/icons";
import { Layout, Menu, Typography } from "antd";
import { Outlet, useLocation, useNavigate } from "react-router-dom";
import { ProjectProvider, useProjects } from "../context/ProjectContext";
import { useAuth } from "../context/AuthContext";

const { Header, Sider, Content } = Layout;

const menuItems = [
  { key: "/", icon: <AppstoreOutlined />, label: "项目工作台" },
  { key: "/projects", icon: <ClusterOutlined />, label: "项目空间" },
  { key: "/documents", icon: <FolderOpenOutlined />, label: "统一资料池" },
  { key: "/test-assets", icon: <ExperimentOutlined />, label: "测试资产" },
  { key: "/requirements", icon: <FileSearchOutlined />, label: "需求分析" },
  { key: "/validation-plans", icon: <ProfileOutlined />, label: "验证方案" },
  { key: "/free-chat", icon: <CommentOutlined />, label: "自由应用" },
  { key: "/settings", icon: <SettingOutlined />, label: "系统设置" },
];

export default function AppShell() {
  const { user, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const selectedKey = menuItems.find((item) => item.key === location.pathname)?.key ?? "/";

  return (
    <ProjectProvider>
      <AppShellLayout selectedKey={selectedKey} onNavigate={navigate} onLogout={logout} />
    </ProjectProvider>
  );
}

function AppShellLayout({
  selectedKey,
  onNavigate,
  onLogout,
}: {
  selectedKey: string;
  onNavigate: (path: string) => void;
  onLogout: () => void;
}) {
  const { currentProject, projects, selectProject } = useProjects();

  return (
    <Layout className="app-shell">
      <Sider breakpoint="lg" collapsedWidth="0" className="app-sider">
        <div className="brand">
          <AuditOutlined />
          <span>AI 测试方案</span>
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[selectedKey]}
          items={menuItems}
          onClick={({ key }) => onNavigate(key)}
        />
      </Sider>
      <Layout>
        <Header className="app-header">
          <select
            className="project-select"
            value={currentProject?.id ?? ""}
            onChange={(event) => selectProject(event.target.value)}
          >
            {projects.map((project) => (
              <option key={project.id} value={project.id}>{project.name}</option>
            ))}
          </select>
          <button className="text-button" onClick={onLogout}>退出登录</button>
        </Header>
        <Content className="app-content">
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
}
