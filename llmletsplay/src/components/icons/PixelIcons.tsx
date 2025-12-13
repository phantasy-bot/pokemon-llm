
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
