import { LassSubpageLayout } from '../LassSubpageLayout'

export function ComingSoon({ title }: { title: string }) {
  return (
    <LassSubpageLayout hideCharacter={true}>
      <div className="coming-soon-wrapper">
        {/* Character Image */}
        <img 
          src="/lass/lass-coming-soon.png" 
          alt="Coming Soon" 
          className="coming-soon-character"
        />

        {/* Speech Bubble */}
        <div className="coming-soon-bubble">
          <h2 className="coming-soon-title">
            COMING SOON
          </h2>
          <p className="coming-soon-text">
            {title} documentation is being prepared
          </p>
          
          {/* Desktop Tail (Right-Down) */}
          <svg 
            className="coming-soon-tail-desktop"
            viewBox="0 0 50 35"
          >
            <path 
              d="M 5 0 Q 10 15, 25 25 Q 40 35, 50 35 Q 35 30, 30 20 Q 25 10, 15 0 Z"
              fill="var(--cream)"
              stroke="var(--accent-primary)"
              strokeWidth="2"
            />
            <rect x="3" y="-2" width="15" height="6" fill="var(--cream)" />
          </svg>

          {/* Mobile Tail (Centered) - Symmetric beak */}
          <svg 
            className="coming-soon-tail-mobile"
            viewBox="0 0 40 30"
          >
            <path 
              d="M 0 0 Q 10 10, 20 30 Q 30 10, 40 0 Z"
              fill="var(--cream)"
              stroke="var(--accent-primary)"
              strokeWidth="2"
            />
             <rect x="0" y="-2" width="40" height="4" fill="var(--cream)" />
          </svg>
        </div>
      </div>
    </LassSubpageLayout>
  )
}
