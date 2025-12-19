import { Icon } from '@iconify/react'
import React from 'react'

interface IconProps {
  size?: number
  color?: string
  style?: React.CSSProperties
}

// Streamline Pixel icons via Iconify
// Icon naming: streamline-pixel:{category}-{name}

// Navigation icons
export const PixelHome2 = ({ size = 24, color = 'currentColor', style }: IconProps) => (
  <Icon icon="streamline-pixel:interface-essential-home-2" width={size} height={size} color={color} style={style} />
)

export const PixelHeart = ({ size = 24, color = 'currentColor', style }: IconProps) => (
  <Icon icon="streamline-pixel:interface-essential-heart-favorite" width={size} height={size} color={color} style={style} />
)

export const PixelInfo = ({ size = 24, color = 'currentColor', style }: IconProps) => (
  <Icon icon="streamline-pixel:interface-essential-information-circle-1" width={size} height={size} color={color} style={style} />
)

export const PixelChip = ({ size = 24, color = 'currentColor', style }: IconProps) => (
  <Icon icon="streamline-pixel:computers-devices-electronics-chipset" width={size} height={size} color={color} style={style} />
)

export const PixelHierarchy = ({ size = 24, color = 'currentColor', style }: IconProps) => (
  <Icon icon="streamline-pixel:interface-essential-hierarchy-1" width={size} height={size} color={color} style={style} />
)

export const PixelLoadingCircle = ({ size = 24, color = 'currentColor', style }: IconProps) => (
  <Icon icon="streamline-pixel:interface-essential-loading-circle-1" width={size} height={size} color={color} style={style} />
)

export const PixelTerminal = ({ size = 24, color = 'currentColor', style }: IconProps) => (
  <Icon icon="streamline-pixel:coding-apps-websites-programming-browser" width={size} height={size} color={color} style={style} />
)

export const PixelTV = ({ size = 24, color = 'currentColor', style }: IconProps) => (
  <Icon icon="streamline-pixel:video-movies-vintage-tv-1" width={size} height={size} color={color} style={style} />
)

// External link icon
export const PixelExternalLink = ({ size = 24, color = 'currentColor', style }: IconProps) => (
  <Icon icon="streamline-pixel:interface-essential-link" width={size} height={size} color={color} style={style} />
)

// Tech specs icons
export const PixelBrain = ({ size = 24, color = 'currentColor', style }: IconProps) => (
  <Icon icon="streamline-pixel:health-brain-1" width={size} height={size} color={color} style={style} />
)

export const PixelEye = ({ size = 24, color = 'currentColor', style }: IconProps) => (
  <Icon icon="streamline-pixel:interface-essential-view-eye" width={size} height={size} color={color} style={style} />
)

export const PixelSpeaker = ({ size = 24, color = 'currentColor', style }: IconProps) => (
  <Icon icon="streamline-pixel:music-speaker" width={size} height={size} color={color} style={style} />
)

// Gender icons
export const PixelGenderFemale = ({ size = 24, color = 'currentColor', style }: IconProps) => (
  <Icon icon="streamline-pixel:user-gender-female" width={size} height={size} color={color} style={style} />
)

// Social media icons
export const TwitterCircle = ({ size = 24, color = 'currentColor', style }: IconProps) => (
  <Icon icon="streamline-pixel:logo-social-media-twitter-circle" width={size} height={size} color={color} style={style} />
)

export const TwitchLogo = ({ size = 24, color = 'currentColor', style }: IconProps) => (
  <Icon icon="streamline-pixel:logo-twitch-1" width={size} height={size} color={color} style={style} />
)

export const InstagramCircle = ({ size = 24, color = 'currentColor', style }: IconProps) => (
  <Icon icon="streamline-pixel:logo-social-media-instagram-circle" width={size} height={size} color={color} style={style} />
)

// Legacy exports for backwards compatibility
export const PixelHome = PixelHome2
export const PixelGamepad = PixelLoadingCircle
export const PixelSitemap = PixelHierarchy
export const PixelSmile = PixelHeart
export const PixelPerson = PixelGenderFemale
export const PixelBox = PixelChip

// Additional cute icons for enhanced UI
export const PixelStar = ({ size = 24, color = 'currentColor', style }: IconProps) => (
  <Icon icon="streamline-pixel:interface-essential-star" width={size} height={size} color={color} style={style} />
)

export const PixelSparkle = ({ size = 24, color = 'currentColor', style }: IconProps) => (
  <Icon icon="streamline-pixel:interface-essential-magic-wand" width={size} height={size} color={color} style={style} />
)

export const PixelGameController = ({ size = 24, color = 'currentColor', style }: IconProps) => (
  <Icon icon="streamline-pixel:entertainment-game-controller" width={size} height={size} color={color} style={style} />
)

export const PixelLightning = ({ size = 24, color = 'currentColor', style }: IconProps) => (
  <Icon icon="streamline-pixel:interface-essential-flash-1" width={size} height={size} color={color} style={style} />
)

export const PixelClock = ({ size = 24, color = 'currentColor', style }: IconProps) => (
  <Icon icon="streamline-pixel:interface-essential-clock" width={size} height={size} color={color} style={style} />
)

export const PixelSettings = ({ size = 24, color = 'currentColor', style }: IconProps) => (
  <Icon icon="streamline-pixel:interface-essential-settings-cog" width={size} height={size} color={color} style={style} />
)

export const PixelUser = ({ size = 24, color = 'currentColor', style }: IconProps) => (
  <Icon icon="streamline-pixel:user-single" width={size} height={size} color={color} style={style} />
)

export const PixelDatabase = ({ size = 24, color = 'currentColor', style }: IconProps) => (
  <Icon icon="streamline-pixel:interface-essential-database" width={size} height={size} color={color} style={style} />
)

export const PixelPlay = ({ size = 24, color = 'currentColor', style }: IconProps) => (
  <Icon icon="streamline-pixel:interface-essential-button-play" width={size} height={size} color={color} style={style} />
)

export const PixelCode = ({ size = 24, color = 'currentColor', style }: IconProps) => (
  <Icon icon="streamline-pixel:interface-essential-edit-code" width={size} height={size} color={color} style={style} />
)

export const PixelMessage = ({ size = 24, color = 'currentColor', style }: IconProps) => (
  <Icon icon="streamline-pixel:interface-essential-chat-bubble-oval" width={size} height={size} color={color} style={style} />
)

export const PixelMap = ({ size = 24, color = 'currentColor', style }: IconProps) => (
  <Icon icon="streamline-pixel:interface-essential-map" width={size} height={size} color={color} style={style} />
)

export const PixelMemory = ({ size = 24, color = 'currentColor', style }: IconProps) => (
  <Icon icon="streamline-pixel:computers-devices-electronics-memory" width={size} height={size} color={color} style={style} />
)

export const PixelPlugin = ({ size = 24, color = 'currentColor', style }: IconProps) => (
  <Icon icon="streamline-pixel:coding-apps-websites-plugin" width={size} height={size} color={color} style={style} />
)

export const PixelLayer = ({ size = 24, color = 'currentColor', style }: IconProps) => (
  <Icon icon="streamline-pixel:design-layer" width={size} height={size} color={color} style={style} />
)

export const PixelPinLocation = ({ size = 24, color = 'currentColor', style }: IconProps) => (
  <Icon icon="streamline-pixel:map-navigation-pin-location-2" width={size} height={size} color={color} style={style} />
)

export const PixelTextFormat = ({ size = 24, color = 'currentColor', style }: IconProps) => (
  <Icon icon="streamline-pixel:interface-essential-text-format-2" width={size} height={size} color={color} style={style} />
)

export const PixelQuestion = ({ size = 24, color = 'currentColor', style }: IconProps) => (
  <Icon icon="streamline-pixel:interface-essential-question-help-square" width={size} height={size} color={color} style={style} />
)

export const PixelChatEmail = ({ size = 24, color = 'currentColor', style }: IconProps) => (
  <Icon icon="streamline-pixel:chat-email" width={size} height={size} color={color} style={style} />
)

export const PixelTarget = ({ size = 24, color = 'currentColor', style }: IconProps) => (
  <Icon icon="streamline-pixel:interface-essential-target" width={size} height={size} color={color} style={style} />
)

export const PixelCheck = ({ size = 24, color = 'currentColor', style }: IconProps) => (
  <Icon icon="streamline-pixel:interface-essential-check" width={size} height={size} color={color} style={style} />
)

export const PixelList = ({ size = 24, color = 'currentColor', style }: IconProps) => (
  <Icon icon="streamline-pixel:interface-essential-list-bullets" width={size} height={size} color={color} style={style} />
)

export const PixelGrid = ({ size = 24, color = 'currentColor', style }: IconProps) => (
  <Icon icon="streamline-pixel:interface-layout-grid-4" width={size} height={size} color={color} style={style} />
)

export const PixelSearch = ({ size = 24, color = 'currentColor', style }: IconProps) => (
  <Icon icon="streamline-pixel:interface-search-magnifying-glass" width={size} height={size} color={color} style={style} />
)

export const PixelAttack = ({ size = 24, color = 'currentColor', style }: IconProps) => (
  <Icon icon="streamline-pixel:weather-meteor" width={size} height={size} color={color} style={style} />
)

export const PixelThinkChat = ({ size = 24, color = 'currentColor', style }: IconProps) => (
  <Icon icon="streamline-pixel:email-chat-think" width={size} height={size} color={color} style={style} />
)

export const PixelRatingStar = ({ size = 24, color = 'currentColor', style }: IconProps) => (
  <Icon icon="streamline-pixel:social-rewards-rating-star-1" width={size} height={size} color={color} style={style} />
)

export const PixelSearchUser = ({ size = 24, color = 'currentColor', style }: IconProps) => (
  <Icon icon="streamline-pixel:search-user" width={size} height={size} color={color} style={style} />
)

export const PixelNotepad = ({ size = 24, color = 'currentColor', style }: IconProps) => (
  <Icon icon="streamline-pixel:content-files-notepad" width={size} height={size} color={color} style={style} />
)

export const PixelThinkChat = ({ size = 24, color = 'currentColor', style }: IconProps) => (
  <Icon icon="streamline-pixel:email-chat-think" width={size} height={size} color={color} style={style} />
)

export const PixelRatingStar = ({ size = 24, color = 'currentColor', style }: IconProps) => (
  <Icon icon="streamline-pixel:social-rewards-rating-star-1" width={size} height={size} color={color} style={style} />
)

export const PixelSearchUser = ({ size = 24, color = 'currentColor', style }: IconProps) => (
  <Icon icon="streamline-pixel:search-user" width={size} height={size} color={color} style={style} />
)

export const PixelNotepad = ({ size = 24, color = 'currentColor', style }: IconProps) => (
  <Icon icon="streamline-pixel:content-files-notepad" width={size} height={size} color={color} style={style} />
)

export const PixelCard = ({ size = 24, color = 'currentColor', style }: IconProps) => (
  <Icon icon="streamline-pixel:entertainment-events-hobbies-card-game-card-club" width={size} height={size} color={color} style={style} />
)

export const PixelCoin = ({ size = 24, color = 'currentColor', style }: IconProps) => (
  <Icon icon="streamline-pixel:business-money-coin-currency" width={size} height={size} color={color} style={style} />
)
