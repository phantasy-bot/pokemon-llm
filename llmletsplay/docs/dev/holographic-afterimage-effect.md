# Holographic Afterimage Effect

A CSS-based effect that creates a rainbow ghost trail behind character images, giving the impression of motion or holographic projection.

## Overview

The effect uses **multiple translucent image copies** (ghost layers) positioned behind the main image, each with:

- Horizontal offset (creating the "trail" direction)
- `hue-rotate` CSS filter animation (cycling through rainbow colors)
- Varying opacity (furthest ghosts are most transparent)
- Staggered animation delays (creating color shimmer variation)

## Quick Start

### 1. Add the CSS

Add the holographic styles to your CSS file (already in `index.css`):

```css
/* Keyframe for rainbow color cycling */
@keyframes holographic-shift {
  0% {
    filter: hue-rotate(0deg) saturate(1.8) brightness(1.1);
  }
  16% {
    filter: hue-rotate(60deg) saturate(2) brightness(1.2);
  }
  33% {
    filter: hue-rotate(120deg) saturate(1.8) brightness(1.1);
  }
  50% {
    filter: hue-rotate(180deg) saturate(2) brightness(1.15);
  }
  66% {
    filter: hue-rotate(240deg) saturate(1.8) brightness(1.2);
  }
  83% {
    filter: hue-rotate(300deg) saturate(2) brightness(1.1);
  }
  100% {
    filter: hue-rotate(360deg) saturate(1.8) brightness(1.1);
  }
}

/* Subtle shimmer/pulse */
@keyframes ghost-shimmer {
  0%,
  100% {
    opacity: 0.35;
  }
  50% {
    opacity: 0.5;
  }
}

/* Container */
.holographic-afterimage {
  position: relative;
  display: inline-block;
  height: 100%;
  width: auto;
}

/* Shared ghost layer styles */
.holographic-afterimage .ghost-layer {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  image-rendering: pixelated;
  object-fit: contain;
}

/* Ghost 1 - Furthest back */
.holographic-afterimage .ghost-1 {
  transform: translateX(-12px);
  opacity: 0.25;
  animation: holographic-shift 3s ease-in-out infinite, ghost-shimmer 2s
      ease-in-out infinite;
  animation-delay: 0s, 0.3s;
  z-index: 1;
}

/* Ghost 2 - Middle */
.holographic-afterimage .ghost-2 {
  transform: translateX(-8px);
  opacity: 0.35;
  animation: holographic-shift 3s ease-in-out infinite, ghost-shimmer 2s
      ease-in-out infinite;
  animation-delay: -0.5s, 0.6s;
  z-index: 2;
}

/* Ghost 3 - Closest */
.holographic-afterimage .ghost-3 {
  transform: translateX(-4px);
  opacity: 0.45;
  animation: holographic-shift 3s ease-in-out infinite, ghost-shimmer 2s
      ease-in-out infinite;
  animation-delay: -1s, 0.9s;
  z-index: 3;
}

/* Main character - solid, on top */
.holographic-afterimage .main-character {
  position: relative;
  z-index: 10;
  height: 100%;
  width: auto;
  display: block;
  image-rendering: pixelated;
}
```

### 2. Use in Components

Wrap your image in the holographic container and add ghost layers:

```tsx
<div className="holographic-afterimage">
  {/* Ghost layers - same image source */}
  <img
    src="/path/to/image.png"
    alt=""
    className="ghost-layer ghost-1"
    aria-hidden="true"
  />
  <img
    src="/path/to/image.png"
    alt=""
    className="ghost-layer ghost-2"
    aria-hidden="true"
  />
  <img
    src="/path/to/image.png"
    alt=""
    className="ghost-layer ghost-3"
    aria-hidden="true"
  />

  {/* Main character - the solid, clear image on top */}
  <img src="/path/to/image.png" alt="Character" className="main-character" />
</div>
```

> **Note**: All ghost layers use the same `src` as the main image. They're hidden from screen readers with `aria-hidden="true"`.

## Customization

### Change Trail Direction

Modify the `translateX` values in each ghost class:

| Direction   | Ghost 1                   | Ghost 2                 | Ghost 3                 |
| ----------- | ------------------------- | ----------------------- | ----------------------- |
| Left trail  | `translateX(-12px)`       | `translateX(-8px)`      | `translateX(-4px)`      |
| Right trail | `translateX(12px)`        | `translateX(8px)`       | `translateX(4px)`       |
| Up trail    | `translateY(-12px)`       | `translateY(-8px)`      | `translateY(-4px)`      |
| Diagonal    | `translate(-12px, -12px)` | `translate(-8px, -8px)` | `translate(-4px, -4px)` |

### Change Animation Speed

Modify the duration in the `animation` property:

```css
animation: holographic-shift 3s ease-in-out infinite; /* 3s = slower cycle */
animation: holographic-shift 1s ease-in-out infinite; /* 1s = faster cycle */
```

### Change Ghost Visibility

Adjust the `opacity` values:

```css
.ghost-1 {
  opacity: 0.25;
} /* Most transparent */
.ghost-2 {
  opacity: 0.35;
}
.ghost-3 {
  opacity: 0.45;
} /* Most visible ghost */
```

### Add More Ghost Layers

Create additional classes (ghost-4, ghost-5, etc.) with progressively smaller offsets:

```css
.holographic-afterimage .ghost-4 {
  transform: translateX(-2px);
  opacity: 0.55;
  animation: holographic-shift 3s ease-in-out infinite;
  animation-delay: -1.5s;
  z-index: 4;
}
```

### Change Color Cycle

Modify the `@keyframes holographic-shift` to use different hue values or add saturation/brightness variations.

For a **cooler tone** (blues/purples only):

```css
@keyframes holographic-cool {
  0%,
  100% {
    filter: hue-rotate(180deg) saturate(2);
  }
  50% {
    filter: hue-rotate(270deg) saturate(2.5);
  }
}
```

For a **warmer tone** (reds/oranges/yellows):

```css
@keyframes holographic-warm {
  0%,
  100% {
    filter: hue-rotate(0deg) saturate(2);
  }
  50% {
    filter: hue-rotate(60deg) saturate(2.5);
  }
}
```

## Responsive Considerations

Add media queries to reduce offset on smaller screens:

```css
@media (max-width: 768px) {
  .holographic-afterimage .ghost-1 {
    transform: translateX(-8px);
  }
  .holographic-afterimage .ghost-2 {
    transform: translateX(-5px);
  }
  .holographic-afterimage .ghost-3 {
    transform: translateX(-2px);
  }
}
```

## Performance Notes

- **GPU acceleration**: The `filter` and `transform` properties trigger GPU compositing
- **4 images per instance**: Each holographic effect loads the same image 4 times (3 ghosts + 1 main)
- **Continuous animation**: Consider pausing with `animation-play-state: paused` when not visible

## Current Usage

- [ComingSoon.tsx](../../src/components/sections/ComingSoon.tsx) - "Coming Soon" pages
- [LandingPage.tsx](../../src/components/LandingPage.tsx) - Homepage hero character
