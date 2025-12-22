import { Polaroid } from './PolaroidStack'

interface PolaroidGalleryProps {
  images: string[];
}

export function PolaroidGallery({ images }: PolaroidGalleryProps) {
  if (!images || images.length === 0) return null;

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-12 p-8 md:p-12 bg-zinc-900/5 rounded-xl border-2 border-dashed border-black/10">
      {images.map((src, i) => (
        <div 
          key={i} 
          className="transform transition-all duration-500 hover:scale-110 hover:z-10 hover:rotate-0"
          style={{ 
            transform: `rotate(${i % 2 === 0 ? '-2deg' : '2deg'})`
          }}
        >
           <Polaroid src={src} alt={`Gallery Image ${i+1}`} />
        </div>
      ))}
    </div>
  )
}
