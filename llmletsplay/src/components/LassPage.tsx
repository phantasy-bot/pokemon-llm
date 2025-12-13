import { useState } from 'react'
import { Sidebar } from './Sidebar'
import { FolderContainer } from './FolderContainer'
import { About } from './sections/About'
import { Architecture } from './sections/Architecture'
import { Memory } from './sections/Memory'
import { StreamCycle } from './sections/StreamCycle'
import { Prompts } from './sections/Prompts'

const navItems = [
  { id: 'about', label: 'About', icon: '📖' },
  { id: 'architecture', label: 'Architecture', icon: '🏗️' },
  { id: 'memory', label: 'Memory Map', icon: '🧠' },
  { id: 'stream', label: 'Stream Cycle', icon: '🔄' },
  { id: 'prompts', label: 'LLM Prompts', icon: '💬' },
]

const sectionTitles: Record<string, string> = {
  about: 'About the Harness',
  architecture: 'System Architecture',
  memory: 'Memory Map',
  stream: 'Stream Cycle',
  prompts: 'LLM Prompts',
}

const sections: Record<string, React.ComponentType> = {
  about: About,
  architecture: Architecture,
  memory: Memory,
  stream: StreamCycle,
  prompts: Prompts,
}

export function LassPage() {
  const [activeSection, setActiveSection] = useState('about')
  const ActiveComponent = sections[activeSection] || About
  const currentTitle = sectionTitles[activeSection] || 'About'

  return (
    <div className="app-container">
      <Sidebar
        navItems={navItems}
        activeSection={activeSection}
        onNavigate={setActiveSection}
      />
      <main className="main-wrapper">
        <FolderContainer title={currentTitle}>
          <ActiveComponent />
        </FolderContainer>
      </main>
    </div>
  )
}
