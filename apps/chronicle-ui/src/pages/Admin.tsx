import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Loader2, Twitter, RefreshCw } from 'lucide-react';
import { useAdmin } from '../hooks/useAdmin';
import { DraftEditor } from '../components/admin/DraftEditor';

export function Admin() {
  const { drafts, loading, isAuthorized, address, publishing, tweeting, handlePublish, handleTweet, handleUpdate, refreshDrafts } = useAdmin();
  const [editingId, setEditingId] = useState<string | null>(null);
  const [searchParams, setSearchParams] = useSearchParams();

  // Handle deep link to edit
  useEffect(() => {
    const editId = searchParams.get('edit');
    if (editId && !loading && drafts.length > 0) {
        const drop = drafts.find(d => d.id === editId);
        if (drop) {
            setEditingId(editId);
        }
    }
  }, [searchParams, loading, drafts]);

  const getImageUrl = (url: string) => {
    if (url.startsWith('http') || url.startsWith('ipfs')) return url;
    const apiBase = import.meta.env.VITE_CHRONICLE_API_URL || 'http://localhost:3001';
    return `${apiBase}${url}`;
  };

  if (!isAuthorized) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[50vh] font-mono gap-4">
        <div className="bg-red-50 text-red-600 p-4 border border-red-200 rounded">
          ACCESS DENIED. WALLET NOT AUTHORIZED.
        </div>
        <p className="text-sm text-gray-400">Connected: {address}</p>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto p-8 font-mono pb-32">
      <div className="flex justify-between items-center mb-8">
          <h1 className="text-3xl font-bold">ADMIN PANEL // DRAFTS</h1>
          <button 
            onClick={refreshDrafts} 
            className="flex items-center gap-2 bg-zinc-100 hover:bg-zinc-200 px-4 py-2 rounded text-sm font-bold"
          >
            <RefreshCw size={14} /> Refresh (Sign Required)
          </button>
      </div>
      
      {loading ? (
        <div className="flex justify-center"><Loader2 className="animate-spin" /></div>
      ) : (
        <div className="space-y-8">
          {drafts.length === 0 && <p className="text-gray-500">No pending drafts.</p>}
          
          {drafts.map(drop => (
            <div key={drop.id} className="border border-zinc-200 p-6 rounded-lg bg-white shadow-sm flex flex-col gap-6">
              
              <div className="flex flex-col md:flex-row gap-6">
                  {/* Image Preview Grid */}
                  <div className="w-full md:w-64 flex-shrink-0 flex flex-col gap-2">
                     <div className="h-48 bg-zinc-100 relative border border-zinc-100">
                        <img src={getImageUrl(drop.publicImageUrl)} className="w-full h-full object-contain" />
                     </div>
                     {/* Gallery Previews */}
                     {drop.images && drop.images.length > 1 && (
                         <div className="flex gap-2 overflow-x-auto pb-2">
                             {drop.images.slice(1).map((img, idx) => (
                                 <div key={idx} className="h-16 w-16 flex-shrink-0 border border-zinc-200 bg-zinc-50">
                                     <img src={getImageUrl(img)} className="w-full h-full object-cover" />
                                 </div>
                             ))}
                         </div>
                     )}
                  </div>
                  
                  <div className="flex-1 space-y-4">
                    {editingId === drop.id ? (
                      <DraftEditor 
                        drop={drop} 
                        onSave={async (id, data) => {
                            await handleUpdate(id, data);
                            setEditingId(null);
                            setSearchParams(params => {
                                params.delete('edit');
                                return params;
                            });
                        }}
                        onCancel={() => {
                            setEditingId(null);
                            setSearchParams(params => {
                                params.delete('edit');
                                return params;
                            });
                        }}
                      />
                    ) : (
                      <>
                        <div className="flex justify-between items-start">
                            <div>
                                <h2 className="text-xl font-bold uppercase">{drop.name}</h2>
                                <div className="flex gap-2 mt-1">
                                    <span className="text-xs bg-yellow-100 text-yellow-800 px-2 py-0.5 rounded font-bold">
                                        {drop.status === 'published' ? 'PUBLISHED' : 'DRAFT'}
                                    </span>
                                    {drop.images && drop.images.length > 1 && (
                                        <span className="text-xs bg-blue-50 text-blue-600 px-2 py-0.5 rounded font-bold">
                                            {drop.images.length} IMAGES
                                        </span>
                                    )}
                                </div>
                            </div>
                        </div>
                        <p className="text-sm text-gray-600 whitespace-pre-wrap">{drop.description}</p>
                        <div className="flex flex-wrap gap-2 pt-4">
                           <button onClick={() => setEditingId(drop.id)} className="border border-black px-4 py-2 text-sm font-bold hover:bg-zinc-50">EDIT</button>
                           
                           {drop.status !== 'published' && (
                               <button 
                                 onClick={() => {
                                     if(confirm('Publish to Zora?')) handlePublish(drop.id);
                                 }} 
                                 disabled={publishing === drop.id}
                                 className="bg-green-600 text-white px-4 py-2 text-sm font-bold hover:bg-green-700 disabled:opacity-50 flex items-center gap-2"
                               >
                                 {publishing === drop.id && <Loader2 size={14} className="animate-spin" />}
                                 {publishing === drop.id ? 'PUBLISHING...' : 'PUBLISH TO ZORA'}
                               </button>
                           )}

                           <button 
                             onClick={() => {
                                 if(confirm('Post to X?')) handleTweet(drop.id);
                             }}
                             disabled={tweeting === drop.id} 
                             className="bg-black text-white px-4 py-2 text-sm font-bold hover:bg-zinc-800 disabled:opacity-50 flex items-center gap-2 ml-auto"
                           >
                             {tweeting === drop.id ? <Loader2 size={14} className="animate-spin" /> : <Twitter size={14} />}
                             {tweeting === drop.id ? 'POSTING...' : 'REPOST TO X'}
                           </button>
                        </div>
                      </>
                    )}
                  </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
