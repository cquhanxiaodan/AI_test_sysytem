import { createContext, ReactNode, useContext, useEffect, useState } from "react";
import { fetchProjects, Project } from "../api/client";
import { useAuth } from "./AuthContext";

type ProjectContextValue = {
  projects: Project[];
  currentProject: Project | null;
  loading: boolean;
  selectProject: (projectId: string) => void;
  reloadProjects: () => Promise<void>;
};

const ProjectContext = createContext<ProjectContextValue | null>(null);

export function ProjectProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const [projects, setProjects] = useState<Project[]>([]);
  const [currentProjectId, setCurrentProjectId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function reloadProjects() {
    if (!user) return;
    setLoading(true);
    try {
      const items = await fetchProjects();
      setProjects(items);
      setCurrentProjectId((existing) => existing ?? items[0]?.id ?? null);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    reloadProjects();
  }, [user?.id]);

  const currentProject = projects.find((project) => project.id === currentProjectId) ?? projects[0] ?? null;

  return (
    <ProjectContext.Provider
      value={{ projects, currentProject, loading, selectProject: setCurrentProjectId, reloadProjects }}
    >
      {children}
    </ProjectContext.Provider>
  );
}

export function useProjects() {
  const context = useContext(ProjectContext);
  if (!context) throw new Error("useProjects must be used inside ProjectProvider");
  return context;
}
