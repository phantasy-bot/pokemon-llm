/**
 * JustChattingOverlay - OBS overlay for "Just Chatting" streams
 *
 * Features:
 * - Holographic entrance animation with frame progression
 * - Page shake effect when character lands (affects entire page)
 * - Pokemon-Red style chatbox for intro TTS with typewriter effect
 */
import { useState, useEffect } from "react";
import "./JustChattingOverlay.css";

// Character frames
const FRAME_0 = "/lass/lass-0.png";
const FRAME_1 = "/lass/lass-1.png";
const FRAME_2 = "/lass/lass-2.png";

// Intro messages (fallbacks if backend doesn't send dynamic text)
const INTRO_MESSAGES = {
  new: "Hey chat! It's Lass! Welcome to my Pokemon Red stream! Let's catch some Pokemon and become the very best!",
  continue:
    "Hey everyone! Lass is back! Had some connection issues but I'm ready to continue my Pokemon adventure!",
};

// Typewriter text component for chatbox
function TypewriterText({
  text,
  speed = 40,
  startDelay = 0,
}: {
  text: string;
  speed?: number;
  startDelay?: number;
}) {
  const [displayedText, setDisplayedText] = useState("");
  const [started, setStarted] = useState(false);

  useEffect(() => {
    const startTimer = setTimeout(() => setStarted(true), startDelay);
    return () => clearTimeout(startTimer);
  }, [startDelay]);

  useEffect(() => {
    if (!started) return;

    let index = 0;
    const interval = setInterval(() => {
      if (index < text.length) {
        setDisplayedText(text.slice(0, index + 1));
        index++;
      } else {
        clearInterval(interval);
      }
    }, speed);

    return () => clearInterval(interval);
  }, [text, speed, started]);

  return (
    <span className="typewriter-text">
      {displayedText}
      {started && displayedText.length < text.length && (
        <span className="typewriter-cursor">▼</span>
      )}
    </span>
  );
}

// Pokemon-Red style chatbox - now accepts dynamic text
function IntroChatbox({ introText }: { introText: string }) {
  // Use dynamic text or fallback to default
  const displayText = introText || INTRO_MESSAGES.new;
  
  return (
    <div className="intro-chatbox">
      <div className="chatbox-inner">
        <TypewriterText
          text={displayText}
          speed={35}
          startDelay={5000} // Start after character lands
        />
      </div>
    </div>
  );
}

// Holographic character component
function HolographicCharacter() {
  return (
    <div className="holographic-afterimage">
      {/* Trail ghosts - Trails 1-3 use FRAME 0 */}
      <img
        src={FRAME_0}
        alt=""
        className="trail-ghost trail-1"
        aria-hidden="true"
      />
      <img
        src={FRAME_0}
        alt=""
        className="trail-ghost trail-2"
        aria-hidden="true"
      />
      <img
        src={FRAME_0}
        alt=""
        className="trail-ghost trail-3"
        aria-hidden="true"
      />

      {/* Trails 4-5 use FRAME 1 */}
      <img
        src={FRAME_1}
        alt=""
        className="trail-ghost trail-4"
        aria-hidden="true"
      />
      <img
        src={FRAME_1}
        alt=""
        className="trail-ghost trail-5"
        aria-hidden="true"
      />

      {/* Trails 6-8 use FRAME 2 */}
      <img
        src={FRAME_2}
        alt=""
        className="trail-ghost trail-6"
        aria-hidden="true"
      />
      <img
        src={FRAME_2}
        alt=""
        className="trail-ghost trail-7"
        aria-hidden="true"
      />
      <img
        src={FRAME_2}
        alt=""
        className="trail-ghost trail-8"
        aria-hidden="true"
      />

      {/* Stationary ghosts */}
      <img
        src={FRAME_2}
        alt=""
        className="ghost-layer ghost-1"
        aria-hidden="true"
      />
      <img
        src={FRAME_2}
        alt=""
        className="ghost-layer ghost-2"
        aria-hidden="true"
      />
      <img
        src={FRAME_2}
        alt=""
        className="ghost-layer ghost-3"
        aria-hidden="true"
      />

      {/* Main character - slides in (invisible) then reveals at end */}
      <img src={FRAME_2} alt="Lass" className="main-character" />
    </div>
  );
}

// Flower background
function FlowerBackground() {
  const rows = [];
  const rowCount = 14;
  const flowersPerRow = 40;

  for (let row = 0; row < rowCount; row++) {
    const flowers = [];
    for (let i = 0; i < flowersPerRow; i++) {
      flowers.push(
        <span key={i} className="flower-icon flower-spin-cw">
          ✿
        </span>
      );
    }

    rows.push(
      <div
        key={row}
        className="flower-row"
        style={{ animationDelay: `${row * -1.5}s` }}
      >
        {flowers}
        {flowers}
        {flowers}
      </div>
    );
  }

  return <div className="flower-background">{rows}</div>;
}

function StreamInfo() {
  return (
    <div className="stream-info">
      <div className="stream-title">
        <span className="title-text">JUST CHATTING</span>
      </div>
      <div className="stream-subtitle">with Lass</div>
    </div>
  );
}

function BrandingSection() {
  return (
    <div className="branding-section">
      <div className="branding-item">
        <img
          src="/sponsors/mystery-gift.png"
          alt="Mystery Gift"
          className="brand-icon"
        />
        <span className="brand-text">mysterygift.fun</span>
      </div>
      <div className="branding-divider">✿</div>
      <div className="branding-item">
        <img
          src="/sponsors/phantasy.png"
          alt="Phantasy"
          className="brand-icon"
        />
        <span className="brand-text">phantasy.bot</span>
      </div>
    </div>
  );
}

interface JustChattingOverlayProps {
  introText?: string;
}

export function JustChattingOverlay({ introText = '' }: JustChattingOverlayProps) {
  return (
    <div className="just-chatting-overlay">
      {/* Background layer - not affected by page shake */}
      <div className="background-layer">
        <FlowerBackground />
      </div>

      {/* Page shake wrapper - contains ALL content that should shake */}
      <div className="page-shake-container">
        {/* Content layer */}
        <div className="content-layer">
          <StreamInfo />
          <BrandingSection />
        </div>

        {/* Character container */}
        <div className="character-container">
          <HolographicCharacter />
        </div>

        {/* Pokemon-Red style chatbox - uses dynamic intro text */}
        <IntroChatbox introText={introText} />
      </div>
    </div>
  );
}
