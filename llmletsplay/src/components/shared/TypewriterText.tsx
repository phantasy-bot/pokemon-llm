import { useState, useEffect, useRef } from 'react'

interface TypewriterTextProps {
  text: string
  speed?: number
  startDelay?: number
  onComplete?: () => void
  className?: string
  style?: React.CSSProperties
}

export function TypewriterText({ 
  text, 
  speed = 30, 
  startDelay = 0,
  onComplete,
  className,
  style
}: TypewriterTextProps) {
  const [displayedText, setDisplayedText] = useState('')
  const indexRef = useRef(0)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    // Reset state when text input changes
    setDisplayedText('')
    indexRef.current = 0
    if (timerRef.current) clearTimeout(timerRef.current)

    const startTimeout = setTimeout(() => {
      timerRef.current = setInterval(() => {
        if (indexRef.current < text.length) {
          setDisplayedText(text.slice(0, indexRef.current + 1))
          indexRef.current++
        } else {
          if (timerRef.current) clearInterval(timerRef.current)
          onComplete?.()
        }
      }, speed)
    }, startDelay)

    return () => {
      clearTimeout(startTimeout)
      if (timerRef.current) clearInterval(timerRef.current)
    }
  }, [text, speed, startDelay])

  return (
    <div className={className} style={{ position: 'relative', ...style }}>
      {/* Invisible text to maintain layout size */}
      <div style={{ opacity: 0, visibility: 'hidden' }} aria-hidden="true">
        {text}
      </div>
      
      {/* Absolute overlay with typed text - uses opacity to keep alignment stable */}
      <div style={{ 
        position: 'absolute', 
        top: 0, 
        left: 0, 
        width: '100%', 
        height: '100%' 
      }}>
        <span>{text.slice(0, displayedText.length)}</span>
        <span style={{ opacity: 0 }}>{text.slice(displayedText.length)}</span>
      </div>
    </div>
  )
}
