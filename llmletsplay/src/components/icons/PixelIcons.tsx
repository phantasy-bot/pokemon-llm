
import React from 'react'

interface IconProps {
  size?: number
  color?: string
  style?: React.CSSProperties
}

export const PixelBrain = ({ size = 24, color = 'currentColor', style }: IconProps) => (
  <svg 
    width={size} 
    height={size} 
    viewBox="0 0 24 24" 
    fill="none" 
    xmlns="http://www.w3.org/2000/svg"
    style={style}
  >
    <path 
      d="M4 10H2V14H4V18H6V20H10V22H14V20H18V18H20V14H22V10H20V6H18V4H14V2H10V4H6V6H4V10ZM6 8V10H8V8H10V6H14V8H16V10H18V14H16V16H14V18H10V16H8V14H6V8Z" 
      fill={color} 
      fillRule="evenodd"
    />
    <rect x="10" y="8" width="4" height="2" fill={color}/>
    <rect x="8" y="10" width="2" height="4" fill={color}/>
    <rect x="14" y="10" width="2" height="4" fill={color}/>
    <rect x="10" y="14" width="4" height="2" fill={color}/>
  </svg>
)

export const PixelEye = ({ size = 24, color = 'currentColor', style }: IconProps) => (
  <svg 
    width={size} 
    height={size} 
    viewBox="0 0 24 24" 
    fill="none" 
    xmlns="http://www.w3.org/2000/svg"
    style={style}
  >
    <path 
      d="M2 12H4V10H6V8H10V6H14V8H18V10H20V12H22V14H20V16H18V18H14V20H10V18H6V16H4V14H2V12ZM4 12V14H6V16H10V18H14V16H18V14H20V12H18V10H14V8H10V10H6V12H4Z" 
      fill={color} 
      fillRule="evenodd"
    />
    <rect x="10" y="10" width="4" height="4" fill={color}/>
  </svg>
)

export const PixelSpeaker = ({ size = 24, color = 'currentColor', style }: IconProps) => (
  <svg 
    width={size} 
    height={size} 
    viewBox="0 0 24 24" 
    fill="none" 
    xmlns="http://www.w3.org/2000/svg"
    style={style}
  >
    <path 
      d="M2 8H6V6H8V4H10V2H12V22H10V20H8V18H6V16H2V8ZM4 10V14H6V16H8V18H10V6H8V8H6V10H4Z" 
      fill={color} 
      fillRule="evenodd"
    />
    <rect x="14" y="6" width="2" height="2" fill={color}/>
    <rect x="16" y="8" width="2" height="2" fill={color}/>
    <rect x="18" y="10" width="2" height="4" fill={color}/>
    <rect x="16" y="14" width="2" height="2" fill={color}/>
    <rect x="14" y="16" width="2" height="2" fill={color}/>
  </svg>
)

export const PixelHome = ({ size = 24, color = 'currentColor', style }: IconProps) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" style={style}>
    <path d="M10 20V14H14V20H19V12H22L12 3L2 12H5V20H10Z" fill={color} />
  </svg>
)

export const PixelGamepad = ({ size = 24, color = 'currentColor', style }: IconProps) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" style={style}>
    <path d="M2 12H4V10H6V8H18V10H20V12H22V16H20V18H18V20H6V18H4V16H2V12ZM6 14H8V16H6V14ZM16 14H18V16H16V14ZM8 12H10V14H8V12ZM14 12H16V14H14V12Z" fill={color} />
  </svg>
)

export const PixelPerson = ({ size = 24, color = 'currentColor', style }: IconProps) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" style={style}>
    <path d="M8 4H16V12H8V4ZM4 14H8V12H16V14H20V22H4V14Z" fill={color} />
  </svg>
)

export const PixelInfo = ({ size = 24, color = 'currentColor', style }: IconProps) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" style={style}>
    <path d="M10 4H14V8H10V4ZM10 10H14V20H10V10Z" fill={color} />
  </svg>
)

export const PixelChip = ({ size = 24, color = 'currentColor', style }: IconProps) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" style={style}>
    <path d="M4 4H20V20H4V4ZM6 6V18H18V6H6Z" fill={color} fillRule="evenodd" />
    <rect x="8" y="2" width="2" height="2" fill={color}/>
    <rect x="14" y="2" width="2" height="2" fill={color}/>
    <rect x="8" y="20" width="2" height="2" fill={color}/>
    <rect x="14" y="20" width="2" height="2" fill={color}/>
    <rect x="2" y="8" width="2" height="2" fill={color}/>
    <rect x="2" y="14" width="2" height="2" fill={color}/>
    <rect x="20" y="8" width="2" height="2" fill={color}/>
    <rect x="20" y="14" width="2" height="2" fill={color}/>
  </svg>
)

export const PixelBox = ({ size = 24, color = 'currentColor', style }: IconProps) => (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" style={style}>
      <path d="M4 4H20V20H4V4ZM6 6V18H18V6H6Z" fill={color} fillRule="evenodd"/>
      <rect x="8" y="8" width="8" height="8" fill={color}/>
    </svg>
)

export const PixelSitemap = ({ size = 24, color = 'currentColor', style }: IconProps) => (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" style={style}>
      <rect x="10" y="2" width="4" height="4" fill={color}/>
      <rect x="4" y="10" width="4" height="4" fill={color}/>
      <rect x="16" y="10" width="4" height="4" fill={color}/>
      <path d="M11 6V8H13V6H11Z" fill={color}/>
      <path d="M12 8V12H6V10" fill={color}/>
      <path d="M12 8V12H18V10" fill={color}/>
    </svg>
)


export const PixelSmile = ({ size = 24, color = 'currentColor', style }: IconProps) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" style={style}>
    <rect x="6" y="6" width="2" height="2" fill={color}/>
    <rect x="16" y="6" width="2" height="2" fill={color}/>
    <rect x="4" y="14" width="2" height="2" fill={color}/>
    <rect x="18" y="14" width="2" height="2" fill={color}/>
    <rect x="6" y="16" width="12" height="2" fill={color}/>
    <path d="M2 4H4V20H2V4ZM20 4H22V20H20V4ZM4 2H20V4H4V2ZM4 20H20V22H4V20Z" fill={color} fillRule="evenodd" opacity="0.5"/>
  </svg>
)

export const PixelTV = ({ size = 24, color = 'currentColor', style }: IconProps) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" style={style}>
    <path d="M2 6H22V18H2V6ZM8 20V22H16V20H8ZM12 2L14 4H10L12 2Z" fill={color} />
    <rect x="4" y="8" width="16" height="8" fill={color} fillOpacity="0.2"/>
    <rect x="16" y="10" width="2" height="4" fill={color}/>
  </svg>
)

export const PixelTerminal = ({ size = 24, color = 'currentColor', style }: IconProps) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" style={style}>
    <path d="M2 4H22V20H2V4ZM4 6V18H20V6H4ZM6 8V10H8V12H10V14H8V16H6V8ZM12 14H16V16H12V14Z" fill={color} />
  </svg>
)

