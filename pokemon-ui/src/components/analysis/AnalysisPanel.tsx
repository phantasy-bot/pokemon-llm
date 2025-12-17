import { useEffect, useState, useRef, useCallback } from "react";
import type { LogEntry } from "../../types/gameTypes";
import { LogEntryCard } from "./LogEntry";
import { VisionScreenshot } from "../vision/VisionScreenshot"; // Restored
import { RecentActions } from "../shared/RecentActions";
import { TypewriterText } from "../shared/TypewriterText";
import "./AnalysisPanel.css";

// Spinning Pokeball SVG for processing status
function SpinningPokeball() {
  return (
    <svg 
      className="spinning-pokeball" 
      viewBox="0 0 24 24" 
      width="18" 
      height="18"
    >
      <circle cx="12" cy="12" r="11" fill="#fff" stroke="#333" strokeWidth="1"/>
      <path d="M1 12 H23" stroke="#333" strokeWidth="2"/>
      <path d="M1 12 A11 11 0 0 1 23 12" fill="#e53935"/>
      <circle cx="12" cy="12" r="4" fill="#fff" stroke="#333" strokeWidth="2"/>
      <circle cx="12" cy="12" r="2" fill="#333"/>
    </svg>
  );
}

// Animated dots component for loading states
function AnimatedDots() {
  const [dots, setDots] = useState('');
  
  useEffect(() => {
    const interval = setInterval(() => {
      setDots(prev => {
        if (prev === '...') return '';
        return prev + '.';
      });
    }, 800);
    return () => clearInterval(interval);
  }, []);
  
  return <span style={{ display: 'inline-block', width: '1.5em', textAlign: 'left' }}>{dots}</span>;
}
const POKEMON_KEYART = [
  "/keyart/pikachu.png",
  "/keyart/charizard.png",
  "/keyart/bulbasaur.png",
  "/keyart/squirtle.png",
  "/keyart/mewtwo.png",
  "/keyart/eevee.png",
];
const ROTATION_INTERVAL = 15000;

interface AnalysisPanelProps {
  logs: LogEntry[];
  totalActions: number; // For RecentActions component
  animateActions?: number; // Timestamp when to trigger button animations
  isProcessing?: boolean;
  processingStatus?: string; // e.g., "ANALYZING VISION...", "THINKING..."
  memoryWrite?: string | null;
  onMemoryWriteClear?: () => void;
  debugMode?: boolean;
}

export function AnalysisPanel({
  logs,
  totalActions,
  animateActions,
  isProcessing = false,
  processingStatus,
  memoryWrite,
  onMemoryWriteClear,
  debugMode,
}: AnalysisPanelProps) {
  // @ts-expect-error - Parameter not used yet
  const _onMemoryWriteClear = onMemoryWriteClear;
  // @ts-expect-error - Parameter kept for future use
  const _isProcessing = isProcessing;
  // @ts-expect-error - Parameter kept for future use
  const _debugMode = debugMode;

  const [currentKeyart, setCurrentKeyart] = useState(0);
  const [persistedMemory, setPersistedMemory] = useState<string | null>(null);
  
  // Ref for auto-scroll on typewriter updates
  const scrollRef = useRef<HTMLDivElement>(null);
  
  const scrollToBottom = useCallback(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, []);

  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentKeyart((prev) => (prev + 1) % POKEMON_KEYART.length);
    }, ROTATION_INTERVAL);
    return () => clearInterval(interval);
  }, []);

  // Persist memory - update when new memory arrives, keep visible until replaced
  useEffect(() => {
    if (memoryWrite) {
      // Clean up potential garbage (tags, 'None')
      const clean = memoryWrite.replace(/<\/?[^>]+(>|$)/g, "").replace(/^None$/i, "").replace(/NONE/g, "").trim();
      setPersistedMemory(clean.length > 3 ? clean : null);
    }
  }, [memoryWrite]);

  // Filter for different types of entries (show only current/most recent)
  const visionEntries = logs.filter((log) => log.is_vision).slice(0, 1);
  const responseEntries = logs.filter((log) => log.is_response).slice(0, 1);


  // Get the latest LLM response entry for main display
  // IMPORTANT: Only show response entries here - vision entries have their own dedicated section
  // Falling back to vision would cause duplication during the THINKING phase
  const latestResponseEntry =
    responseEntries.length > 0 ? responseEntries[0] : null;
  const latestVisionEntry = visionEntries.length > 0 ? visionEntries[0] : null;
  
  // Only show LLM response entries in this section - no fallback to vision
  const rawLatestEntry = latestResponseEntry;

  // Process the entry to hide COMMENTARY, SUMMARY, and MEMORY_WRITE sections
  // (COMMENTARY is shown in the character panel, SUMMARY/MEMORY_WRITE are redundant)  
  const latestEntry = (() => {
    if (!rawLatestEntry) return null;
    
    // For LLM responses, strip out sections we don't want to display
    if (rawLatestEntry.is_response && rawLatestEntry.text) {
      let cleanedText = rawLatestEntry.text;
      
      // Remove COMMENTARY section (captures until next numbered section or end)
      cleanedText = cleanedText.replace(
        /\n*\d+\.\s*\*?\*?COMMENTARY\*?\*?:?[^\n]*(?:\n(?!\d+\.).*?)*/gi, 
        ''
      );
      
      // Remove SUMMARY section
      cleanedText = cleanedText.replace(
        /\n*\d+\.\s*\*?\*?SUMMARY\*?\*?:?[^\n]*(?:\n(?!\d+\.).*?)*/gi, 
        ''
      );
      
      // Remove MEMORY_WRITE section
      cleanedText = cleanedText.replace(
        /\n*\d+\.\s*\*?\*?MEMORY_WRITE\*?\*?:?[^\n]*(?:\n(?!\d+\.).*?)*/gi, 
        ''
      );
      
      // Also remove trailing </game_analysis> tag if present
      cleanedText = cleanedText.replace(/<\/game_analysis>/gi, '');
      
      return {
        ...rawLatestEntry,
        text: cleanedText.trim()
      };
    }
    
    return rawLatestEntry;
  })();

  // Auto-scroll to bottom when new content arrives
  useEffect(() => {
    scrollToBottom();
  }, [latestEntry, scrollToBottom]);

  // Determine which section should be active - MUTUALLY EXCLUSIVE
  // Priority: Actions (animating) > Vision (analyzing) > LLM (thinking) > None
  const isVisionActive = processingStatus?.toUpperCase().includes('VISION') ?? false;
  const isLlmActive = processingStatus?.toUpperCase().includes('THINKING') ?? false;
  
  
  // Track action animation state locally for immediate response
  const [actionPhase, setActionPhase] = useState<'idle' | 'gathering' | 'sending'>('idle');
  const lastAnimateTrigger = useRef<number | undefined>(undefined);
  
  // Track if typewriter animation is currently running
  // Text should only be dark/visible during typewriter, faded otherwise
  const [isTypewriting, setIsTypewriting] = useState(false);
  
  useEffect(() => {
    if (animateActions && animateActions !== lastAnimateTrigger.current) {
      lastAnimateTrigger.current = animateActions;
      
      // Start Phase 1: Gathering Courage (Highlight ON, Animation Delayed)
      setActionPhase('gathering');
      setIsTypewriting(false);
      
      // Start Phase 2: Sending Actions (Highlight ON, Animation Playing) after 1s
      const gatheringTimer = setTimeout(() => {
        setActionPhase('sending');
        
        // End Phase: Idle after 3s of sending
        const sendingTimer = setTimeout(() => {
          setActionPhase('idle');
        }, 3000);
        
        return () => clearTimeout(sendingTimer);
      }, 1000); // 1000ms gathering courage duration
      
      return () => clearTimeout(gatheringTimer);
    }
  }, [animateActions]);
  
  // Only one section can be active at a time
  // Action is active if we are in gathering OR sending phase
  const isActionActive = actionPhase !== 'idle';
  const activeSection = isActionActive ? 'actions' : isVisionActive ? 'vision' : isLlmActive ? 'llm' : 'none';

  // Override processing status during action phases
  let displayProcessingStatus = processingStatus;
  if (actionPhase === 'gathering') {
    displayProcessingStatus = "gathering courage to act...";
  } else if (actionPhase === 'sending') {
    displayProcessingStatus = "sending actions...";
  }

  return (
    <div className="analysis-panel-container">
      <div
        key={currentKeyart}
        className="analysis-panel__keyart"
        style={{ backgroundImage: `url(${POKEMON_KEYART[currentKeyart]})` }}
      />
      <div className="analysis-panel">
        
        {/* 1. History / LLM Analysis Section (Flex Grow) */}
        <div className={`analysis-panel__llm-analysis-wrapper ${activeSection === 'llm' ? 'analysis-panel__llm-analysis-wrapper--active' : ''}`}>
          <span className="analysis-panel__section-label">LLM ANALYSIS</span>
          
        <div className="analysis-panel__llm-analysis-scroll" ref={scrollRef}>
            <div className="analysis-panel__list">
              {/* Show only current entry or waiting state */}
              {latestEntry ? (
                <div className={`analysis-panel__content-wrapper ${!isTypewriting ? 'analysis-panel__content-wrapper--faded' : ''}`}>
                  <LogEntryCard 
                    key={latestEntry.id} 
                    entry={latestEntry} 
                    isNew 
                    onScroll={scrollToBottom} 
                    onTypewriterStart={() => setIsTypewriting(true)}
                    onTypewriterComplete={() => setIsTypewriting(false)}
                  />
                </div>
              ) : (
                /* No analysis yet - show centered processing status or waiting text */
                <div className="analysis-panel__empty-centered">
                  {processingStatus ? (
                    <div className="analysis-panel__processing-indicator">
                      <SpinningPokeball />
                      <span className="analysis-panel__processing-text">{processingStatus}</span>
                    </div>
                  ) : (
                    <span>waiting for Pokemon LLM analysis<AnimatedDots /></span>
                  )}
                </div>
              )}
            </div>
          </div>
          
          {/* Processing status at bottom - always rendered with fixed height to prevent layout shift */}
          <div className={`analysis-panel__processing-bottom ${latestEntry && displayProcessingStatus ? '' : 'analysis-panel__processing-bottom--hidden'}`}>
            <SpinningPokeball />
            <span className="analysis-panel__processing-text">{displayProcessingStatus || 'IDLE'}</span>
          </div>
        </div>

        {/* 2. Recent Actions Section (Inserted here) */}
        <RecentActions 
          logs={logs} 
          totalActions={totalActions} 
          animateTrigger={animateActions} 
          isWaitingForAction={activeSection === 'none'}
          isActive={activeSection === 'actions'}
          delayMs={1000}
        />

        {/* 3. Latest Memory Section (Above Vision) */}
        <div className="analysis-panel__memory-section">
          <span className="analysis-panel__section-label">LATEST MEMORY</span>
          <p className="analysis-panel__memory-text">
            {persistedMemory ? (
              <TypewriterText 
                text={persistedMemory}
                speed={20}
              />
            ) : (
              <>no memories recorded yet<AnimatedDots /></>
            )}
          </p>
        </div>

        {/* 4. Vision Section (Fixed Height, Row Layout) */}


        <div className="analysis-panel__vision-section">
          <div className="analysis-panel__vision-row">
            {/* Column 1: Screenshot Only */}
            <div className="analysis-panel__vision-col-screenshot">
              <VisionScreenshot 
                base64Data={latestVisionEntry?.screenshot_base64}
                isAnalyzing={isVisionActive}
              />
            </div>

            {/* Column 2: Content with Sheared Title */}
            <div className={`analysis-panel__vision-col-content ${activeSection === 'vision' ? 'analyzing' : ''}`}>
              <div className="analysis-panel__vision-title-internal">
                VISION ANALYSIS
              </div>
              
              {visionEntries.length > 0 ? (
                // Check if we're in the "analyzing" placeholder state (not real analysis yet)
                visionEntries[0].text === "Analyzing screenshot..." ? (
                  <div className="analysis-panel__vision-placeholder">
                    <span className="analysis-panel__vision-placeholder-text">
                      Analyzing screenshot<AnimatedDots />
                    </span>
                  </div>
                ) : (
                  // Real vision analysis data - render normally
                  visionEntries.map((entry) => (
                    <div key={entry.id} className="analysis-panel__vision-entry">
                      <LogEntryCard entry={entry} compact />
                    </div>
                  ))
                )
              ) : (
                <div className="analysis-panel__vision-placeholder">
                  <span className="analysis-panel__vision-placeholder-text">
                    waiting for vision input<AnimatedDots />
                  </span>
                </div>
              )}
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}

