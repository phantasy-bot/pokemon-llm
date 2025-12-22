import { useState, useEffect } from 'react'
import { Menu, X, Twitch } from 'lucide-react'

interface NavigationProps {
  children: React.ReactNode
  walletConnect?: React.ReactNode
}

export function Navigation({ children, walletConnect }: NavigationProps) {
  const [isOpen, setIsOpen] = useState(false)

  useEffect(() => {
    if (isOpen) {
      document.body.classList.add('menu-open')
    } else {
      document.body.classList.remove('menu-open')
    }
    return () => document.body.classList.remove('menu-open')
  }, [isOpen])

  return (
    <>
      {/* Mobile Header Bar */}
      {!isOpen && (
        <div className="fixed top-0 left-0 right-0 h-16 bg-white/90 backdrop-blur-sm z-40 flex items-center justify-between px-4 border-b border-black/5 md:hidden">
             <button 
               onClick={() => setIsOpen(true)}
               className="p-2 -ml-2"
             >
               <Menu size={24} />
             </button>
             
             <span className="font-display font-bold text-2xl tracking-tight">CHRONICLE<span className="animate-blink">.</span></span>
             
             <div className="flex items-center">
                {walletConnect}
             </div>
        </div>
      )}

      {/* Desktop Floating Controls */}
      {!isOpen && (
        <>
          <button 
            onClick={() => setIsOpen(true)}
            className="hidden md:flex fixed top-6 left-8 z-40 p-3 bg-black text-white rounded-full hover:shadow-brutal hover:bg-[#FDFBF7] hover:text-black border border-transparent hover:border-black hover:scale-110 active:scale-95 active:shadow-none transition-all"
            title="Open Menu"
          >
            <Menu size={20} />
          </button>
          
          <div className="hidden md:block fixed top-6 right-8 z-50">
            {walletConnect}
          </div>
        </>
      )}

      {/* Main Content Wrapper */}
      <div className={`relative z-0 transition-opacity duration-500 ${isOpen ? 'opacity-0 pointer-events-none' : 'opacity-100'}`}>
        {children}
      </div>

      {/* Full Screen Menu Overlay (Transparent) */}
      <div 
        className={`fixed inset-0 z-50 flex items-center justify-center transition-all duration-500 ${
          isOpen ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none'
        }`}
      >
        {/* No background here, relying on body class change */}

        <button 
          onClick={() => setIsOpen(false)}
          className="absolute top-6 left-4 md:left-8 p-3 text-zinc-400 hover:text-white transition-colors"
        >
          <X size={24} />
        </button>

        <nav className="flex flex-col gap-12 text-center p-8 w-full max-w-lg relative z-10">
          <div className="flex flex-col gap-2 mb-8">
            <span className="text-zinc-500 font-mono text-sm tracking-widest uppercase">Navigation</span>
            <div className="w-12 h-px bg-zinc-700 mx-auto" />
          </div>

          <a href="#" onClick={() => setIsOpen(false)} className="group cursor-pointer">
            <span className="text-5xl md:text-6xl font-display font-bold text-transparent bg-clip-text bg-gradient-to-r from-white to-zinc-400 group-hover:from-blue-400 group-hover:to-blue-600 transition-all">
              CHRONICLE.
            </span>
          </a>

          <a 
            href="https://twitch.tv/lassplayspokemon" 
            target="_blank" 
            rel="noopener noreferrer"
            className="group flex items-center justify-center gap-4 text-white hover:text-[#9146FF] transition-colors"
          >
            <Twitch size={32} />
            <span className="text-3xl md:text-4xl font-display font-bold">STREAM</span>
          </a>

          <a 
            href="https://zora.co" 
            target="_blank" 
            rel="noopener noreferrer"
            className="group flex items-center justify-center gap-4 text-white hover:text-[#0070f3] transition-colors"
          >
            <div className="w-8 h-8 rounded-full border-2 border-current" />
            <span className="text-3xl md:text-4xl font-display font-bold">ZORA</span>
          </a>
        </nav>
      </div>
    </>
  )
}
