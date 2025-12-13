import { Sidebar } from './Sidebar'
import { FolderContainer } from './FolderContainer'
import { About } from './sections/About'
import { Architecture } from './sections/Architecture'
import { Memory } from './sections/Memory'
import { StreamCycle } from './sections/StreamCycle'
import { Prompts } from './sections/Prompts'
import { Persona } from './sections/Persona'
import { Routes, Route, useNavigate, useLocation } from 'react-router-dom'
import { 
  PixelHome, 
  PixelSmile, 
  PixelInfo, 
  PixelChip, 
  PixelSitemap, 
  PixelGamepad, 
  PixelTerminal 
} from './icons/PixelIcons'

const navItems = [
  { id: 'home', label: 'Home', icon: <PixelHome size={18} /> },
  { id: 'lass', label: 'Lass', icon: <PixelSmile size={18} /> },
  { id: 'about', label: 'About', icon: <PixelInfo size={18} /> },
  { id: 'architecture', label: 'Architecture', icon: <PixelChip size={18} /> },
  { id: 'memory', label: 'Memory Map', icon: <PixelSitemap size={18} /> },
  { id: 'stream', label: 'Stream Cycle', icon: <PixelGamepad size={18} /> },
  { id: 'prompts', label: 'LLM Prompts', icon: <PixelTerminal size={18} /> },
]

const sectionTitles: Record<string, string> = {
  lass: 'Lass',
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
  // If /lass or /lass/, segment[2] is undefined -> default to 'lass'
  const pathSegment = location.pathname.split('/')[2]
  const activeSection = navItems.find(item => item.id === pathSegment)?.id || (location.pathname.endsWith('/lass') || location.pathname.endsWith('/lass/') ? 'lass' : '')
  const currentTitle = sectionTitles[activeSection] || 'Lass'

  const handleNavigate = (id: string) => {
    if (id === 'home') navigate('/')
    else if (id === 'lass') navigate('/lass')
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
            <Route index element={<Persona />} />
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
