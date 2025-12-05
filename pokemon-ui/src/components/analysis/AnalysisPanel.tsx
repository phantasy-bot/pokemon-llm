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
  totalActions?: number;
  memoryWrite?: string | null;
  onMemoryWriteClear?: () => void;
}

export function AnalysisPanel({
  logs,
  isProcessing = false,
  totalActions = 0,
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
  const actionEntries = logs.filter((log) => log.is_action).slice(0, 3);

  // Get the latest LLM response entry for main display - prioritize response over vision
  const latestResponseEntry =
    responseEntries.length > 0 ? responseEntries[0] : null;
  const latestVisionEntry = visionEntries.length > 0 ? visionEntries[0] : null;
  const latestEntry =
    latestResponseEntry ||
    latestVisionEntry ||
    (logs.length > 0 ? logs[0] : null);

  const renderThinkingText = () => {
    const text = "THINKING...";
    return (
      <span className="analysis-panel__thinking-text">
        {text.split("").map((char, i) => (
          <span key={i} style={{ animationDelay: `${i * 0.1}s` }}>
            {char}
          </span>
        ))}
      </span>
    );
  };



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
              
              {/* Thinking Animation Overlay */}
              <div className={`analysis-panel__thinking ${isProcessing ? 'active' : ''}`}>
                <div className="analysis-panel__thinking-spinner" />
                {renderThinkingText()}
              </div>
            </div>
          </div>
        </div>

        {/* 2. Recent Actions Section (Show last 3 entries, chronological left-to-right) */}
        <div className="analysis-panel__actions-section">
          <span className="analysis-panel__section-label">RECENT ACTIONS</span>
          <div className="analysis-panel__actions-list">
            {(() => {
                // We want the last 3 entries, but displayed chronological: #189, #190, #191
                // actionEntries is [Latest(#191), Prev(#190), Prev(#189), ...]
                
                // 1. Take top 3 latest
                const top3 = actionEntries.slice(0, 3);
                
                // 2. Reverse them so they are [Oldest, Middle, Newest]
                // Note: If we have fewer than 3, we still want them to fill from the left or right?
                // User wants "#189, #190, #191" -> suggests filling left-to-right with oldest first.
                // If we only have 1 action (#1), it should probably be on the right or left?
                // "at the end of the container" -> Newest is at the end (right).
                
                // Let's ensure we always render 3 slots.
                // If we have [A_191, A_190], top3 is [A_191, A_190].
                // Reversed: [A_190, A_191].
                // We need to pad this to 3 items.
                // Should the empty slots be at the start (left) or end (right)?
                // "Latest action being the highest number at the end of the container"
                // So #191 is at slot 3 (right).
                // So we need [Empty/Oldest, Middle, Latest].
                // If we have 2 actions: [Empty, #190, #191].
                
                // Construct the display array of length 3
                // We prefer to fill from the right (Latest is index 2).
                
                const displayItems = new Array(3).fill(null);
                
                // Fill backwards from the end
                // displayItems[2] = top3[0] (Latest)
                // displayItems[1] = top3[1]
                // displayItems[0] = top3[2]
                
                top3.forEach((action, i) => {
                    const targetIndex = 2 - i; // 0->2, 1->1, 2->0
                    if (targetIndex >= 0) {
                        displayItems[targetIndex] = action;
                    }
                });

                return displayItems.map((action, i) => {
                     // i is 0, 1, 2 (Left to Right)
                     
                     if (action) {
                         // We need the ID for this action.
                         // We know 'action' came from top3.
                         // Find its index in top3 to deduce number?
                         // top3[0] is #Total.
                         // top3[1] is #Total-1.
                         const originalIndex = actionEntries.indexOf(action); // Find its original index in actionEntries
                         const number = totalActions - originalIndex;
                         
                         const rawText = action.text || action.message || "";
                         const cleanText = rawText.replace("Action:", "").trim();
                         const keys = cleanText.split(";").map((k: string) => k.trim()).filter((k: string) => k).map((k: string) => {
                            const upper = k.toUpperCase();
                            if (upper === "START") return "S";
                            if (upper === "SELECT") return "SEL";
                            return upper;
                         });
                         if (keys.length === 0 && cleanText) keys.push(cleanText.charAt(0));

                         return (
                            <div key={action.id} className="analysis-panel__action-item">
                                <span className="analysis-panel__action-number" style={{ opacity: 0.5, fontFamily: 'var(--font-mono)' }}>
                                #{number}
                                </span>
                                <div className="analysis-panel__action-group">
                                {keys.map((k: string, idx: number) => (
                                    <div key={idx} className="analysis-panel__action-square">
                                    {k}
                                    </div>
                                ))}
                                </div>
                            </div>
                        );
                     } else {
                         return (
                            <div key={`empty-${i}`} className="analysis-panel__action-item">
                                <span className="analysis-panel__action-number" style={{ opacity: 0.2, fontFamily: 'var(--font-mono)' }}>
                                #--
                                </span>
                                <div className="analysis-panel__action-group">
                                <div className="analysis-panel__action-square empty" />
                                </div>
                            </div>
                        );
                     }
                });
            })()}
          </div>
        </div>

        {/* 3. Vision Section (Fixed Height, Row Layout) */}
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

