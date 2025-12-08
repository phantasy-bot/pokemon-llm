import { useEffect, useState } from "react";
import type { LogEntry } from "../../types/gameTypes";
import { LogEntryCard } from "./LogEntry";
import { VisionScreenshot } from "../vision/VisionScreenshot"; // Restored
import { RecentActions } from "../shared/RecentActions";
import "./AnalysisPanel.css";

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
  // Note: processingStatus moved to OBS widget (obs-widgets/status_widget.html)
  memoryWrite?: string | null;
  onMemoryWriteClear?: () => void;
  debugMode?: boolean;
}

export function AnalysisPanel({
  logs,
  totalActions,
  isProcessing = false,
  memoryWrite,
  onMemoryWriteClear,
  debugMode = false,
}: AnalysisPanelProps) {
  // @ts-expect-error - Parameter not used yet
  const _onMemoryWriteClear = onMemoryWriteClear;
  // @ts-expect-error - Parameter kept for future use
  const _isProcessing = isProcessing;

  const [currentKeyart, setCurrentKeyart] = useState(0);
  const [persistedMemory, setPersistedMemory] = useState<string | null>(null);

  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentKeyart((prev) => (prev + 1) % POKEMON_KEYART.length);
    }, ROTATION_INTERVAL);
    return () => clearInterval(interval);
  }, []);

  // Persist memory - update when new memory arrives, keep visible until replaced
  useEffect(() => {
    if (memoryWrite) {
      setPersistedMemory(memoryWrite);
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

  // Filter entry based on debug mode (Summary View vs Full View)
  const latestEntry = (() => {
    if (!rawLatestEntry) return null;
    if (debugMode) return rawLatestEntry; // Debug mode = show everything
    
    // In normal mode, if it's an LLM response, try to extract sections
    if (rawLatestEntry.is_response) {
       // Try to find SUMMARY section (can be section 9 or 10 depending on prompt version)
       const summaryMatch = rawLatestEntry.text?.match(/(?:^|\n)\d+\.\s*SUMMARY[\s\S]*$/i);
       
       if (summaryMatch) {
         let summaryText = summaryMatch[0];
         // Clean up: remove the section header (e.g., "9. SUMMARY" or "10. SUMMARY")
         summaryText = summaryText.replace(/\d+\.\s*SUMMARY[^\n]*\n?/i, "").trim();
         // Remove </game_analysis> closing tag if caught
         summaryText = summaryText.replace(/<\/game_analysis>/gi, "").trim();
         // Remove JSON action block if present at end
         summaryText = summaryText.replace(/\s*\{"action"[^}]+\}\s*$/i, "").trim();
         // Remove leading dash and bullet points
         summaryText = summaryText.replace(/^\s*-\s*/gm, "").trim();
         
         return {
           ...rawLatestEntry,
           text: summaryText || "Processing..."
         };
       }
       
       // Fallback: Try to extract COMMENTARY section if SUMMARY not found
       const commentaryMatch = rawLatestEntry.text?.match(/(?:^|\n)\d+\.\s*COMMENTARY[\s\S]*?(?=\n\d+\.|<\/game_analysis>|$)/i);
       if (commentaryMatch) {
         let commentaryText = commentaryMatch[0];
         // Clean up the header and bullet points
         commentaryText = commentaryText.replace(/\d+\.\s*COMMENTARY[^\n]*\n?/i, "").trim();
         commentaryText = commentaryText.replace(/^\s*-\s*/gm, "").trim();
         commentaryText = commentaryText.replace(/<\/game_analysis>/gi, "").trim();
         
         return {
           ...rawLatestEntry,
           text: commentaryText || "Processing..."
         };
       }
       
       // Final fallback: Extract just the action from JSON if present
       const actionMatch = rawLatestEntry.text?.match(/\{"action"\s*:\s*"([^"]+)"\}/);
       if (actionMatch) {
         return {
           ...rawLatestEntry,
           text: `Action: ${actionMatch[1]}`
         };
       }
    }
    
    return rawLatestEntry;
  })();

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
        <div className="analysis-panel__history-wrapper">
          <span className="analysis-panel__section-label">LLM ANALYSIS</span>
          <div className="analysis-panel__history-scroll">
            <div className="analysis-panel__list">
              {/* Show only current entry or waiting state */}
              {latestEntry ? (
                <LogEntryCard key={latestEntry.id} entry={latestEntry} isNew />
              ) : (
                !isProcessing && (
                  <div className="analysis-panel__empty">
                    waiting for Pokemon LLM analysis...
                  </div>
                )
              )}
            </div>
          </div>
          
          {/* Status animation moved to OBS widget (obs-widgets/status_widget.html) */}
        </div>

        {/* 2. Recent Actions Section (Inserted here) */}
        <RecentActions logs={logs} totalActions={totalActions} />

        {/* 3. Vision Section (Fixed Height, Row Layout) */}


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
                    waiting for vision input...
                  </span>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* 4. Latest Memory Section (Bottom Anchor) */}
        <div className="analysis-panel__memory-section">
          <span className="analysis-panel__section-label">LATEST MEMORY</span>
          <p className="analysis-panel__memory-text">
            {persistedMemory || "no memories recorded yet"}
          </p>
        </div>

      </div>
    </div>
  );
}

