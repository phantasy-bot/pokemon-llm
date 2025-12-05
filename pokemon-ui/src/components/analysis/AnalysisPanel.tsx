import { useEffect, useState } from "react";
import type { LogEntry } from "../../types/gameTypes";
import { LogEntryCard } from "./LogEntry";
import { VisionScreenshot } from "../vision/VisionScreenshot";
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
  isProcessing?: boolean;
  memoryWrite?: string | null;
  onMemoryWriteClear?: () => void;
}

export function AnalysisPanel({
  logs,
  isProcessing = false,
  memoryWrite,
  onMemoryWriteClear,
}: AnalysisPanelProps) {
  // @ts-expect-error - Parameter not used yet
  const _onMemoryWriteClear = onMemoryWriteClear;
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
  const latestEntry =
    latestResponseEntry ||
    latestVisionEntry ||
    (logs.length > 0 ? logs[0] : null);


  return (
    <div className="analysis-panel-container">
      <div
        key={currentKeyart}
        className="analysis-panel__keyart"
        style={{ backgroundImage: `url(${POKEMON_KEYART[currentKeyart]})` }}
      />
      <div className="analysis-panel">
        
        {/* 1. History / LLM Analysis Section (Flex Grow) */}
        <div className="analysis-panel__history">
          <span className="analysis-panel__section-label">LLM ANALYSIS</span>
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
            
            {/* Thinking Animation Overlay */}
            <div className={`analysis-panel__thinking ${isProcessing ? 'active' : ''}`}>
              <div className="analysis-panel__thinking-spinner" />
              <span className="analysis-panel__thinking-text">THINKING...</span>
            </div>
          </div>
        </div>

        {/* 2. Vision Section (Fixed Height, Row Layout) */}
        <div className="analysis-panel__vision-section">
          <div className="analysis-panel__vision-row">
            {/* Column 1: Screenshot Only */}
            <div className="analysis-panel__vision-col-screenshot">
              <VisionScreenshot 
                timestamp={latestVisionEntry?.timestamp?.toString() || Date.now().toString()} 
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

        {/* 3. Latest Memory Section (Bottom Anchor) */}
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

