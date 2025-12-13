import { LassSubpageLayout } from '../LassSubpageLayout'

export function ComingSoon({ title }: { title: string }) {
  return (
    <LassSubpageLayout characterImage="/lass/lass-coming-soon.png">
      <div className="section" style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'flex-start',
        justifyContent: 'flex-start',
        minHeight: '50vh',
        gap: '24px',
        position: 'relative',
        paddingTop: '40px'
      }}>
        {/* Speech Bubble */}
        <div style={{
          position: 'relative',
          padding: '24px 48px',
          background: 'var(--cream)',
          border: '2px solid var(--accent-primary)',
          borderRadius: '12px',
          boxShadow: '4px 4px 0 rgba(0,0,0,0.1)',
          maxWidth: '400px'
        }}>
          <h2 style={{
            fontFamily: 'var(--font-display)',
            fontSize: '28px',
            color: 'var(--text-primary)',
            margin: '0 0 8px 0',
            letterSpacing: '2px'
          }}>
            COMING SOON
          </h2>
          <p style={{
            fontFamily: 'var(--font-mono)',
            fontSize: '14px',
            color: 'var(--text-secondary)',
            margin: 0
          }}>
            {title} documentation is being prepared
          </p>
          
          {/* Curved speech bubble tail pointing toward character on right */}
          <svg 
            style={{
              position: 'absolute',
              bottom: '-30px',
              right: '20px',
              width: '50px',
              height: '35px',
              overflow: 'visible'
            }}
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
        </div>
      </div>
    </LassSubpageLayout>
  )
}
