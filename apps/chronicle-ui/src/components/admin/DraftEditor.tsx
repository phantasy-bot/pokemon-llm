import { useState } from 'react';
import { Drop } from '../../lib/api';

interface DraftEditorProps {
  drop: Drop;
  onSave: (id: string, formData: FormData) => Promise<void>;
  onCancel: () => void;
}

export function DraftEditor({ drop, onSave, onCancel }: DraftEditorProps) {
  const [form, setForm] = useState({
    name: drop.name,
    description: drop.description,
    file: null as File | null,
    galleryFiles: [] as File[]
  });

  const handleSubmit = async () => {
    const formData = new FormData();
    formData.append('name', form.name);
    formData.append('description', form.description);
    if (form.file) {
      formData.append('image', form.file);
    }
    
    if (form.galleryFiles.length > 0) {
        for (let i = 0; i < form.galleryFiles.length; i++) {
            formData.append('gallery', form.galleryFiles[i]);
        }
    }

    await onSave(drop.id, formData);
  };

  return (
    <div className="space-y-4">
      <div>
          <label className="block text-xs font-bold mb-1">TITLE</label>
          <input 
            className="w-full border border-black p-2 font-bold" 
            value={form.name} 
            onChange={e => setForm({...form, name: e.target.value})}
          />
      </div>
      <div>
          <label className="block text-xs font-bold mb-1">DESCRIPTION</label>
          <textarea 
            className="w-full border border-black p-2 h-24 text-sm" 
            value={form.description}
            onChange={e => setForm({...form, description: e.target.value})}
          />
      </div>
      <div className="p-4 bg-zinc-50 border border-zinc-100 rounded">
          <label className="block text-xs font-bold mb-2">REPLACE MAIN IMAGE</label>
          <input 
            type="file" 
            className="text-sm w-full"
            onChange={e => setForm({...form, file: e.target.files?.[0] || null})}
          />
      </div>
      
      <div className="p-4 bg-zinc-50 border border-zinc-100 rounded">
          <label className="block text-xs font-bold mb-2">ADD GALLERY IMAGES (Optional)</label>
          <input 
            type="file" 
            multiple
            className="text-sm w-full"
            onChange={e => setForm({...form, galleryFiles: Array.from(e.target.files || [])})}
          />
          <p className="text-[10px] text-zinc-500 mt-1">Select multiple files to add to gallery.</p>
      </div>

      <div className="flex gap-2 pt-2">
        <button onClick={handleSubmit} className="bg-black text-white px-4 py-2 text-sm font-bold hover:bg-zinc-800">SAVE</button>
        <button onClick={onCancel} className="border border-black px-4 py-2 text-sm font-bold hover:bg-zinc-50">CANCEL</button>
      </div>
    </div>
  );
}
