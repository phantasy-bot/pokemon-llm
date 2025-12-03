import type { BadgeType } from "../../types/gameTypes";
import "./BadgeDisplay.css";

interface BadgeDisplayProps {
  badges: BadgeType[];
  className?: string;
}

// Kanto gym badges with emoji mapping and gym leader info
const KANTO_BADGES: Record<
  BadgeType,
  { emoji: string; gymLeader: string; location: string; type: string }
> = {
  Boulder: {
    emoji: "🪨",
    gymLeader: "Brock",
    location: "Pewter City",
    type: "Rock",
  },
  Cascade: {
    emoji: "💧",
    gymLeader: "Misty",
    location: "Cerulean City",
    type: "Water",
  },
  Thunder: {
    emoji: "⚡",
    gymLeader: "Lt. Surge",
    location: "Vermilion City",
    type: "Electric",
  },
  Rainbow: {
    emoji: "🌈",
    gymLeader: "Erika",
    location: "Celadon City",
    type: "Grass",
  },
  Soul: {
    emoji: "💜",
    gymLeader: "Koga",
    location: "Fuchsia City",
    type: "Poison",
  },
  Marsh: {
    emoji: "🐸",
    gymLeader: "Sabrina",
    location: "Saffron City",
    type: "Psychic",
  },
  Volcano: {
    emoji: "🌋",
    gymLeader: "Blaine",
    location: "Cinnabar Island",
    type: "Fire",
  },
  Earth: {
    emoji: "🌍",
    gymLeader: "Giovanni",
    location: "Viridian City",
    type: "Ground",
  },
};

export function BadgeDisplay({ badges, className = "" }: BadgeDisplayProps) {
  const earnedBadges = new Set(badges);
  const badgeEntries = Object.entries(KANTO_BADGES) as [
    BadgeType,
    (typeof KANTO_BADGES)[BadgeType],
  ][];

  return (
    <div className={`badge-display ${className}`}>
      <div className="badge-display__track">
        {badgeEntries.map(([badgeType, badgeInfo], index) => {
          const isEarned = earnedBadges.has(badgeType);
          const isNextBadge = !isEarned && index === earnedBadges.size;

          return (
            <div key={badgeType} className="badge-display__node-wrapper">
              <div
                className={`badge-display__badge badge-display__badge--${
                  isEarned ? "earned" : isNextBadge ? "next" : "locked"
                }`}
                title={`${badgeInfo.gymLeader}'s ${badgeInfo.type} Badge (${badgeInfo.location})`}
              >
                <div className="badge-display__badge-emoji">
                  {isEarned ? badgeInfo.emoji : "🔒"}
                </div>
                <div className="badge-display__badge-info">
                  <span className="badge-display__badge-name">{badgeType}</span>
                  <span className="badge-display__badge-leader">
                    {badgeInfo.gymLeader}
                  </span>
                </div>
              </div>

              {/* Connector line between badges */}
              {index < badgeEntries.length - 1 && (
                <div
                  className={`badge-display__connector badge-display__connector--${
                    isEarned ? "earned" : "locked"
                  }`}
                />
              )}
            </div>
          );
        })}
      </div>

      {/* Progress indicator */}
      <div className="badge-display__progress">
        <span className="badge-display__progress-text">
          {earnedBadges.size}/8 Badges
        </span>
        <div className="badge-display__progress-bar">
          <div
            className="badge-display__progress-fill"
            style={{ width: `${(earnedBadges.size / 8) * 100}%` }}
          />
        </div>
      </div>

      {/* Legend status */}
      {earnedBadges.size === 8 && (
        <div className="badge-display__legend-status">
          <span className="badge-display__legend-icon">👑</span>
          <span className="badge-display__legend-text">
            Ready for Indigo Plateau!
          </span>
        </div>
      )}
    </div>
  );
}
