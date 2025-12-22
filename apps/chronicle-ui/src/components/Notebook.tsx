interface NotebookProps {
  title?: string;
  content: string;
  date?: string;
  className?: string;
}

export function Notebook({ title, content, date, className = "" }: NotebookProps) {
  return (
    <div className={`relative bg-white shadow-brutal overflow-hidden rounded-sm w-full ${className}`}>
      {/* Red margin line */}
      <div className="absolute top-0 bottom-0 left-10 md:left-14 w-px bg-red-400 z-10 opacity-60" />
      
      {/* Paper Content */}
      <div className="notebook-paper min-h-[400px] w-full pt-10 pb-10 px-14 md:px-20 relative">
        <div className="notebook-font text-xl md:text-2xl text-zinc-800 leading-[30px]">
          {date && (
             <div className="text-right text-zinc-500 text-lg mb-2">{date}</div>
          )}
          {title && (
            <h2 className="font-bold text-3xl mb-6 text-zinc-900">{title}</h2>
          )}
          <div className="whitespace-pre-wrap">
            {content}
          </div>
        </div>
      </div>
      
      {/* Binder Holes */}
      <div className="absolute top-0 bottom-0 left-2 md:left-4 flex flex-col justify-center gap-32 py-10">
         {[1,2,3].map(i => (
           <div key={i} className="w-5 h-5 bg-[#FDFBF7] rounded-full shadow-[inset_1px_1px_3px_rgba(0,0,0,0.2)]" />
         ))}
      </div>
    </div>
  )
}
