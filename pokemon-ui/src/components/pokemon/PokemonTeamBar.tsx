import { useRef, useEffect, useState } from "react";
import type { PokemonTeamBarProps } from "../../types/display";
import { PokemonCard } from "./PokemonCard";
import { Minimap } from "./Minimap";
import "./PokemonTeamBar.css";

const SCROLL_SPEED = 50;
const PAUSE_DURATION = 3000;

interface ExtendedPokemonTeamBarProps extends PokemonTeamBarProps {
  minimapLocation?: string;
  minimapTimestamp?: string;
  minimapVisible?: boolean;
  explorationPct?: number; // Exploration percentage for current map
  lassMarkings?: Array<{  // Lass's minimap overlay markers
    x: number;
    y: number;
    type: 'N' | 'O';
    opacity: number;
    age_hours?: number;
  }>;
  minimapGridSize?: { width: number; height: number }; // Grid dimensions for overlay
}

export function PokemonTeamBar({ 
  pokemon,
  minimapLocation = "Unknown Area",
  minimapTimestamp,
  minimapVisible = true,
  explorationPct,
  lassMarkings,
  minimapGridSize,
}: ExtendedPokemonTeamBarProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [isOverflowing, setIsOverflowing] = useState(false);

  // Filter out empty slots and fainted Pokemon for display purposes
  const activePokemon = pokemon.filter((p) => p && !p.isFainted);

  useEffect(() => {
    const container = scrollRef.current;
    if (!container) return;

    const checkOverflow = () => {
      setIsOverflowing(container.scrollWidth > container.clientWidth);
    };

    checkOverflow();
    window.addEventListener("resize", checkOverflow);
    return () => window.removeEventListener("resize", checkOverflow);
  }, [activePokemon.length]);

  useEffect(() => {
    const container = scrollRef.current;
    if (!container || !isOverflowing) return;

    let animationId: number;
    let direction = 1;
    let isPaused = false;
    let pauseTimeout: ReturnType<typeof setTimeout>;

    const animate = () => {
      if (isPaused) {
        animationId = requestAnimationFrame(animate);
        return;
      }

      const maxScroll = container.scrollWidth - container.clientWidth;
      const currentScroll = container.scrollLeft;

      if (direction === 1 && currentScroll >= maxScroll) {
        isPaused = true;
        pauseTimeout = setTimeout(() => {
          direction = -1;
          isPaused = false;
        }, PAUSE_DURATION);
      } else if (direction === -1 && currentScroll <= 0) {
        isPaused = true;
        pauseTimeout = setTimeout(() => {
          direction = 1;
          isPaused = false;
        }, PAUSE_DURATION);
      } else {
        container.scrollLeft += direction * (SCROLL_SPEED / 60);
      }

      animationId = requestAnimationFrame(animate);
    };

    const startTimeout = setTimeout(() => {
      animationId = requestAnimationFrame(animate);
    }, PAUSE_DURATION);

    return () => {
      cancelAnimationFrame(animationId);
      clearTimeout(startTimeout);
      clearTimeout(pauseTimeout);
    };
  }, [isOverflowing]);

  // Transform Pokemon data to display format
  const transformedPokemon = pokemon.map((p, index) => ({
    id: p.id || `pokemon-${index}`,
    name: p.name,
    nickname: p.nickname,
    level: p.level,
    type: p.type,
    type2: p.type2,
    hp: p.hp,
    maxHp: p.maxHp,
    hpPercent: p.maxHp > 0 ? (p.hp / p.maxHp) * 100 : 0,
    hpStatus: (p.hp <= 0
      ? "critical"
      : p.hp < p.maxHp * 0.3
        ? "wounded"
        : "healthy") as "healthy" | "wounded" | "critical",
    isFainted: p.hp <= 0,
    status: p.status,
  }));

  return (
    <div className="pokemon-team-bar">
      <div className="pokemon-team-bar__main">
        <div className="pokemon-team-bar__header">
          <h2 className="pokemon-team-bar__title">Pokemon Team</h2>
          <span className="pokemon-team-bar__count">
            {activePokemon.length}/{pokemon.length} active
          </span>
        </div>

        <div className="pokemon-team-bar__grid">
          {transformedPokemon.map((p) => (
            <div key={p.id} className="pokemon-team-grid-item">
              <PokemonCard pokemon={p} />
            </div>
          ))}
          {/* Empty slots to show 6 total */}
          {Array.from({ length: Math.max(0, 6 - pokemon.length) }).map(
            (_, index) => (
              <div key={`empty-${index}`} className="pokemon-empty-slot">
                <span className="pokemon-empty-slot__text">EMPTY</span>
              </div>
            ),
          )}
        </div>
      </div>

      <div className="pokemon-team-bar__minimap">
        <Minimap
          location={minimapLocation}
          visible={minimapVisible}
          timestamp={minimapTimestamp}
          explorationPct={explorationPct}
          lassMarkings={lassMarkings}
          minimapGridSize={minimapGridSize}
          className="pokemon-team-bar__minimap-component"
        />
      </div>
    </div>
  );
}
