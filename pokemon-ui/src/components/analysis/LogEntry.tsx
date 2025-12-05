import type { LogEntry } from "../../types/gameTypes";
import ReactMarkdown from "react-markdown";
import rehypeRaw from "rehype-raw";
import { VisionScreenshot } from "../vision/VisionScreenshot";
import "./LogEntry.css";

interface LogEntryProps {
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
      return ""; // Remove eye icon for cleaner display
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
      return "LLM Analysis";
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

export function LogEntryCard({
  entry,
  isNew,
  compact = false,
}: LogEntryProps) {
  const logType = extractLogType(entry);
  const icon = getLogTypeIcon(logType);
  const label = getLogTypeLabel(logType);
  const text = entry.text || entry.message || "";

  // For compact mode, show minimal info BUT still render markdown for vision
  if (compact) {
    // For vision entries, render with markdown formatting
    if (logType === "vision") {
      return (
        <div className="log-entry log-entry--compact log-entry--vision log-entry--vision-full">
      <div className="log-entry__compact-vision" dangerouslySetInnerHTML={{ __html: formatLogText(text) }} />
        </div>
      );
    }
    
    // For other types, use simple truncation
    const charLimit = 100;
    return (
      <div className={`log-entry log-entry--compact log-entry--${logType}`}>
        <span className="log-entry__compact-icon">{icon}</span>
        <span className="log-entry__compact-text">
          {truncateText(text, charLimit)}
        </span>
      </div>
    );
  }

  return (
    <div
      className={`log-entry${isNew ? " log-entry--new" : ""} log-entry--${logType}`}
    >
      {/* Header - Only show for Action and General types, hide for Vision/Response to reduce noise */}
      {logType !== "vision" && logType !== "response" && (
        <div className="log-entry__header">
          <div className="log-entry__type-info">
            <span className="log-entry__type-icon">{icon}</span>
            <span className="log-entry__type-label">{label}</span>
          </div>
          {entry.timestamp && (
            <span className="log-entry__timestamp">
              {new Date(entry.timestamp).toLocaleTimeString()}
            </span>
          )}
        </div>
      )}

      <div className="log-entry__content">
        {logType === "vision" ? (
          <div className="log-entry__vision-container">
            {/* Screenshot on the left */}
            <div className="log-entry__vision-screenshot">
              <VisionScreenshot
                timestamp={entry.timestamp || Date.now().toString()}
                compact={compact}
              />
            </div>

            {/* Vision analysis text and details on the right */}
            <div className="log-entry__vision-content">
              {/* Format log text with coordinate and action highlighting */}
              <div className="log-entry__text">
                <ReactMarkdown rehypePlugins={[rehypeRaw]}>
                  {formatLogText(text)}
                </ReactMarkdown>
              </div>

              {/* Special sections for vision analysis */}
              <div className="log-entry__vision-details">
                {text.includes("Pokemon") && (
                  <div className="log-entry__pokemon-indicator">
                    <span className="log-entry__pokemon-icon">⚡</span>
                    <span className="log-entry__pokemon-text">
                      Pokemon detected
                    </span>
                  </div>
                )}
                {text.includes("[") && text.includes("]") && (
                  <div className="log-entry__coordinate-indicator">
                    <span className="log-entry__coordinate-icon">📍</span>
                    <span className="log-entry__coordinate-text">
                      Location data
                    </span>
                  </div>
                )}
              </div>
            </div>
          </div>
        ) : (
          /* For non-vision entries, show text only */
          <>
            <div className="log-entry__text">
              <ReactMarkdown rehypePlugins={[rehypeRaw]}>
                {formatLogText(text)}
              </ReactMarkdown>
            </div>

            {/* Special sections for response analysis */}
            {logType === "response" && (
              <div className="log-entry__response-details">
                {text.toLowerCase().includes("battle") && (
                  <div className="log-entry__battle-indicator">
                    <span className="log-entry__battle-icon">⚔️</span>
                    <span className="log-entry__battle-text">
                      Battle strategy
                    </span>
                  </div>
                )}
                {text.toLowerCase().includes("item") && (
                  <div className="log-entry__item-indicator">
                    <span className="log-entry__item-icon">🎒</span>
                    <span className="log-entry__item-text">
                      Item management
                    </span>
                  </div>
                )}
              </div>
            )}

            {/* Special sections for action entries */}
            {logType === "action" && (
              <div className="log-entry__actions">
                {extractActions(text).map((action, index) => {
                  const actionType = /[AB]/.test(action)
                    ? "button"
                    : "direction";
                  return (
                    <span
                      key={index}
                      className={`log-entry__action log-entry__action--${actionType}`}
                    >
                      {action}
                    </span>
                  );
                })}
              </div>
            )}
          </>
        )}
      </div>
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



// Format log text with highlighting and proper markdown parsing
function formatLogText(text: string): string {
  let formattedText = text;

  // Filter out box tokens before other processing
  formattedText = formattedText.replace(/&#259;|&#258;/g, "");
  // Remove actual begin_of_box and end_of_box tags
  formattedText = formattedText.replace(/<\s*\|\s*begin_of_box\s*\|\s*>/g, "");
  formattedText = formattedText.replace(/<\s*\|\s*end_of_box\s*\|\s*>/g, "");

  // Check if this is a vision analysis that should be formatted as a list
  if (
    text.includes("Readable Text:") ||
    text.includes("Character Position:") ||
    text.includes("Visible NPCs:") ||
    // Check for JSON format keys
    (text.includes("screen_type") && text.includes("player_position"))
  ) {
    return formatVisionAnalysisAsList(formattedText);
  }

  // Convert markdown headers (###, ##, #) to styled HTML
  formattedText = formattedText.replace(/^### (.+)$/gm, '<h4 class="log-section-header">$1</h4>');
  formattedText = formattedText.replace(/^## (.+)$/gm, '<h3 class="log-section-header log-section-header--major">$1</h3>');
  formattedText = formattedText.replace(/^# (.+)$/gm, '<h2 class="log-section-header log-section-header--main">$1</h2>');
  
  // Convert bold text (**text**)
  formattedText = formattedText.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  
  // Convert bullet points at start of line
  formattedText = formattedText.replace(/^- (.+)$/gm, '<div class="log-bullet">• $1</div>');
  
  // Add section dividers for numbered sections (1. CURRENT STATE, etc.)
  formattedText = formattedText.replace(
    /^(\d+)\.\s*([A-Z][A-Z\s&]+)$/gm, 
    '<div class="log-numbered-section"><span class="log-section-number">$1.</span> <span class="log-section-title">$2</span></div>'
  );
  
  // Highlight game_analysis tags as section separators (but don't remove them)
  formattedText = formattedText.replace(
    /<game_analysis>/gi,
    '<div class="game-analysis-start">📊 Analysis</div>'
  );
  formattedText = formattedText.replace(
    /<\/game_analysis>/gi,
    '<div class="game-analysis-end"></div>'
  );

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
  
  // Convert newlines to proper breaks for better formatting
  formattedText = formattedText.replace(/\n\n/g, '</p><p>');
  formattedText = formattedText.replace(/\n/g, '<br/>');

  return `<div class="formatted-log-content">${formattedText}</div>`;
}

// Format vision analysis as a structured list
function formatVisionAnalysisAsList(text: string): string {
  // 1. Try to parse as JSON first (new format)
  try {
    // Extract JSON substring if wrapped in extra text
    const jsonMatch = text.match(/\{[\s\S]*\}/);
    if (jsonMatch) {
      const jsonText = jsonMatch[0];
      const data = JSON.parse(jsonText);
      let htmlItems: string[] = [];
      
      // Helper to split semicolon lists and join with commas
      const formatList = (str: string) => {
        if (!str || str === "unreadable") return "";
        return str.split(';').map(s => s.trim()).filter(Boolean).join(', ');
      };

      // Helper to add item
      const addItem = (label: string, value: string) => {
        if (!value || value === "unreadable" || value === "none") return;
        htmlItems.push(`<div class="vision-item">
          <span class="vision-category">${label}</span>
          <span class="vision-content">${value}</span>
        </div>`);
      };

      // Map fields to UI
      if (data.screen_type) addItem("SCREEN", data.screen_type.toUpperCase());
      if (data.readable_text) addItem("TEXT", formatList(data.readable_text));
      if (data.player_position) addItem("POSITION", data.player_position);
      if (data.nearby_objects) addItem("NEARBY", formatList(data.nearby_objects));
      if (data.npcs) addItem("NPCs", formatList(data.npcs));
      if (data.obstacles) addItem("OBSTACLES", formatList(data.obstacles));
      if (data.ui_elements) addItem("UI", formatList(data.ui_elements));
      if (data.battle_info) addItem("BATTLE", formatList(data.battle_info));
      if (data.menu_cursor) addItem("CURSOR", data.menu_cursor);
      if (data.navigation_notes) addItem("NAV", formatList(data.navigation_notes));

      if (htmlItems.length > 0) {
        return htmlItems.join("");
      }
    }
  } catch (e) {
    // Not valid JSON, fall back to string parsing
  }

  // 2. Fallback to old string parsing if not JSON
  // Split by double newlines or by category headers
  const sections = text
    .split(/\n\s*(?=[A-Z][a-zA-Z\s]*:)/)
    .filter((section) => section.trim());

  if (sections.length === 0) return text;

  let htmlItems: string[] = [];

  sections.forEach((section) => {
    const trimmedSection = section.trim();
    if (!trimmedSection) return;

    // Find the category header (text before the first colon)
    const colonIndex = trimmedSection.indexOf(":");
    if (colonIndex === -1) return;

    const category = trimmedSection.substring(0, colonIndex).trim();
    const content = trimmedSection.substring(colonIndex + 1).trim();

    if (!content) return;

    // Map old categories to new simple labels without emojis
    let simpleLabel = category.toUpperCase();
    if (simpleLabel === "READABLE TEXT") simpleLabel = "TEXT";
    if (simpleLabel === "CHARACTER POSITION") simpleLabel = "POSITION";
    if (simpleLabel === "VISIBLE NPCS") simpleLabel = "NPCs";
    if (simpleLabel === "UI ELEMENTS") simpleLabel = "UI";
    
    htmlItems.push(`<div class="vision-item">
      <span class="vision-category">${simpleLabel}</span>
      <span class="vision-content">${content.replace(/•/g, '').replace(/;\s*/g, ', ')}</span>
    </div>`);
  });

  return htmlItems.join("");
}
