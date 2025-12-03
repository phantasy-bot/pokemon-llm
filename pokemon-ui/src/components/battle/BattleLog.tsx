import { useEffect, useState } from "react";
import type { LogEntry } from "../../types/gameTypes";
import { BattleEntry } from "./BattleEntry";
import "./BattleLog.css";

const POKEMON_KEYART = [
  "/keyart/pikachu.png",
  "/keyart/charizard.png",
  "/keyart/bulbasaur.png",
  "/keyart/squirtle.png",
  "/keyart/mewtwo.png",
  "/keyart/eevee.png",
];
const ROTATION_INTERVAL = 15000;

interface BattleLogProps {
  logs: LogEntry[];
  isProcessing?: boolean;
  memoryWrite?: string | null;
  onMemoryWriteClear?: () => void;
}

export function BattleLog({
  logs,
  isProcessing = false,
  memoryWrite,
  onMemoryWriteClear,
}: BattleLogProps) {
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

  // Get the latest Pokemon-related entries (newest at start of array due to prepend)
  const latestEntry = logs.length > 0 ? logs[0] : null;

  // Filter for vision and response entries (important Pokemon analysis)
  const visionEntries = logs.filter((log) => log.is_vision).slice(0, 3);
  const responseEntries = logs.filter((log) => log.is_response).slice(0, 2);

  // Get recent actions from last few entries
  const recentActions = logs
    .filter((log) => log.is_action && log.text)
    .slice(0, 5)
    .map((log) => ({
      id: log.id || `action-${Date.now()}`,
      text: log.text || "",
      actions: extractActions(log.text || ""),
    }));

  return (
    <div className="battle-log-container">
      <div
        key={currentKeyart}
        className="battle-log__keyart"
        style={{ backgroundImage: `url(${POKEMON_KEYART[currentKeyart]})` }}
      />
      <div className="battle-log">
        {/* Current AI Thought - Single, Centered */}
        <div className="battle-log__current">
          {latestEntry ? (
            <BattleEntry key={latestEntry.id} entry={latestEntry} isNew />
          ) : (
            !isProcessing && (
              <div className="battle-log__empty">
                Waiting for Pokemon battle analysis...
              </div>
            )
          )}

          {isProcessing && (
            <div className="battle-log__thinking">
              <span className="battle-log__thinking-text">
                {"Analyzing...".split("").map((char, i) => (
                  <span
                    key={i}
                    className="battle-log__thinking-char"
                    style={{ animationDelay: `${i * 0.12}s` }}
                  >
                    {char}
                  </span>
                ))}
              </span>
            </div>
          )}
        </div>

        {/* Pokemon Vision Analysis Section */}
        {visionEntries.length > 0 && (
          <div className="battle-log__vision-section">
            <span className="battle-log__section-label">VISION ANALYSIS</span>
            <div className="battle-log__vision-list">
              {visionEntries.map((entry) => (
                <div key={entry.id} className="battle-log__vision-entry">
                  <BattleEntry entry={entry} compact />
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Footer: Recent Actions + Memory */}
        <div className="battle-log__footer">
          {/* Recent Actions */}
          {recentActions.some((r) => r.actions.length > 0) && (
            <div className="battle-log__actions-section">
              <span className="battle-log__section-label">RECENT ACTIONS</span>
              <div className="battle-log__action-list">
                {recentActions
                  .filter((r) => r.actions.length > 0)
                  .map((r) => (
                    <div key={r.id} className="battle-log__action-row">
                      {r.actions.map((btn, idx) => (
                        <span key={idx} className="battle-log__action-btn">
                          {btn}
                        </span>
                      ))}
                    </div>
                  ))}
              </div>
            </div>
          )}

          {/* Latest Memory - Persistent */}
          <div className="battle-log__memory-section">
            <span className="battle-log__section-label">LATEST MEMORY</span>
            <p className="battle-log__memory-text">
              {persistedMemory || "No battle memories recorded yet"}
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
