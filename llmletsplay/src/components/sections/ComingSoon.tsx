import { LassSubpageLayout } from '../LassSubpageLayout'

export function ComingSoon({ title }: { title: string }) {
  return (
    <LassSubpageLayout hideCharacter={true}>
      <div className="coming-soon-wrapper">
        {/* Group Container - Anchors Character and Bubble together */}
        <div className="coming-soon-group">
          {/* Character Image */}
          <img 
            src="/lass/lass-coming-soon.png" 
            alt="Coming Soon" 
            className="coming-soon-character"
          />

          {/* Speech Bubble - Relative to Group */}
          <div className="coming-soon-bubble">
            <h2 className="coming-soon-title">
              COMING SOON
            </h2>
            <p className="coming-soon-text">
              {title} documentation is being prepared
            </p>
            
            {/* Desktop Tail (Right-Down) - Triangular pointing Right */}
            <svg 
              className="coming-soon-tail-desktop"
              viewBox="0 0 50 35"
            >
              <polygon 
                points="0,0 50,0 48,33"
                fill="var(--cream)"
                stroke="var(--accent-primary)"
                strokeWidth="2"
              />
              <rect x="0" y="-2" width="50" height="5" fill="var(--cream)" />
            </svg>

            {/* Tablet Tail (Left-Pointing) - Triangular pointing Left */}
            <svg 
              className="coming-soon-tail-tablet"
              viewBox="0 0 50 35"
            >
              <polygon 
                points="0,0 50,0 2,33"
                fill="var(--cream)"
                stroke="var(--accent-primary)"
                strokeWidth="2"
              />
              <rect x="0" y="-2" width="50" height="5" fill="var(--cream)" />
            </svg>

            {/* Mobile Tail (Centered) - Triangular */}
            <svg 
              className="coming-soon-tail-mobile"
              viewBox="0 0 40 30"
            >
              <polygon 
                points="0,0 40,0 20,28"
                fill="var(--cream)"
                stroke="var(--accent-primary)"
                strokeWidth="2"
              />
              <rect x="0" y="-2" width="40" height="5" fill="var(--cream)" />
            </svg>
          </div>
        </div>
      </div>
    </LassSubpageLayout>
  )
}
