import { Sidebar } from './Sidebar'
import { FolderContainer } from './FolderContainer'
import { About } from './sections/About'
import { Architecture } from './sections/Architecture'
import { Memory } from './sections/Memory'
import { StreamCycle } from './sections/StreamCycle'
import { Prompts } from './sections/Prompts'
import { Routes, Route, useNavigate, useLocation, Navigate } from 'react-router-dom'

const navItems = [
  { id: 'about', label: 'About', icon: '' },
  { id: 'architecture', label: 'Architecture', icon: '' },
  { id: 'memory', label: 'Memory Map', icon: '' },
  { id: 'stream', label: 'Stream Cycle', icon: '' },
  { id: 'prompts', label: 'LLM Prompts', icon: '' },
]

const sectionTitles: Record<string, string> = {
  about: 'About the Harness',
  architecture: 'System Architecture',
  memory: 'Memory Map',
  stream: 'Stream Cycle',
  prompts: 'LLM Prompts',
}

export function LassLayout() {
  const navigate = useNavigate()
  const location = useLocation()
  
  // Extract active section from URL path (e.g. /lass/about -> about)
  const currentPath = location.pathname.split('/').pop() || 'about'
  const activeSection = navItems.find(item => item.id === currentPath)?.id || 'about'
  const currentTitle = sectionTitles[activeSection] || 'About'

  const handleNavigate = (id: string) => {
    navigate(`/lass/${id}`)
  }

  return (
    <div className="app-container">
      <Sidebar
        navItems={navItems}
        activeSection={activeSection}
        onNavigate={handleNavigate}
      />
      <main className="main-wrapper" style={{ padding: '24px', paddingLeft: '0', paddingBottom: '0' }}>
        <FolderContainer title={currentTitle}>
          <Routes>
            <Route index element={<Navigate to="about" replace />} />
            <Route path="about" element={<About />} />
            <Route path="architecture" element={<Architecture />} />
            <Route path="memory" element={<Memory />} />
            <Route path="stream" element={<StreamCycle />} />
            <Route path="prompts" element={<Prompts />} />
          </Routes>
        </FolderContainer>
      </main>
    </div>
  )
}
