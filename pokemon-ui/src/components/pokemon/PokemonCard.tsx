/**
 * PokemonCard component for displaying Pokemon team member info.
 *
 * Displays Pokemon name, level, type, HP, and status in a card format
 * adapted from the Fire Emblem UnitCard component.
 */

import type { PokemonCardProps } from "../../types/display";
import { HPBar } from "../units/HPBar";
import "./PokemonCard.css";

/**
 * Convert Pokemon name to sprite URL path
 * Handles special cases like "Mr. Mime", "Nidoran♀", "Farfetch'd"
 */
function getPokemonSpriteUrl(name: string): string {
  // Convert to lowercase and handle special characters
  let filename = name
    .toLowerCase()
    .replace(/♀/g, "-f")      // Nidoran♀ → nidoran-f
    .replace(/♂/g, "-m")      // Nidoran♂ → nidoran-m
    .replace(/\./g, "")       // Mr. Mime → mr mime
    .replace(/'/g, "")        // Farfetch'd → farfetchd
    .replace(/\s+/g, "-")     // spaces → hyphens
    .replace(/-+/g, "-")      // multiple hyphens → single hyphen
    .trim();
  
  return `/sprites/pokemon/${filename}.png`;
}

export function PokemonCard({ pokemon, compact = false }: PokemonCardProps) {
  const faintedClass = pokemon.isFainted ? "fainted" : "";
  const spriteUrl = getPokemonSpriteUrl(pokemon.name);

  return (
    <div
      className={`pokemon-card ${faintedClass} ${compact ? "pokemon-card--compact" : ""}`}
      style={{
        // Pokemon type background gradient - will be enhanced with CSS variables
        background: pokemon.isFainted
          ? "linear-gradient(to bottom, rgba(128, 128, 128, 0.15), #808080)"
          : `linear-gradient(to bottom, rgba(255,255,255,0.15), ${getPokemonTypeColor(pokemon.type)})`,
      }}
    >
      {/* Pokemon sprite */}
      <div className="pokemon-card__sprite-container">
        <img
          src={spriteUrl}
          alt={pokemon.name}
          className="pokemon-card__sprite"
          onError={(e) => {
            // Hide broken images
            (e.target as HTMLImageElement).style.display = 'none';
          }}
        />
      </div>

      <div className="pokemon-card__info">
        <div className="pokemon-card__header">
          <span className="pokemon-card__name">
            {pokemon.nickname || pokemon.name}
          </span>
          <span className="pokemon-card__level">Lv.{pokemon.level}</span>
        </div>

        <HPBar
          current={pokemon.hp}
          max={pokemon.maxHp}
          showNumbers={!compact}
          size={compact ? "sm" : "md"}
        />

        <div className="pokemon-card__type-row">
          <span className="pokemon-card__type">{pokemon.type}</span>
          {pokemon.type2 && (
            <span className="pokemon-card__type pokemon-card__type--secondary">
              {pokemon.type2}
            </span>
          )}
        </div>

        {/* Status condition display */}
        {pokemon.status && pokemon.status !== "None" && (
          <div className="pokemon-card__status">
            <span className="pokemon-card__status-text">{pokemon.status}</span>
          </div>
        )}

        {/* Fainted indicator */}
        {pokemon.isFainted && (
          <div className="pokemon-card__fainted-overlay">
            <span className="pokemon-card__fainted-text">FAINTED</span>
          </div>
        )}
      </div>
    </div>
  );
}

// Helper function to get Pokemon type colors (from Vue app)
function getPokemonTypeColor(type: string): string {
  const typeColors: Record<string, string> = {
    Water: "#4fc3f7",
    Grass: "#81c784",
    Poison: "#ba68c8",
    Electric: "#ffd54f",
    Rock: "#a1887f",
    Ground: "#d7ccc8",
    Fighting: "#e57373",
    Normal: "#bdbdbd",
    Bug: "#cddc39",
    Ghost: "#9575cd",
    Steel: "#b0bec5",
    Fire: "#ff8a65",
    Psychic: "#f06292",
    Ice: "#80deea",
    Dragon: "#7e57c2",
    Dark: "#757575",
    Fairy: "#f48fb1",
    Flying: "#90a4ae",
  };

  return typeColors[type] || "#aaaaaa";
}
