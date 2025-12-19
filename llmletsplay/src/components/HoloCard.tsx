import React, { useRef, useState } from 'react';
import './CardGallery.css';

interface CardType {
  name: string;
  rarity: string;
  description: string;
  image: string;
  dataAttributes?: Record<string, string>;
}

export function HoloCard({ cardType, isActive = true }: { cardType: CardType; isActive?: boolean }) {
  const cardRef = useRef<HTMLDivElement>(null);
  const [position, setPosition] = useState({ x: 50, y: 50 });
  const [rotation, setRotation] = useState({ rx: 0, ry: 0 });
  const [isInteracting, setIsInteracting] = useState(false);

  const updateCardTransform = (clientX: number, clientY: number) => {
    if (!cardRef.current || !isActive) return;
    const rect = cardRef.current.getBoundingClientRect();
    const x = ((clientX - rect.left) / rect.width) * 100;
    const y = ((clientY - rect.top) / rect.height) * 100;
    const rx = ((y - 50) / 50) * -15;
    const ry = ((x - 50) / 50) * 15;

    setPosition({ x, y });
    setRotation({ rx, ry });
  };

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    updateCardTransform(e.clientX, e.clientY);
  };

  const handleTouchMove = (e: React.TouchEvent<HTMLDivElement>) => {
    if (e.touches.length > 0) {
      const touch = e.touches[0];
      updateCardTransform(touch.clientX, touch.clientY);
    }
  };

  const handleInteractionStart = () => setIsInteracting(true);

  const handleInteractionEnd = () => {
    setIsInteracting(false);
    setPosition({ x: 50, y: 50 });
    setRotation({ rx: 0, ry: 0 });
  };

  const hyp = Math.sqrt(Math.pow((position.x - 50) / 50, 2) + Math.pow((position.y - 50) / 50, 2));

  return (
    <div
      ref={cardRef}
      className={`card ${isActive ? 'active' : ''} ${isInteracting ? 'interacting' : ''}`}
      data-rarity={cardType.rarity}
      {...(cardType.dataAttributes || {})}
      style={
        {
          '--mx': `${position.x}%`,
          '--my': `${position.y}%`,
          '--posx': `${position.x}%`,
          '--posy': `${position.y}%`,
          '--pos': `${position.x}% ${position.y}%`,
          '--rx': `${rotation.ry}deg`,
          '--ry': `${rotation.rx}deg`,
          '--hyp': hyp,
          '--o': isInteracting ? 1 : 0,
          width: '280px', // Default width
          height: '390px', // Default height based on standard card ratio
          cursor: 'pointer',
        } as React.CSSProperties
      }
      onMouseEnter={handleInteractionStart}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleInteractionEnd}
      onTouchStart={handleInteractionStart}
      onTouchMove={handleTouchMove}
      onTouchEnd={handleInteractionEnd}
      onTouchCancel={handleInteractionEnd}
    >
      <div className="card__translater">
        <div className="card__rotator">
          <div className="card__front">
            <img src={cardType.image} alt={cardType.name} className="card__image" />
            <div className="card__shine"></div>
            <div className="card__glare"></div>
          </div>
        </div>
      </div>
    </div>
  );
}
