import { useState, useEffect, useRef } from 'react';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import { Navigation } from '../components/Navigation';
import { WalletConnection } from '../components/WalletConnection';
import { NetworkChecker } from '../components/NetworkChecker';
import { TimelineStrip } from '../components/TimelineStrip';
import { FileText, ArrowLeft, ArrowRight } from 'lucide-react';
import { getFeed, type Drop } from '../lib/api';
import { AnimatePresence, motion } from 'framer-motion';

export function FolderLayout() {
  const [drops, setDrops] = useState<Drop[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [slideDirection, setSlideDirection] = useState<number>(0); // -1 = left, 1 = right, 0 = none
  const [isOpening, setIsOpening] = useState(false);
  const [isClosing, setIsClosing] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();
  const prevPathRef = useRef(location.pathname);
  
  const isContentPage = location.pathname.startsWith('/content/');

  // Fetch feed globally for the timeline strip
  useEffect(() => {
    getFeed().then(data => {
      // Sort ASC (Oldest -> Newest)
      // API returns DESC. Reverse it.
      setDrops(data.reverse());
    }).catch(console.error);
  }, []);

  // Handle folder open/close animations on route change
  useEffect(() => {
    const wasContentPage = prevPathRef.current.startsWith('/content/');
    const isNowContentPage = location.pathname.startsWith('/content/');
    
    if (!wasContentPage && isNowContentPage) {
      // Opening folder (going to content page)
      setIsOpening(true);
      const timer = setTimeout(() => setIsOpening(false), 800);
      return () => clearTimeout(timer);
    }
    
    prevPathRef.current = location.pathname;
  }, [location.pathname]);

  const handleChronicleClick = () => {
    setCurrentIndex(0);
    if (isContentPage) {
      setIsClosing(true);
      setTimeout(() => {
        setIsClosing(false);
        navigate('/');
      }, 600);
    } else {
      navigate('/');
    }
  };

  const handleSelectDrop = (index: number) => {
    if (!isContentPage) {
      setSlideDirection(index > currentIndex ? -1 : 1);
    }
    setCurrentIndex(index);
    if (isContentPage) {
      // Trigger close animation, then navigate
      setIsClosing(true);
      setTimeout(() => {
        setIsClosing(false);
        navigate('/');
      }, 600);
    } else {
      navigate('/');
    }
  };

  const handlePrev = () => {
    if (currentIndex > 0) {
      setSlideDirection(1);  // Reversed: new folder comes from "behind/above"
      setCurrentIndex(curr => curr - 1);
    }
  };

  const handleNext = () => {
    if (currentIndex < drops.length - 1) {
      setSlideDirection(-1);  // Reversed: new folder comes from "front/below"
      setCurrentIndex(curr => curr + 1);
    }
  };

  const handleBackToTimeline = () => {
    // Trigger close animation first, then navigate
    setIsClosing(true);
    setTimeout(() => {
      setIsClosing(false);
      navigate('/');
    }, 600);
  };

  // Folder slide variants for pagination - diagonal movement
  const folderSlideVariants = {
    enter: (direction: number) => ({
      x: direction > 0 ? 80 : -80,           // Reduced horizontal
      y: direction > 0 ? -40 : 40,           // Add vertical: up for "behind", down for "front"
      opacity: 0,
      scale: direction > 0 ? 0.94 : 1.03,    // Smaller from behind, slightly larger from front
    }),
    center: {
      x: 0,
      y: 0,
      opacity: 1,
      scale: 1,
      transition: { 
        duration: 0.4, 
        ease: "easeOut" as const
      }
    },
    exit: (direction: number) => ({
      x: direction < 0 ? 80 : -80,           // Exit opposite direction
      y: direction < 0 ? -40 : 40,
      opacity: 0,
      scale: direction < 0 ? 0.94 : 1.03,
      transition: { duration: 0.35 }
    })
  };

  // Content variants - "slapped down from above" effect with staggered top-then-bottom feel
  // Uses transform-origin top to make it pivot from top edge, creating the "slap" effect
  const contentVariants = {
    enter: {
      opacity: 0,
      y: -80,              // Start above
      scale: 1.06,         // Start slightly larger (closer to viewer)
      rotateX: -15,        // More pronounced tilt - top edge closer to viewer
      transformPerspective: 1200,
    },
    center: {
      opacity: 1,
      y: 0,
      scale: 1,
      rotateX: 0,
      transition: { 
        duration: 0.5,
        delay: 0.1,
        // Stagger the properties: rotateX settles first (top lands), then y/scale (bottom settles)
        rotateX: {
          duration: 0.3,
          delay: 0.1,
          ease: [0.22, 1, 0.36, 1],  // Fast start, smooth end
        },
        y: {
          duration: 0.45,
          delay: 0.15,
          ease: [0.34, 1.56, 0.64, 1],  // Bouncy overshoot for the settling
        },
        scale: {
          duration: 0.4,
          delay: 0.12,
          ease: [0.34, 1.56, 0.64, 1],
        },
        opacity: {
          duration: 0.25,
          delay: 0.08,
        }
      }
    },
    exit: {
      opacity: 0,
      y: 40,
      scale: 0.96,
      rotateX: 5,           // Slight tilt as it exits (bottom lifts first)
      transition: { duration: 0.2 }
    }
  };

  const showLeftArrow = !isContentPage && drops.length > 1 && currentIndex > 0;
  const showRightArrow = !isContentPage && drops.length > 1 && currentIndex < drops.length - 1;

  return (
    <Navigation>
      <div className="min-h-screen p-4 lg:p-8 font-mono relative z-0">
        
        {/* Fixed Wallet Connection (Top Right) */}
        <div className="fixed top-6 right-6 lg:right-8 z-50">
          <WalletConnection />
        </div>

        {/* Fixed Post Count (Bottom Left) */}
        <div className="fixed bottom-6 left-6 lg:left-8 z-50 font-mono text-xs font-bold tracking-widest text-ink/40 pointer-events-none">
          {drops.length > 0 ? (
            isContentPage ? (
              <span>VIEWING MEMORY</span>
            ) : (
              <span>{currentIndex + 1} / {drops.length}</span>
            )
          ) : (
            <span>LOADING...</span>
          )}
        </div>

        <div className="max-w-5xl mx-auto pt-4 pb-20">
          
          {/* Header Section */}
          <div className="flex flex-col lg:flex-row justify-between items-start lg:items-end mb-8 gap-4 pl-12 lg:pl-0">
            <motion.div 
              initial={{ opacity: 0, y: -20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5 }}
            >
              <button onClick={handleChronicleClick} className="block cursor-pointer hover:opacity-80 transition-opacity text-left">
                <h1 className="text-6xl lg:text-8xl font-bold font-display tracking-tighter mb-2 text-ink leading-none">
                  CHRONICLE
                </h1>
              </button>
            </motion.div>
          </div>

          <div className="mb-6">
            <NetworkChecker />
          </div>

          {/* Main Folder Container Wrapper - includes pagination */}
          <div className="relative mt-16">
            
            {/* Back to Timeline Arrow - Only show on content pages */}
            {isContentPage && (
              <div className="hidden lg:flex absolute -left-16 xl:-left-20 top-1/2 -translate-y-1/2 z-20">
                <button 
                  onClick={handleBackToTimeline}
                  className="p-3 bg-white/60 border-2 border-black/20 rounded-full shadow-sm hover:bg-white hover:border-black hover:shadow-brutal-sm hover:-translate-y-0.5 transition-all text-black/30 hover:text-black"
                  title="Back to Timeline"
                >
                  <ArrowLeft size={24} />
                </button>
              </div>
            )}

            {/* Mobile/Tablet Back Arrow - Only show on content pages */}
            {isContentPage && (
              <div className="lg:hidden fixed bottom-5 left-4 z-50">
                <button 
                  onClick={handleBackToTimeline}
                  className="p-2 bg-white border-2 border-black rounded-full shadow-brutal-sm text-black"
                  title="Back to Timeline"
                >
                  <ArrowLeft size={18} />
                </button>
              </div>
            )}

            {/* Desktop Pagination Arrows - Only show when there's something to navigate to */}
            {showLeftArrow && (
              <div className="hidden lg:flex absolute -left-16 xl:-left-20 top-1/2 -translate-y-1/2 z-20">
                <button 
                  onClick={handlePrev}
                  className="p-3 bg-white/60 border-2 border-black/20 rounded-full shadow-sm hover:bg-white hover:border-black hover:shadow-brutal-sm hover:-translate-y-0.5 transition-all text-black/30 hover:text-black"
                  title="Older"
                >
                  <ArrowLeft size={24} />
                </button>
              </div>
            )}

            {showRightArrow && (
              <div className="hidden lg:flex absolute -right-16 xl:-right-20 top-1/2 -translate-y-1/2 z-20">
                <button 
                  onClick={handleNext}
                  className="p-3 bg-white/60 border-2 border-black/20 rounded-full shadow-sm hover:bg-white hover:border-black hover:shadow-brutal-sm hover:-translate-y-0.5 transition-all text-black/30 hover:text-black"
                  title="Newer"
                >
                  <ArrowRight size={24} />
                </button>
              </div>
            )}

            {/* Mobile/Tablet Pagination Arrows - Bottom right, inline with page count */}
            {!isContentPage && drops.length > 1 && (
              <div className="lg:hidden fixed bottom-5 right-4 z-50 flex items-center gap-2">
                <button 
                  onClick={handlePrev}
                  disabled={currentIndex === 0}
                  className="p-2 bg-white border-2 border-black rounded-full shadow-brutal-sm text-black disabled:opacity-30 disabled:shadow-none"
                  title="Older"
                >
                  <ArrowLeft size={18} />
                </button>
                <button 
                  onClick={handleNext}
                  disabled={currentIndex === drops.length - 1}
                  className="p-2 bg-white border-2 border-black rounded-full shadow-brutal-sm text-black disabled:opacity-30 disabled:shadow-none"
                  title="Newer"
                >
                  <ArrowRight size={18} />
                </button>
              </div>
            )}

            {/* 3D Perspective Wrapper */}
            <div className="folder-wrapper">
              
              {/* Folder with Tab - Animated only for pagination, not for opening */}
              <AnimatePresence mode="wait" custom={slideDirection}>
                <motion.div
                  key={`folder-${currentIndex}`}
                  custom={slideDirection}
                  variants={isContentPage ? undefined : folderSlideVariants}
                  initial={isContentPage ? false : "enter"}
                  animate="center"
                  exit={isContentPage ? undefined : "exit"}
                  className="relative"
                >
                  {/* Stacked folders behind (only during animation, simulated via CSS) */}
                  <div className={`folder-stack-effect ${slideDirection !== 0 && !isContentPage ? 'active' : ''}`} />

                  {/* Tab */}
                  <div className={`folder-tab text-xs lg:text-sm uppercase tracking-widest flex items-center gap-3`}>
                    <FileText size={16} />
                    <span className="font-bold hidden lg:inline">LOGS // LASS_PLAYS_POKEMON</span>
                    <span className="font-bold lg:hidden">LOGS</span>
                  </div>

                  {/* Timeline Strip */}
                  <div className="absolute -top-[34px] lg:-top-[42px] right-0 left-[160px] lg:left-[360px] h-[36px] lg:h-[44px] flex items-center justify-end px-4 z-0">
                     <TimelineStrip 
                        drops={drops} 
                        currentIndex={currentIndex} 
                        onSelect={handleSelectDrop} 
                     />
                  </div>
                  
                  {/* Folder Body */}
                  <div className={`folder-container p-6 lg:p-12 relative flex flex-col overflow-hidden ${isOpening ? 'opening' : ''} ${isClosing ? 'closing' : ''} ${isContentPage && !isOpening && !isClosing ? 'opened' : ''} min-h-[600px]`}>
                    <div className="absolute inset-0 bg-[url('/grid.svg')] opacity-5 pointer-events-none rounded-lg" />

                    {/* Animated Content Switcher */}
                    <AnimatePresence mode="wait">
                      <motion.div
                        key={location.pathname}
                        variants={contentVariants}
                        initial="enter"
                        animate="center"
                        exit="exit"
                        className="flex-1 flex flex-col z-10"
                      >
                        <Outlet context={{ drops, currentIndex, setCurrentIndex, handleBackToTimeline }} />
                      </motion.div>
                    </AnimatePresence>

                  </div>
                </motion.div>
              </AnimatePresence>
            </div>
          </div>
        </div>
      </div>
    </Navigation>
  );
}
