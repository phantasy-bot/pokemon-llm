import { useState, useEffect, useRef } from "react";
import type { LogEntry } from "../../types/gameTypes";
import "./RecentActions.css";

interface RecentActionsProps {
  logs: LogEntry[];
  totalActions: number;
  animateTrigger?: number; // Timestamp when to trigger button animations
  isWaitingForAction?: boolean; // When true, show "waiting for actions..." in current column
  isActive?: boolean; // When true, highlight the entire section with accent color
}

const MAX_VISIBLE_KEYS = 5;
const SCROLL_INTERVAL_MS = 500; // Match the flash animation delay

// Animated dots component for waiting state - resets after 3 dots
function AnimatedDots() {
  const [dots, setDots] = useState('');
  
  useEffect(() => {
    const interval = setInterval(() => {
      setDots(prev => prev === '...' ? '' : prev + '.');
    }, 400);
    return () => clearInterval(interval);
  }, []);
  
  return <span className="animated-dots">{dots}</span>;
}

export function RecentActions({ logs, totalActions, animateTrigger, isWaitingForAction = false, isActive = false }: RecentActionsProps) {
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
  
  const actionEntries = logs.filter((log) => log.is_action).slice(0, 2); // Only need 2 for 2-column layout

  // For 2-column layout: previous (index 0) and current (index 1)
  // Previous = second most recent action, Current = most recent action
  const previousAction = actionEntries.length > 1 ? actionEntries[1] : null;
  const currentAction = actionEntries.length > 0 ? actionEntries[0] : null;

  // Calculate button counts for action number labels
  const getButtonCount = (action: LogEntry | null) => {
    if (!action) return 0;
    const rawText = action.text || action.message || "";
    const cleanText = rawText.replace("Action:", "").trim();
    const buttons = cleanText.split(";").filter((k: string) => k.trim()).length;
    return buttons > 0 ? buttons : 1;
  };

  const prevButtonCount = getButtonCount(previousAction);
  const currButtonCount = getButtonCount(currentAction);
  
  // Calculate action numbers
  const totalButtonsDisplayed = prevButtonCount + currButtonCount;
  const startNum = totalActions - totalButtonsDisplayed + 1;
  
  const prevStartNum = startNum;
  const prevEndNum = startNum + prevButtonCount - 1;
  const currStartNum = prevEndNum + 1;
  const currEndNum = currStartNum + currButtonCount - 1;

  // Track scroll offset for current action overflow animation
  const [scrollOffset, setScrollOffset] = useState(0);
  const currentActionId = currentAction?.id;
  
  // Get keys for current action
  const getActionKeys = (action: LogEntry | null) => {
    if (!action) return [];
    const rawText = action.text || action.message || "";
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
  };

  const currentKeys = getActionKeys(currentAction);
  const hasOverflow = currentKeys.length > MAX_VISIBLE_KEYS;
  
  // Reset scroll offset when new action arrives
  useEffect(() => {
    setScrollOffset(0);
  }, [currentActionId]);
  
  // Auto-scroll through overflow keys
  useEffect(() => {
    if (!hasOverflow) return;
    
    const maxOffset = currentKeys.length - MAX_VISIBLE_KEYS;
    
    const timer = setInterval(() => {
      setScrollOffset(prev => {
        if (prev >= maxOffset) return prev;
        return prev + 1;
      });
    }, SCROLL_INTERVAL_MS);
    
    return () => clearInterval(timer);
  }, [hasOverflow, currentKeys.length, currentActionId]);

  // Render action column
  const renderActionColumn = (
    action: LogEntry | null, 
    startNum: number, 
    endNum: number, 
    isCurrentColumn: boolean
  ) => {
    if (!action) {
      // Empty column
      if (isCurrentColumn && isWaitingForAction) {
        // Show waiting message in current column
        return (
          <div className="recent-actions__item recent-actions__item--waiting">
            <span className="recent-actions__waiting-text">
              waiting for actions<AnimatedDots />
            </span>
          </div>
        );
      }
      return (
        <div className="recent-actions__item recent-actions__item--empty">
          <span className="recent-actions__number recent-actions__number--empty">#--</span>
          <div className="recent-actions__group">
            <div className="recent-actions__square recent-actions__square--empty" />
          </div>
        </div>
      );
    }

    const keys = getActionKeys(action);
    const numberLabel = startNum !== endNum ? `#${startNum}-${endNum}` : `#${startNum}`;
    
    // Apply visibility window for overflow
    let visibleKeys = keys;
    let showOverflowIndicator = false;
    
    if (keys.length > MAX_VISIBLE_KEYS) {
      if (isCurrentColumn) {
        visibleKeys = keys.slice(scrollOffset, scrollOffset + MAX_VISIBLE_KEYS);
        showOverflowIndicator = scrollOffset + MAX_VISIBLE_KEYS < keys.length;
      } else {
        visibleKeys = keys.slice(0, MAX_VISIBLE_KEYS);
        showOverflowIndicator = true;
      }
    }

    return (
      <div className={`recent-actions__item ${isCurrentColumn ? 'recent-actions__item--current' : 'recent-actions__item--previous'}`}>
        <span className="recent-actions__number">{numberLabel}</span>
        <div className="recent-actions__group">
          {visibleKeys.map((k: string, idx: number) => (
            <div 
              key={`${scrollOffset}-${idx}`} 
              className={`recent-actions__square ${shouldAnimate && isCurrentColumn ? 'flash' : ''}`}
              style={shouldAnimate && isCurrentColumn ? { animationDelay: `${idx * 0.5}s` } : undefined}
            >
              {k}
            </div>
          ))}
          {showOverflowIndicator && (
            <div className="recent-actions__square recent-actions__square--overflow">⋯</div>
          )}
        </div>
      </div>
    );
  };

  return (
    <div className={`recent-actions ${isActive ? 'recent-actions--active' : ''}`}>
      <span className="recent-actions__label">PREVIOUS ACTION</span>
      <span className="recent-actions__label-right">CURRENT ACTION</span>
      <div className="recent-actions__list">
        {renderActionColumn(previousAction, prevStartNum, prevEndNum, false)}
        {renderActionColumn(currentAction, currStartNum, currEndNum, true)}
      </div>
    </div>
  );
}
