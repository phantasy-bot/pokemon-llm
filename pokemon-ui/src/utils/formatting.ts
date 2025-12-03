// Text formatting utilities for Pokemon battle logs (adapted from Vue app)

export function formatLogText(text: string): string {
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
    (fullMatch, prefix, sequence) => {
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

export function extractActions(text: string): string[] {
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

export function getActionType(action: string): "button" | "direction" {
  return ["A", "B", "START", "SELECT"].includes(action.toUpperCase())
    ? "button"
    : "direction";
}
