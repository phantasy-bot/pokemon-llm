import { useState, useEffect, useRef, useCallback } from 'react';
import './TypewriterText.css';

interface TypewriterTextProps {
  text: string;
  speed?: number; // ms per character
  className?: string;
  onComplete?: () => void;
}

/**
 * Typewriter effect component that animates text character by character.
 * For plain text only - renders characters one at a time.
 */
export function TypewriterText({
  text,
  speed = 15, // Default 15ms per character for fast readable typing
  className = '',
  onComplete,
}: TypewriterTextProps) {
  const [displayedLength, setDisplayedLength] = useState(0);
  const textRef = useRef(text);
  const onCompleteRef = useRef(onComplete);
  
  // Keep ref in sync
  useEffect(() => {
    onCompleteRef.current = onComplete;
  }, [onComplete]);
  
  // Reset when text changes
  useEffect(() => {
    if (textRef.current !== text) {
      textRef.current = text;
      setDisplayedLength(0);
    }
  }, [text]);
  
  // Animate the text - one character at a time
  useEffect(() => {
    if (displayedLength >= text.length) {
      onCompleteRef.current?.();
      return;
    }
    
    const timer = setTimeout(() => {
      setDisplayedLength(prev => prev + 1);
    }, speed);
    
    return () => clearTimeout(timer);
  }, [displayedLength, text.length, speed]);
  
  // Return the visible portion of text
  const visibleText = text.slice(0, displayedLength);
  const isComplete = displayedLength >= text.length;
  
  return (
    <span className={className}>
      {visibleText}
      {!isComplete && <span className="typewriter-cursor">▋</span>}
    </span>
  );
}

/**
 * Hook for typewriter effect on any text content.
 * Returns the portion of text to display.
 */
export function useTypewriter(text: string, speed = 15): { displayedText: string; isComplete: boolean } {
  const [displayedLength, setDisplayedLength] = useState(0);
  const textRef = useRef(text);
  
  useEffect(() => {
    if (textRef.current !== text) {
      textRef.current = text;
      setDisplayedLength(0);
    }
  }, [text]);
  
  useEffect(() => {
    if (displayedLength >= text.length) {
      return;
    }
    
    const timer = setTimeout(() => {
      setDisplayedLength(prev => prev + 1);
    }, speed);
    
    return () => clearTimeout(timer);
  }, [displayedLength, text.length, speed]);
  
  return {
    displayedText: text.slice(0, displayedLength),
    isComplete: displayedLength >= text.length
  };
}

interface TypewriterHTMLProps {
  html: string;
  speed?: number; // ms per character (of plain text, not HTML tags)
  className?: string;
  onComplete?: () => void;
}

/**
 * Typewriter for HTML content that preserves styling.
 * Extracts plain text from HTML, animates character count,
 * then re-renders with visibility applied to text nodes.
 */
export function TypewriterHTML({
  html,
  speed = 20,
  className = '',
  onComplete,
}: TypewriterHTMLProps) {
  const [revealedChars, setRevealedChars] = useState(0);
  const htmlRef = useRef(html);
  const onCompleteRef = useRef(onComplete);
  
  // Get plain text length from HTML
  const getTextContent = useCallback((htmlString: string): string => {
    const temp = document.createElement('div');
    temp.innerHTML = htmlString;
    return temp.textContent || temp.innerText || '';
  }, []);
  
  const plainText = getTextContent(html);
  const totalChars = plainText.length;
  const isComplete = revealedChars >= totalChars;
  
  // Keep refs in sync
  useEffect(() => {
    onCompleteRef.current = onComplete;
  }, [onComplete]);
  
  // Reset when HTML changes
  useEffect(() => {
    if (htmlRef.current !== html) {
      htmlRef.current = html;
      setRevealedChars(0);
    }
  }, [html]);
  
  // Animate character reveal - one at a time
  useEffect(() => {
    if (isComplete) {
      onCompleteRef.current?.();
      return;
    }
    
    const timer = setTimeout(() => {
      setRevealedChars(prev => prev + 1);
    }, speed);
    
    return () => clearTimeout(timer);
  }, [revealedChars, isComplete, speed]);
  
  // Process HTML to hide characters beyond revealedChars and insert cursor
  const processedHtml = useCallback(() => {
    const temp = document.createElement('div');
    temp.innerHTML = html;
    
    // Create cursor element
    const cursorSpan = document.createElement('span');
    cursorSpan.className = "typewriter-cursor";
    cursorSpan.textContent = "▋";
    
    if (isComplete) {
      // If complete, insert cursor at the end of the last actual content
      let target: Node = temp;
      while (target.lastChild) {
        if (target.lastChild.nodeType === Node.TEXT_NODE) {
          target.appendChild(cursorSpan);
          return temp.innerHTML;
        }
        target = target.lastChild;
      }
      target.appendChild(cursorSpan);
      return temp.innerHTML;
    }
    
    let charCount = 0;
    let cursorInserted = false;
    
    const walker = document.createTreeWalker(temp, NodeFilter.SHOW_TEXT, null);
    const textNodes: Text[] = [];
    let node: Text | null;
    while ((node = walker.nextNode() as Text | null)) {
      textNodes.push(node);
    }
    
    textNodes.forEach(textNode => {
      const text = textNode.textContent || '';
      const startIndex = charCount;
      const endIndex = charCount + text.length;
      charCount = endIndex;
      
      if (cursorInserted) {
         textNode.textContent = '';
         return;
      }

      if (revealedChars <= startIndex) {
        if (!cursorInserted) {
            textNode.parentNode?.insertBefore(cursorSpan, textNode);
            cursorInserted = true;
        }
        textNode.textContent = '';
      } else if (revealedChars < endIndex) {
        const visibleCount = revealedChars - startIndex;
        textNode.textContent = text.slice(0, visibleCount);
        if (textNode.nextSibling) {
            textNode.parentNode?.insertBefore(cursorSpan, textNode.nextSibling);
        } else {
            textNode.parentNode?.appendChild(cursorSpan);
        }
        cursorInserted = true;
      }
    });
    
    if (!cursorInserted) {
       let target: Node = temp;
        // Drill down to last text node or just append to end
        while (target.lastChild && target.lastChild.nodeType !== Node.TEXT_NODE) {
            target = target.lastChild;
        }
        target.appendChild(cursorSpan);
    }
    
    return temp.innerHTML;
  }, [html, revealedChars, isComplete]);
  
  return (
    <div className={`typewriter-html ${className}`}>
      <span dangerouslySetInnerHTML={{ __html: processedHtml() }} />
    </div>
  );
}

// Export TypewriterReveal as alias to TypewriterHTML for backward compatibility
export const TypewriterReveal = TypewriterHTML;
