import { useEffect, useState, useRef, useCallback } from "react";
import type { LogEntry } from "../../types/gameTypes";
import { LogEntryCard } from "./LogEntry";
import { VisionScreenshot } from "../vision/VisionScreenshot"; // Restored
import { RecentActions } from "../shared/RecentActions";
import { TypewriterText } from "../shared/TypewriterText";
import "./AnalysisPanel.css";

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
  isProcessing?: boolean;
  processingStatus?: string; // e.g., "ANALYZING VISION...", "THINKING..."
  memoryWrite?: string | null;
  onMemoryWriteClear?: () => void;
  debugMode?: boolean;
}

export function AnalysisPanel({
  logs,
  totalActions,
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


  // Get the latest LLM response entry for main display - prioritize response over vision
  const latestResponseEntry =
    responseEntries.length > 0 ? responseEntries[0] : null;
  const latestVisionEntry = visionEntries.length > 0 ? visionEntries[0] : null;
  
  // Determine the entry to show
  const rawLatestEntry =
    latestResponseEntry ||
    latestVisionEntry ||
    (logs.length > 0 ? logs[0] : null);

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

  // Note: Thinking animation moved to OBS widget (obs-widgets/status_widget.html)

  return (
    <div className="analysis-panel-container">
      <div
        key={currentKeyart}
        className="analysis-panel__keyart"
        style={{ backgroundImage: `url(${POKEMON_KEYART[currentKeyart]})` }}
      />
      <div className="analysis-panel">
        
        {/* 1. History / LLM Analysis Section (Flex Grow) */}
        <div className="analysis-panel__llm-analysis-wrapper">
          <span className="analysis-panel__section-label">LLM ANALYSIS</span>
          
          {/* Processing Status Indicator - shows when agent is working */}
          {processingStatus && (
            <div className="analysis-panel__status-indicator">
              <span className="analysis-panel__status-pulse" />
              <span className="analysis-panel__status-text">{processingStatus}</span>
            </div>
          )}
          
          <div className="analysis-panel__llm-analysis-scroll" ref={scrollRef}>
            <div className="analysis-panel__list">
              {/* Show only current entry or waiting state */}
              {latestEntry ? (
                <LogEntryCard key={latestEntry.id} entry={latestEntry} isNew onScroll={scrollToBottom} />
              ) : (
                !isProcessing && (
                  <div className="analysis-panel__empty">
                    waiting for Pokemon LLM analysis...
                  </div>
                )
              )}
            </div>
          </div>
        </div>

        {/* 2. Recent Actions Section (Inserted here) */}
        <RecentActions logs={logs} totalActions={totalActions} />

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
              />
            </div>

            {/* Column 2: Content with Sheared Title */}
            <div className="analysis-panel__vision-col-content">
              <div className="analysis-panel__vision-title-internal">
                VISION ANALYSIS
              </div>
              
              {visionEntries.length > 0 ? (
                visionEntries.map((entry) => (
                  <div key={entry.id} className="analysis-panel__vision-entry">
                    <LogEntryCard entry={entry} compact />
                  </div>
                ))
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

