import { useState } from 'react';
import { Polaroid } from './PolaroidStack';
import { ChevronLeft, ChevronRight } from 'lucide-react';

interface InteractivePolaroidStackProps {
  images: string[];
}

export function InteractivePolaroidStack({ images }: InteractivePolaroidStackProps) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [animating, setAnimating] = useState(false);
  const [direction, setDirection] = useState<'next' | 'prev'>('next');

  const handleNext = (e?: React.MouseEvent) => {
    e?.stopPropagation();
    if (animating) return;
    setDirection('next');
    setAnimating(true);
    setTimeout(() => {
      setCurrentIndex((prev) => (prev + 1) % images.length);
      setAnimating(false);
    }, 300);
  };

  const handlePrev = (e?: React.MouseEvent) => {
    e?.stopPropagation();
    if (animating) return;
    setDirection('prev');
    setAnimating(true);
    setTimeout(() => {
      setCurrentIndex((prev) => (prev - 1 + images.length) % images.length);
      setAnimating(false);
    }, 300);
  };

  if (!images || images.length === 0) return null;

  // We render the current top image and the next one behind it to maintain the "stack" illusion
  const currentImage = images[currentIndex];
  
  // For 'next', we show nextIndex behind. For 'prev', we show prevIndex behind?
  // Actually, 'prev' usually means the previous image comes onto the stack.
  // The transition logic I have is "current image flies away".
  // If I want 'prev', the 'prev' image should "fly in".
  // For simplicity, I'll keep the same animation (fly away) but just change the index, or reverse the fly direction.
  
  const nextIndex = (currentIndex + 1) % images.length;
  const nextImage = images[nextIndex];

  // Random-ish rotations based on index to make it feel natural
  const rotations = [-2, 1, -1, 2, -3, 3];
  const currentRotation = rotations[currentIndex % rotations.length];
  const nextRotation = rotations[nextIndex % rotations.length];

  return (
    <div className="relative w-full max-w-lg mx-auto h-[400px] flex items-center justify-center gap-4">
      {/* Prev Button */}
      {images.length > 1 && (
        <button 
          onClick={handlePrev}
          className="p-2 rounded-full hover:bg-white/10 text-zinc-400 hover:text-white transition-colors z-20"
        >
          <ChevronLeft size={32} />
        </button>
      )}

      <div className="relative w-64 h-64 md:w-80 md:h-80 flex items-center justify-center">
        {/* Back of stack (Next Image) - Visible peek */}
        {images.length > 1 && (
          <div 
            className="absolute transition-transform duration-500 ease-in-out"
            style={{ 
              transform: `rotate(${nextRotation}deg) scale(0.95)`,
              zIndex: 0
            }}
          >
            <Polaroid src={nextImage} alt="Next" />
          </div>
        )}

        {/* Top Image - Click to cycle */}
        <div 
          className={`absolute cursor-pointer transition-all duration-300 ease-in-out z-10 
            ${animating 
              ? (direction === 'next' ? 'opacity-0 translate-x-20 rotate-12' : 'opacity-0 -translate-x-20 -rotate-12') 
              : 'opacity-100'}`}
          style={{ 
            transform: !animating ? `rotate(${currentRotation}deg)` : undefined
          }}
          onClick={handleNext}
        >
          <Polaroid src={currentImage} alt="Current" />
          
          {/* Counter Centered */}
          {images.length > 1 && (
            <div className="absolute -bottom-8 left-0 right-0 text-center text-xs font-mono text-zinc-400">
              {currentIndex + 1} / {images.length} • Click to cycle
            </div>
          )}
        </div>
      </div>

      {/* Next Button */}
      {images.length > 1 && (
        <button 
          onClick={handleNext}
          className="p-2 rounded-full hover:bg-white/10 text-zinc-400 hover:text-white transition-colors z-20"
        >
          <ChevronRight size={32} />
        </button>
      )}
    </div>
  );
}
