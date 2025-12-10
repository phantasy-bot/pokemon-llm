import type { LogEntry } from "../../types/gameTypes";
import "./RecentActions.css";

interface RecentActionsProps {
  logs: LogEntry[];
  totalActions: number;
}

export function RecentActions({ logs, totalActions }: RecentActionsProps) {
  const actionEntries = logs.filter((log) => log.is_action).slice(0, 3);

  // We want the last 3 entries, but displayed chronological: oldest at left, newest at right
  const top3 = actionEntries.slice(0, 3);
  
  // Construct the display array of length 3, filling from the right
  const displayItems = new Array(3).fill(null);
  top3.forEach((action, i) => {
    const targetIndex = 2 - i; // 0->2, 1->1, 2->0
    if (targetIndex >= 0) {
      displayItems[targetIndex] = action;
    }
  });

  // Calculate action numbers based on totalActions
  const buttonCounts: number[] = [];
  for (let i = 0; i < displayItems.length; i++) {
    const action = displayItems[i];
    if (action) {
      const rawText = action.text || action.message || "";
      const cleanText = rawText.replace("Action:", "").trim();
      const buttons = cleanText.split(";").filter((k: string) => k.trim()).length;
      buttonCounts.push(buttons > 0 ? buttons : 1);
    } else {
      buttonCounts.push(0);
    }
  }
  
  // Calculate starting number - work backwards from totalActions
  const totalButtonsDisplayed = buttonCounts.reduce((a, b) => a + b, 0);
  let currentNum = totalActions - totalButtonsDisplayed + 1;
  
  const numberedItems: Array<{action: any, startNum: number, endNum: number} | null> = [];
  
  // Traverse in display order (left to right = oldest to newest)
  for (let i = 0; i < displayItems.length; i++) {
    const action = displayItems[i];
    if (action) {
      const buttonCount = buttonCounts[i];
      const startNum = currentNum;
      const endNum = currentNum + buttonCount - 1;
      currentNum = endNum + 1;
      numberedItems.push({ action, startNum, endNum });
    } else {
      numberedItems.push(null);
    }
  }

  return (
    <div className="recent-actions">
      <span className="recent-actions__label">RECENT ACTIONS</span>
      <span className="recent-actions__label-right">CURRENT</span>
      <div className="recent-actions__list">
        {numberedItems.map((item, i) => {
          if (item) {
            const { action, startNum, endNum } = item;
            
            // Format as range if multiple buttons, single number otherwise
            const numberLabel = (startNum !== endNum)
              ? `#${startNum}-${endNum}`
              : `#${startNum}`;
            
            const rawText = action.text || action.message || "";
            const cleanText = rawText.replace("Action:", "").trim();
            const keys = cleanText.split(";").map((k: string) => k.trim()).filter((k: string) => k).map((k: string) => {
              const upper = k.toUpperCase();
              if (upper === "START") return "S";
              if (upper === "SELECT") return "SEL";
              return upper;
            });
            if (keys.length === 0 && cleanText) keys.push(cleanText.charAt(0));


            // Check if this is the most recent action
            const isLatest = action.id === actionEntries[0]?.id;

            return (
              <div key={action.id} className="recent-actions__item">
                <span className="recent-actions__number">
                  {numberLabel}
                </span>
                <div className="recent-actions__group">
                  {keys.map((k: string, idx: number) => (
                    <div 
                      key={idx} 
                      className={`recent-actions__square ${isLatest ? 'flash' : ''}`}
                      style={isLatest ? { animationDelay: `${idx * 0.5}s` } : undefined}
                    >
                      {k}
                    </div>
                  ))}
                </div>
              </div>
            );
          } else {
            return (
              <div key={`empty-${i}`} className="recent-actions__item">
                <span className="recent-actions__number recent-actions__number--empty">
                  #--
                </span>
                <div className="recent-actions__group">
                  <div className="recent-actions__square recent-actions__square--empty" />
                </div>
              </div>
            );
          }
        })}
      </div>
    </div>
  );
}
