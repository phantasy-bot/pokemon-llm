import { useState, useEffect, useRef } from "react";
import type { LogEntry } from "../../types/gameTypes";
import "./RecentActions.css";

interface RecentActionsProps {
  logs: LogEntry[];
  totalActions: number;
  animateTrigger?: number; // Timestamp when to trigger button animations
}

const MAX_VISIBLE_KEYS = 5;
const SCROLL_INTERVAL_MS = 500; // Match the flash animation delay

export function RecentActions({ logs, totalActions, animateTrigger }: RecentActionsProps) {
  // Track when to animate - only animate when animateTrigger changes
  const [shouldAnimate, setShouldAnimate] = useState(false);
  const lastTriggerRef = useRef<number | undefined>(undefined);
  
  // Only trigger animation when animateTrigger changes (not on data arrival)
  useEffect(() => {
    if (animateTrigger && animateTrigger !== lastTriggerRef.current) {
      lastTriggerRef.current = animateTrigger;
      setShouldAnimate(true);
      
      // Reset animation flag after animation completes (about 3s for all buttons)
      const timer = setTimeout(() => setShouldAnimate(false), 3000);
      return () => clearTimeout(timer);
    }
  }, [animateTrigger]);
  
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

  // Track scroll offset for latest action overflow animation
  const [scrollOffset, setScrollOffset] = useState(0);
  const latestActionId = actionEntries[0]?.id;
  
  // Get keys for latest action to check if we need scrolling
  const latestItem = numberedItems[2]; // Latest is always at index 2
  const latestKeys = latestItem ? (() => {
    const rawText = latestItem.action.text || latestItem.action.message || "";
    const cleanText = rawText.replace("Action:", "").trim();
    return cleanText.split(";").map((k: string) => k.trim()).filter((k: string) => k).map((k: string) => {
      const upper = k.toUpperCase();
      if (upper === "U") return "↑";
      if (upper === "D") return "↓";
      if (upper === "L") return "←";
      if (upper === "R") return "→";
      if (upper === "START") return "S";
      if (upper === "SELECT") return "SEL";
      return upper;
    });
  })() : [];
  
  const hasOverflow = latestKeys.length > MAX_VISIBLE_KEYS;
  
  // Reset scroll offset when new action arrives
  useEffect(() => {
    setScrollOffset(0);
  }, [latestActionId]);
  
  // Auto-scroll through overflow keys on the latest action
  useEffect(() => {
    if (!hasOverflow) return;
    
    const maxOffset = latestKeys.length - MAX_VISIBLE_KEYS;
    
    const timer = setInterval(() => {
      setScrollOffset(prev => {
        if (prev >= maxOffset) return prev; // Stop at end
        return prev + 1;
      });
    }, SCROLL_INTERVAL_MS);
    
    return () => clearInterval(timer);
  }, [hasOverflow, latestKeys.length, latestActionId]);

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
            const allKeys = cleanText.split(";").map((k: string) => k.trim()).filter((k: string) => k).map((k: string) => {
              const upper = k.toUpperCase();
              // Convert movement keys to arrow icons
              if (upper === "U") return "↑";
              if (upper === "D") return "↓";
              if (upper === "L") return "←";
              if (upper === "R") return "→";
              if (upper === "START") return "S";
              if (upper === "SELECT") return "SEL";
              return upper;
            });
            if (allKeys.length === 0 && cleanText) allKeys.push(cleanText.charAt(0));

            // Check if this is the most recent action
            const isLatest = action.id === actionEntries[0]?.id;
            
            // Apply visibility window for overflow
            let visibleKeys = allKeys;
            let showOverflowIndicator = false;
            
            if (allKeys.length > MAX_VISIBLE_KEYS) {
              if (isLatest) {
                // For latest action, use scroll offset
                visibleKeys = allKeys.slice(scrollOffset, scrollOffset + MAX_VISIBLE_KEYS);
                showOverflowIndicator = scrollOffset + MAX_VISIBLE_KEYS < allKeys.length;
              } else {
                // For older actions, just show first 5 with indicator
                visibleKeys = allKeys.slice(0, MAX_VISIBLE_KEYS);
                showOverflowIndicator = true;
              }
            }

            return (
              <div key={action.id} className="recent-actions__item">
                <span className="recent-actions__number">
                  {numberLabel}
                </span>
                <div className="recent-actions__group">
                  {visibleKeys.map((k: string, idx: number) => (
                    <div 
                      key={`${scrollOffset}-${idx}`} 
                      className={`recent-actions__square ${shouldAnimate && isLatest ? 'flash' : ''}`}
                      style={shouldAnimate && isLatest ? { animationDelay: `${idx * 0.5}s` } : undefined}
                    >
                      {k}
                    </div>
                  ))}
                  {showOverflowIndicator && (
                    <div className="recent-actions__square recent-actions__square--overflow">
                      ⋯
                    </div>
                  )}
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
