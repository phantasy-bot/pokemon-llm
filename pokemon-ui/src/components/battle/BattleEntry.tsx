import type { LogEntry } from "../../types/gameTypes";
import ReactMarkdown from "react-markdown";
import "./BattleEntry.css";

interface BattleEntryProps {
  entry: LogEntry;
  isNew?: boolean;
  compact?: boolean;
}

function extractLogType(
  entry: LogEntry,
): "vision" | "response" | "action" | "general" {
  if (entry.is_vision) return "vision";
  if (entry.is_response) return "response";
  if (entry.is_action) return "action";
  return "general";
}

function getLogTypeIcon(
  type: "vision" | "response" | "action" | "general",
): string {
  switch (type) {
    case "vision":
      return "👁";
    case "response":
      return "💭";
    case "action":
      return "🎮";
    case "general":
      return "📝";
  }
}

function getLogTypeLabel(
  type: "vision" | "response" | "action" | "general",
): string {
  switch (type) {
    case "vision":
      return "Vision Analysis";
    case "response":
      return "Battle Analysis";
    case "action":
      return "Action";
    case "general":
      return "Log";
  }
}

function truncateText(text: string, maxLength: number = 300): string {
  if (text.length <= maxLength) return text;
  return text.slice(0, maxLength) + "...";
}

export function BattleEntry({
  entry,
  isNew,
  compact = false,
}: BattleEntryProps) {
  const logType = extractLogType(entry);
  const icon = getLogTypeIcon(logType);
  const label = getLogTypeLabel(logType);
  const text = entry.text || entry.message || "";

  // For compact mode, show minimal info
  if (compact) {
    return (
      <div
        className={`battle-entry battle-entry--compact battle-entry--${logType}`}
      >
        <span className="battle-entry__compact-icon">{icon}</span>
        <span className="battle-entry__compact-text">
          {truncateText(text, 100)}
        </span>
      </div>
    );
  }

  return (
    <div
      className={`battle-entry${isNew ? " battle-entry--new" : ""} battle-entry--${logType}`}
    >
      <div className="battle-entry__header">
        <div className="battle-entry__type-info">
          <span className="battle-entry__type-icon">{icon}</span>
          <span className="battle-entry__type-label">{label}</span>
        </div>
        {entry.timestamp && (
          <span className="battle-entry__timestamp">
            {new Date(entry.timestamp).toLocaleTimeString()}
          </span>
        )}
      </div>

      <div className="battle-entry__content">
        {/* Format log text with coordinate and action highlighting */}
        <div className="battle-entry__text">
          <ReactMarkdown>{formatLogText(text)}</ReactMarkdown>
        </div>

        {/* Special sections for vision analysis */}
        {logType === "vision" && (
          <div className="battle-entry__vision-details">
            {text.includes("Pokemon") && (
              <div className="battle-entry__pokemon-indicator">
                <span className="battle-entry__pokemon-icon">⚡</span>
                <span className="battle-entry__pokemon-text">
                  Pokemon detected
                </span>
              </div>
            )}
            {text.includes("[") && text.includes("]") && (
              <div className="battle-entry__coordinate-indicator">
                <span className="battle-entry__coordinate-icon">📍</span>
                <span className="battle-entry__coordinate-text">
                  Location data
                </span>
              </div>
            )}
          </div>
        )}

        {/* Special sections for response analysis */}
        {logType === "response" && (
          <div className="battle-entry__response-details">
            {text.toLowerCase().includes("battle") && (
              <div className="battle-entry__battle-indicator">
                <span className="battle-entry__battle-icon">⚔️</span>
                <span className="battle-entry__battle-text">
                  Battle strategy
                </span>
              </div>
            )}
            {text.toLowerCase().includes("item") ||
              (text.toLowerCase().includes("potion") && (
                <div className="battle-entry__item-indicator">
                  <span className="battle-entry__item-icon">💊</span>
                  <span className="battle-entry__item-text">Item usage</span>
                </div>
              ))}
          </div>
        )}
      </div>

      {/* Action badges for action entries */}
      {logType === "action" && (
        <div className="battle-entry__actions">
          {extractActions(text).map((action, idx) => (
            <span
              key={idx}
              className={`battle-entry__action battle-entry__action--${getActionType(action)}`}
            >
              {action}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

// Helper functions
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

function getActionType(action: string): "button" | "direction" {
  return ["A", "B", "START", "SELECT"].includes(action.toUpperCase())
    ? "button"
    : "direction";
}

// Format log text with highlighting (adapted from Vue app)
function formatLogText(text: string): string {
  let formattedText = text;

  // Highlight coordinates
  const coordRegex = /(\[\d+,\s*\d+\])/g;
  formattedText = formattedText.replace(coordRegex, (match) => {
    return `<span class="coordinate">${match}</span>`;
  });

  // Highlight action sequences
  const actionSequenceRegex =
    /(Action:\s*)([ABUDLRS][\s;ABUDLRS]*?)(?=[^ABUDLRS\s;]|$)/g;
  formattedText = formattedText.replace(
    actionSequenceRegex,
    (_fullMatch, prefix, sequence) => {
      let cleanedSequence = sequence
        .replace(/;/g, "")
        .replace(/\s+/g, " ")
        .trim();
      let highlightedSequence = "";

      for (const actionChar of cleanedSequence) {
        if (actionChar === " ") {
          highlightedSequence += " ";
        } else if (
          ["A", "B", "START", "SELECT"].includes(actionChar.toUpperCase())
        ) {
          highlightedSequence += `<span class="action-type-button">${actionChar}</span>`;
        } else {
          highlightedSequence += `<span class="action-type-direction">${actionChar}</span>`;
        }
      }

      return prefix + highlightedSequence;
    },
  );

  return formattedText;
}
