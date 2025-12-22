import { useParams, useOutletContext } from 'react-router-dom';
import { Notebook } from '../components/Notebook';
import { InteractivePolaroidStack } from '../components/InteractivePolaroidStack';
import { Polaroid } from '../components/PolaroidStack';
import { type Drop } from '../lib/api';

interface ContentContext {
  drops: Drop[];
  currentIndex: number;
  setCurrentIndex: React.Dispatch<React.SetStateAction<number>>;
  handleBackToTimeline: () => void;
}

export function ContentPage() {
  const { id } = useParams();
  const { handleBackToTimeline } = useOutletContext<ContentContext>();
  
  // Teaser Logic
  const TEASER_ADDRESS = "0x5555555555555555555555555555555555555555";
  const isTeaser = (id?.toLowerCase() === TEASER_ADDRESS.toLowerCase()) || id === 'LLP-001'; 
  
  const content = {
    title: isTeaser ? "The Journey Begins!" : "Locked Memory",
    date: "Dec 20, 2025",
    text: isTeaser 
      ? "Dear Diary,\n\nToday Professor Oak gave me my very first Pokemon! *sparkle* Pikachu is cute but a bit stubborn. We battled Blue right in the lab - it was intense but we pulled through! (He's so annoying >_<)\n\nMom gave me the Running Shoes (finally!!). I'm heading to Viridian City now. The tall grass is scary but I'm ready. \n\nI can't believe I'm finally a trainer. I wonder what kind of Pokemon I'll meet? I hope I can find a Jigglypuff.\n\n- Lass <3"
      : "This content is locked. Please unlock it from the timeline.",
    images: isTeaser 
      ? [
          "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/25.png",
          "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/1.png",
          "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/4.png",
          "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/7.png"
        ]
      : []
  };

  // U-shape rotations for desktop - creates a parabola effect
  const getUShapeStyle = (index: number, total: number) => {
    // Calculate position from center (-1 to 1)
    const centerOffset = (index - (total - 1) / 2) / ((total - 1) / 2 || 1);
    // Parabola: edges higher, center lower (y = x^2 effect) - more dramatic
    const yOffset = Math.pow(centerOffset, 2) * 50; // Max 50px lift at edges
    // Rotation: edges tilt outward more dramatically
    const rotation = centerOffset * 12; // Max 12deg rotation at edges
    
    return {
      transform: `translateY(-${yOffset}px) rotate(${rotation}deg)`,
    };
  };

  if (!isTeaser) {
      return (
        <div className="flex flex-col items-center justify-center p-8 text-center min-h-[400px]">
            <h1 className="text-4xl font-display font-bold mb-4 text-ink">CONTENT LOCKED</h1>
            <p className="mb-8 font-mono text-ink-light">Please authenticate via the Timeline to view this memory.</p>
            <button 
              onClick={handleBackToTimeline}
              className="px-6 py-3 bg-black text-white font-mono uppercase tracking-widest text-sm shadow-brutal-sm rounded-full"
            >
                Return to Timeline
            </button>
        </div>
      )
  }

  return (
    <div className="w-full flex flex-col items-center">
      <div className="flex flex-col items-center gap-8 w-full max-w-4xl">
         {/* Photos Section */}
         <div className="w-full px-4">
           {/* Desktop: U-shape row layout - full width with more gap */}
           <div className="hidden lg:flex justify-between items-end gap-8 py-12 w-full">
             {content.images.map((img, idx) => (
               <div 
                 key={idx} 
                 className="flex-1 flex justify-center transition-transform duration-300 hover:scale-105 hover:-translate-y-2"
                 style={getUShapeStyle(idx, content.images.length)}
               >
                 <Polaroid src={img} alt={`Photo ${idx + 1}`} className="w-full max-w-[180px]" />
               </div>
             ))}
           </div>

           {/* Mobile/Tablet: Interactive slider */}
           <div className="lg:hidden py-4 w-full flex justify-center">
             <InteractivePolaroidStack images={content.images} />
           </div>
         </div>

         {/* Bottom: Notebook - WITH graphite construction paper background */}
         <div className="w-full px-4">
           <div className="bg-zinc-700 p-6 lg:p-10 shadow-inner">
             <Notebook title={content.title} date={content.date} content={content.text} />
           </div>
         </div>
      </div>
    </div>
  )
}
