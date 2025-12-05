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
  totalActions?: number;
}

export function AnalysisPanel({
  logs,
  isProcessing = false,
  memoryWrite,
  onMemoryWriteClear,
  totalActions = 0,
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

  // Get recent actions from last few entries
  const recentActions = logs
    .filter((log) => log.is_action && log.text)
    .slice(0, 3)
    .map((log, index) => {
      const actions = extractActions(log.text || "");
      // Calculate action number: most recent gets totalActions, then count backwards
      const actionNumber = Math.max(1, totalActions - (2 - index));

      return {
        id: log.id || `action-${Date.now()}`,
        text: log.text || "",
        actions: actions,
        actionNumber: actionNumber,
      };
    });

  return (
    <div className="analysis-panel-container">
      <div
        key={currentKeyart}
        className="analysis-panel__keyart"
        style={{ backgroundImage: `url(${POKEMON_KEYART[currentKeyart]})` }}
      />
      <div className="analysis-panel">
        {/* Current AI Thought - Single, Centered */}
        <div className="analysis-panel__current">
          {latestEntry ? (
            <LogEntryCard key={latestEntry.id} entry={latestEntry} isNew />
          ) : (
            !isProcessing && (
              <div className="analysis-panel__empty">
                waiting for Pokemon LLM analysis...
              </div>
            )
          )}

          {isProcessing && (
            <div className="analysis-panel__thinking">
              <span className="analysis-panel__thinking-text">
                {"Analyzing...".split("").map((char, i) => (
                  <span
                    key={i}
                    className="analysis-panel__thinking-char"
                    style={{ animationDelay: `${i * 0.12}s` }}
                  >
                    {char}
                  </span>
                ))}
              </span>
            </div>
          )}
        </div>

        {/* Pokemon Vision Analysis Section - Always Show */}
        <div className="analysis-panel__vision-section">
          <span className="analysis-panel__section-label">VISION ANALYSIS</span>

          {/* Two-column layout: screenshot on left, vision content on right */}
          <div className="analysis-panel__vision-row">
            {/* Screenshot column - 35% */}
            <div className="analysis-panel__vision-screenshot-column">
              <VisionScreenshot 
                timestamp={latestVisionEntry?.timestamp?.toString() || Date.now().toString()} 
              />
            </div>

            {/* Vision content column - 65% */}
            <div className="analysis-panel__vision-content-column">
              <div className="analysis-panel__vision-list">
                {visionEntries.length > 0 ? (
                  visionEntries.map((entry) => (
                    <div key={entry.id} className="analysis-panel__vision-entry">
                      <LogEntryCard entry={entry} compact />
                    </div>
                  ))
                ) : (
                  <div className="analysis-panel__vision-placeholder">
                    <div className="analysis-panel__vision-placeholder-text">
                      no vision analysis available yet
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Footer: Recent Actions + Memory */}
        <div className="analysis-panel__footer">
          {/* Recent Actions - Always Show */}
          <div className="analysis-panel__actions-section">
            <span className="analysis-panel__section-label">RECENT ACTIONS</span>
            <div className="analysis-panel__action-list">
              {recentActions.some((r) => r.actions.length > 0) ? (
                recentActions
                  .filter((r) => r.actions.length > 0)
                  .map((r) => (
                    <div key={r.id} className="analysis-panel__action-row">
                      <span className="analysis-panel__action-number">
                        #{r.actionNumber || "?"}
                      </span>
                      {r.actions.map((btn, idx) => (
                        <span key={idx} className="analysis-panel__action-btn">
                          {btn}
                        </span>
                      ))}
                    </div>
                  ))
              ) : (
                <div className="analysis-panel__actions-placeholder">
                  <span className="analysis-panel__actions-placeholder-text">
                    no recent actions
                  </span>
                </div>
              )}
            </div>
          </div>

          {/* Latest Memory - Persistent */}
          <div className="analysis-panel__memory-section">
            <span className="analysis-panel__section-label">LATEST MEMORY</span>
            <p className="analysis-panel__memory-text">
              {persistedMemory || "no memories recorded yet"}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

// Helper function to extract actions from text (adapted from Vue app)
function extractActions(text: string): string[] {
  const actionSequenceRegex =
    /(Action:\s*)([ABUDLRS][\s;ABUDLRS]*?)(?=[^ABUDLRS\s;]|$)/g;
  const actions: string[] = [];

  let match;
  while ((match = actionSequenceRegex.exec(text)) !== null) {
    const sequence = match[2];
    const cleanedActions = sequence
      .replace(/;/g, "")
      .replace(/\s+/g, " ")
      .trim()
      .split("");

    actions.push(...cleanedActions);
  }

  return actions;
}
