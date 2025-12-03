/**
 * Data transformation functions.
 * Convert raw WebSocket data to display-ready formats.
 */

import type { ThoughtEntry, HPStatus } from "../types/display";

export function getHPStatus(hp: number, maxHp: number): HPStatus {
  const percent = (hp / maxHp) * 100;
  if (percent <= 25) return "critical";
  if (percent <= 50) return "wounded";
  return "healthy";
}

export function extractButtons(text: string): string[] {
  const pattern = /\b(UP|DOWN|LEFT|RIGHT|A|B|START|SELECT|L|R)\b/gi;
  const matches = text.match(pattern);
  return matches ? [...new Set(matches.map((a) => a.toUpperCase()))] : [];
}

export function extractTools(text: string): string[] {
  const toolKeywords = [
    "move",
    "attack",
    "wait",
    "item",
    "heal",
    "rescue",
    "trade",
    "visit",
    "seize",
    "talk",
  ];
  const lower = text.toLowerCase();
  return toolKeywords.filter((tool) => lower.includes(tool));
}

interface ParsedSections {
  observation?: string;
  reasoning?: string;
  action?: string;
}

export function parseSections(text: string): ParsedSections {
  const sections: ParsedSections = {};

  // Match ## Observation, ## Reasoning, ## ACTION sections
  const observationMatch = text.match(/##\s*Observation\s*([\s\S]*?)(?=##|$)/i);
  const reasoningMatch = text.match(/##\s*Reasoning\s*([\s\S]*?)(?=##|$)/i);
  // Handle both "## ACTION:" and "ACTION:" formats
  const actionMatch = text.match(/(?:##\s*)?ACTION:\s*([A-Za-z;]+)/i);

  if (observationMatch) sections.observation = observationMatch[1].trim();
  if (reasoningMatch) sections.reasoning = reasoningMatch[1].trim();
  if (actionMatch) sections.action = actionMatch[1].trim();

  return sections;
}

export function parseActionButtons(actionStr: string): string[] {
  // Parse "A;A;A;" into ["A", "A", "A"]
  return actionStr
    .split(";")
    .map((b) => b.trim().toUpperCase())
    .filter((b) => b.length > 0);
}

export function transformThought(
  rawThought: string,
  screenshot?: string,
): ThoughtEntry {
  const cleanedText = rawThought.replace(/^\[.*?\]\s*/, "");
  const sections = parseSections(cleanedText);

  // Extract action buttons from the ACTION section if present
  const actionButtons = sections.action
    ? parseActionButtons(sections.action)
    : [];

  return {
    id: crypto.randomUUID(),
    timestamp: new Date(),
    text: cleanedText,
    buttons: extractButtons(rawThought),
    tools: extractTools(rawThought),
    screenshot,
    sections: {
      observation: sections.observation,
      reasoning: sections.reasoning,
      action: sections.action,
    },
    actionButtons,
  };
}

export function formatElapsedTime(gameStatus?: string): string {
  if (!gameStatus) return "0:00:00";
  return gameStatus;
}

export function formatTimestamp(date: Date): string {
  return date.toLocaleTimeString("en-US", {
    hour12: false,
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}
