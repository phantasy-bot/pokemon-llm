import { Sidebar } from './Sidebar'
import { FolderContainer } from './FolderContainer'
import { About } from './sections/About'
import { Architecture } from './sections/Architecture'
import { Memory } from './sections/Memory'
import { StreamCycle } from './sections/StreamCycle'
import { Prompts } from './sections/Prompts'
import { Persona } from './sections/Persona'
import { Routes, Route, useNavigate, useLocation, Navigate } from 'react-router-dom'

const navItems = [
  { id: 'home', label: 'Home', icon: '🏠' },
  { id: 'persona', label: 'Persona', icon: '👤' },
  { id: 'about', label: 'About', icon: '' },
  { id: 'architecture', label: 'Architecture', icon: '' },
  { id: 'memory', label: 'Memory Map', icon: '' },
  { id: 'stream', label: 'Stream Cycle', icon: '' },
  { id: 'prompts', label: 'LLM Prompts', icon: '' },
]

const sectionTitles: Record<string, string> = {
  persona: 'Lass Persona',
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
  const currentPath = location.pathname.split('/').pop() || 'persona'
  const activeSection = navItems.find(item => item.id === currentPath)?.id || 'persona'
  const currentTitle = sectionTitles[activeSection] || 'Persona'

  const handleNavigate = (id: string) => {
    if (id === 'home') navigate('/')
    else navigate(`/lass/${id}`)
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
            <Route index element={<Navigate to="persona" replace />} />
            <Route path="persona" element={<Persona />} />
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
