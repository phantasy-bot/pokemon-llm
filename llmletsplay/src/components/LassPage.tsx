import { Sidebar } from './Sidebar'
import { FolderContainer } from './FolderContainer'
import { About } from './sections/About'
import { Architecture } from './sections/Architecture'
import { ComingSoon } from './sections/ComingSoon'
import { Persona } from './sections/Persona'
import { Tokenomics } from './sections/Tokenomics'
import { Collection } from './sections/Collection'
// import { Battle } from './sections/Battle'  // TODO: Re-enable when battle screen is ready
import { Routes, Route, useNavigate, useLocation } from 'react-router-dom'
import { Icon } from '@iconify/react'
import { 
  PixelHome2, 
  PixelInfo, 
  PixelChip, 
  PixelHierarchy, 
  PixelLoadingCircle, 
  PixelTerminal,
  PixelTV,
  PixelCoin,
  PixelCard
} from './icons/PixelIcons'

const navItems = [
  { id: 'home', label: 'Home', icon: <PixelHome2 size={18} /> },
  { id: 'lass', label: 'Lass Plays Pokemon', icon: <Icon icon="streamline-pixel:photography-focus-flower" width={18} height={18} />, hasDivider: true },
  // { id: 'battle', label: 'Battle Mode', icon: <Icon icon="streamline-pixel:lightning-bolt-pixel" width={18} height={18} />, isSubItem: true },  // TODO: Re-enable
  { id: 'about', label: 'About', icon: <PixelInfo size={18} />, isSubItem: true },
  { id: 'architecture', label: 'Architecture', icon: <PixelChip size={18} />, isSubItem: true },
  { id: 'collection', label: 'Card Collection', icon: <PixelCard size={18} />, isSubItem: true },
  { id: 'prompts', label: 'LLM Prompts', icon: <PixelTerminal size={18} />, isSubItem: true },
  { id: 'memory', label: 'Memory Map', icon: <PixelHierarchy size={18} />, isSubItem: true },
  { id: 'stream', label: 'Stream Cycle', icon: <PixelLoadingCircle size={18} />, isSubItem: true },
  { id: 'tokenomics', label: 'Tokenomics', icon: <PixelCoin size={18} />, isSubItem: true },
  { id: 'livestream', label: 'Watch Stream!', icon: <PixelTV size={18} />, isSubItem: true, isExternal: true, href: 'https://twitch.tv/lassplayspokemon' },
]

const sectionTitles: Record<string, string> = {
  lass: 'Lass ✿',
  // battle: 'Battle!',  // TODO: Re-enable
  about: 'About',
  architecture: 'Architecture',
  memory: 'Memory',
  stream: 'Stream Cycle',
  prompts: 'Prompts',
  tokenomics: 'Tokenomics',
  collection: 'Card Collection',
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
      <main className="main-wrapper" style={{ position: 'relative', overflow: 'hidden' }}>
        <FolderContainer 
          key={location.pathname}
          title={currentTitle} 
          titleStyle={{ fontSize: '64px', letterSpacing: '8px' }}
          navItems={navItems}
          activeSection={activeSection}
          onNavigate={handleNavigate}
        >
          <Routes>
            <Route index element={<Persona />} />
            {/* <Route path="battle" element={<Battle />} /> */}  {/* TODO: Re-enable */}
            <Route path="about" element={<About />} />
            <Route path="architecture" element={<Architecture />} />
            <Route path="memory" element={<ComingSoon title="Memory Map" />} />
            <Route path="stream" element={<ComingSoon title="Stream Cycle" />} />
            <Route path="prompts" element={<ComingSoon title="LLM Prompts" />} />
            <Route path="tokenomics" element={<Tokenomics />} />
            <Route path="collection" element={<Collection />} />
          </Routes>
        </FolderContainer>
      </main>
    </div>
  )
}
