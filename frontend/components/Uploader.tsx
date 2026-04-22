'use client';

import { useState, useRef, useEffect } from 'react';

// Backend Harmony - Keep these definitions
type Point = { x: number; y: number };
type Box = [number, number, number, number];
type ZoneKey = 'front_left' | 'front_right' | 'back_left' | 'back_right';

const ZONE_LABELS: { key: ZoneKey; label: string }[] = [
  { key: 'front_left', label: 'Front-Left' },
  { key: 'front_right', label: 'Front-Right' },
  { key: 'back_left', label: 'Back-Left' },
  { key: 'back_right', label: 'Back-Right' },
];

export default function Uploader() {
  const [file, setFile] = useState<File | null>(null);
  const [step, setStep] = useState<'SELECT' | 'CALIBRATE_COURT' | 'CALIBRATE_ZONES' | 'PROCESSING'>('SELECT');
  const [jobId, setJobId] = useState<string | null>(null);
  const [statusMsg, setStatusMsg] = useState('');
  const [corners, setCorners] = useState<Point[]>([]);
  const [p1Zones, setP1Zones] = useState<Partial<Record<ZoneKey, Box>>>({});
  const [p2Zones, setP2Zones] = useState<Partial<Record<ZoneKey, Box>>>({});
  const [activePlayer, setActivePlayer] = useState<'P1' | 'P2'>('P1');
  const [activeZone, setActiveZone] = useState<ZoneKey>('front_left');

  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const isDragging = useRef(false);
  const dragStart = useRef<Point | null>(null);

  // Helper to get environment variables safely
  const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';
  const INTERNAL_SECRET = process.env.NEXT_PUBLIC_INTERNAL_SECRET || '';

  // ── Canvas Redraw Logic ──
  const redrawCanvas = (currentDragBox?: { x: number; y: number; w: number; h: number; color: string }) => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    // Draw Court Corners (Aesthetic Green)
    corners.forEach((pt, i) => {
      ctx.beginPath();
      ctx.arc(pt.x, pt.y, 8, 0, 2 * Math.PI);
      ctx.fillStyle = '#4ade80';
      ctx.fill();
      ctx.lineWidth = 3;
      ctx.strokeStyle = '#FFFFFF';
      ctx.stroke();

      if (i > 0) {
        ctx.beginPath();
        ctx.moveTo(corners[i - 1].x, corners[i - 1].y);
        ctx.lineTo(pt.x, pt.y);
        ctx.strokeStyle = '#4ade80';
        ctx.lineWidth = 4;
        ctx.stroke();
      }
    });

    if (corners.length === 4) {
      ctx.beginPath();
      ctx.moveTo(corners[3].x, corners[3].y);
      ctx.lineTo(corners[0].x, corners[0].y);
      ctx.strokeStyle = '#4ade80';
      ctx.lineWidth = 4;
      ctx.stroke();
    }

    const drawZones = (zones: Partial<Record<ZoneKey, Box>>, color: string, prefix: string) => {
      Object.entries(zones).forEach(([key, box]) => {
        if (!box) return;
        const [x1, y1, x2, y2] = box;
        ctx.strokeStyle = color;
        ctx.lineWidth = 3;
        ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);
        ctx.fillStyle = color;
        ctx.font = 'bold 24px inherit';
        ctx.fillText(`${prefix}-${key.replace('_', ' ').toUpperCase()}`, x1 + 10, y1 + 32);
      });
    };

    drawZones(p1Zones, '#FF6B6B', 'P1');
    drawZones(p2Zones, '#4DABF7', 'P2');

    if (currentDragBox) {
      ctx.strokeStyle = currentDragBox.color;
      ctx.lineWidth = 3;
      ctx.setLineDash([5, 5]);
      ctx.strokeRect(currentDragBox.x, currentDragBox.y, currentDragBox.w, currentDragBox.h);
      ctx.setLineDash([]);
    }
  };

  // ── Polling Engine ──
  useEffect(() => {
    let intervalId: NodeJS.Timeout;
    if (step === 'PROCESSING' && jobId) {
      intervalId = setInterval(async () => {
        try {
          const res = await fetch(`${API_BASE_URL}/api/matches/status/${jobId}`, { credentials: 'include' });
          if (!res.ok) return;
          const data = await res.json();
          if (data.status === 'COMPLETED') {
            setStatusMsg('Match analyzed! Syncing dashboard...');
            clearInterval(intervalId);
            setTimeout(() => window.location.reload(), 1500);
          } else if (data.status === 'FAILED') {
            setStatusMsg('❌ Pipeline failure. Resetting...');
            clearInterval(intervalId);
            setStep('CALIBRATE_ZONES');
          } else {
            setStatusMsg('AI is extracting pose metrics and ball physics...');
          }
        } catch (err) { console.error('Polling error', err); }
      }, 3000);
    }
    return () => { if (intervalId) clearInterval(intervalId); };
  }, [step, jobId, API_BASE_URL]);

  // ── Interaction Logic ──
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setStep('CALIBRATE_COURT');
      setCorners([]); setP1Zones({}); setP2Zones({}); setJobId(null);
    }
  };

  useEffect(() => {
    if ((step === 'CALIBRATE_COURT' || step === 'CALIBRATE_ZONES') && file && videoRef.current && canvasRef.current) {
      const video = videoRef.current;
      const objectUrl = URL.createObjectURL(file);
      video.src = objectUrl;

      // Force-seek to wake up the buffer
      video.onloadedmetadata = () => { video.currentTime = 1; };
      video.onseeked = () => {
        if (canvasRef.current) {
          canvasRef.current.width = video.videoWidth;
          canvasRef.current.height = video.videoHeight;
          redrawCanvas();
        }
      };
      return () => URL.revokeObjectURL(objectUrl);
    }
  }, [step, file]);

  const getMousePos = (e: React.MouseEvent<HTMLCanvasElement>): Point | null => {
    const canvas = canvasRef.current; if (!canvas) return null;
    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;
    return { x: Math.round((e.clientX - rect.left) * scaleX), y: Math.round((e.clientY - rect.top) * scaleY) };
  };

  const handleMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const pos = getMousePos(e); if (!pos) return;
    if (step === 'CALIBRATE_COURT' && corners.length < 4) {
      setCorners([...corners, pos]);
      setTimeout(() => redrawCanvas(), 0);
    }
    else if (step === 'CALIBRATE_ZONES') { isDragging.current = true; dragStart.current = pos; }
  };

  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (step === 'CALIBRATE_ZONES' && isDragging.current && dragStart.current) {
      const pos = getMousePos(e); if (!pos) return;
      const x = Math.min(dragStart.current.x, pos.x); const y = Math.min(dragStart.current.y, pos.y);
      const w = Math.abs(pos.x - dragStart.current.x); const h = Math.abs(pos.y - dragStart.current.y);
      const color = activePlayer === 'P1' ? '#FF6B6B' : '#4DABF7';
      redrawCanvas({ x, y, w, h, color });
    }
  };

  const handleMouseUp = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (step === 'CALIBRATE_ZONES' && isDragging.current && dragStart.current) {
      const pos = getMousePos(e);
      if (pos) {
        const x1 = Math.min(dragStart.current.x, pos.x); const y1 = Math.min(dragStart.current.y, pos.y);
        const x2 = Math.max(dragStart.current.x, pos.x); const y2 = Math.max(dragStart.current.y, pos.y);
        if (x2 - x1 > 20 && y2 - y1 > 20) {
          const newBox: Box = [x1, y1, x2, y2];
          if (activePlayer === 'P1') setP1Zones(prev => ({ ...prev, [activeZone]: newBox }));
          if (activePlayer === 'P2') setP2Zones(prev => ({ ...prev, [activeZone]: newBox }));
        }
      }
      isDragging.current = false; dragStart.current = null; setTimeout(() => redrawCanvas(), 0);
    }
  };

  const handleSubmit = async () => {
    if (!file || corners.length !== 4) return;
    setStep('PROCESSING');
    setStatusMsg('Uploading and initializing neural pipeline...');
    const payload = { court_corners: corners, p1_zones: p1Zones, p2_zones: p2Zones };
    const formData = new FormData();
    formData.append('video', file);
    formData.append('coords', JSON.stringify(payload));
    try {
      const res = await fetch(`${API_BASE_URL}/api/matches/upload`, {
        method: 'POST',
        headers: { 'X-Internal-Secret': INTERNAL_SECRET },
        credentials: 'include',
        body: formData,
      });
      if (!res.ok) { const errorText = await res.text(); throw new Error(errorText); }
      const data = await res.json();
      setJobId(data.jobId);
    } catch (error) {
      setStatusMsg(`❌ Error: ${error instanceof Error ? error.message : 'Upload failed'}.`);
      setStep('CALIBRATE_ZONES');
    }
  };

  const allP1Done = Object.keys(p1Zones).length === 4;
  const allP2Done = Object.keys(p2Zones).length === 4;
  const readyToSubmit = corners.length === 4 && allP1Done && allP2Done;

  return (
    <div className="max-w-4xl mx-auto bg-white/5 backdrop-blur-xl p-6 md:p-8 rounded-[40px] border border-white/10 shadow-2xl transition-all overflow-hidden">
      
      {step === 'SELECT' && (
        <div className="text-center py-12 flex flex-col items-center">
          <div className="w-16 h-16 bg-[#4ade80] rounded-full flex items-center justify-center mb-6 shadow-lg">
             <span className="text-2xl text-[#062016]">↑</span>
          </div>
          <h2 className="text-3xl font-extrabold tracking-tighter mb-2 text-white">Begin Analysis</h2>
          <p className="text-[#a3b8ae] mb-8 max-w-xs text-sm font-medium">Upload recording to generate spatial intelligence.</p>
          
          <label className="relative group cursor-pointer">
            <input type="file" accept="video/mp4" onChange={handleFileChange} className="hidden" id="match-upload" />
            <div className="px-10 py-4 bg-[#4ade80] text-[#062016] rounded-full font-black uppercase tracking-widest text-[11px] transition-all hover:scale-105 active:scale-95">
               Select Video
            </div>
          </label>
        </div>
      )}

      {(step === 'CALIBRATE_COURT' || step === 'CALIBRATE_ZONES') && (
        <div className="space-y-6">
          <header className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
            <div>
              <span className="text-[9px] font-black uppercase tracking-[0.3em] text-[#4ade80]">Configuration</span>
              <h2 className="text-xl font-bold tracking-tighter text-white">
                {step === 'CALIBRATE_COURT' ? `Calibrate Court (${corners.length}/4)` : 'Map Tactical Zones'}
              </h2>
            </div>

            <div className="flex gap-3">
              {step === 'CALIBRATE_COURT' && corners.length === 4 && (
                <button onClick={() => setStep('CALIBRATE_ZONES')} className="px-5 py-2 bg-white text-black rounded-full font-black uppercase tracking-widest text-[9px] transition-all hover:bg-[#4ade80]">
                  Next Stage
                </button>
              )}
              {step === 'CALIBRATE_ZONES' && (
                <button onClick={handleSubmit} disabled={!readyToSubmit} 
                        className={`px-6 py-2 rounded-full font-black uppercase tracking-widest text-[9px] transition-all
                        ${readyToSubmit ? 'bg-[#fb923c] text-black shadow-lg hover:scale-105 active:scale-95' : 'bg-white/10 text-white/20 cursor-not-allowed border border-white/5'}`}>
                  Run Pipeline
                </button>
              )}
            </div>
          </header>

          <div className="relative rounded-2xl overflow-hidden border border-white/10 bg-black shadow-inner max-h-[500px]">
            <canvas 
              ref={canvasRef} 
              onMouseDown={handleMouseDown} onMouseMove={handleMouseMove} onMouseUp={handleMouseUp} onMouseLeave={handleMouseUp} 
              className="w-full h-auto cursor-crosshair opacity-90 hover:opacity-100"
            />
          </div>

          {step === 'CALIBRATE_ZONES' && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
              <div className="flex gap-2">
                <button onClick={() => setActivePlayer('P1')} className={`flex-1 py-2 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all ${activePlayer === 'P1' ? 'bg-[#FF6B6B] text-black' : 'bg-white/5 text-gray-400'}`}>
                  P1 (Far) {allP1Done && '✓'}
                </button>
                <button onClick={() => setActivePlayer('P2')} className={`flex-1 py-2 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all ${activePlayer === 'P2' ? 'bg-[#4DABF7] text-black' : 'bg-white/5 text-gray-400'}`}>
                  P2 (Near) {allP2Done && '✓'}
                </button>
              </div>
              <div className="grid grid-cols-4 gap-1.5">
                {ZONE_LABELS.map(({ key }) => (
                  <button 
                    key={key} onClick={() => setActiveZone(key)} 
                    className={`py-2 rounded-lg text-[8px] font-black uppercase tracking-tighter border transition-all
                      ${activeZone === key ? 'bg-[#4ade80] text-black border-transparent' : 'bg-white/5 text-gray-500 border-white/5'}`}
                  >
                    {key.split('_').map(w => w[0].toUpperCase()).join('')}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {step === 'PROCESSING' && (
        <div className="text-center py-16 flex flex-col items-center">
          <div className="relative w-12 h-12 mb-6">
             <div className="absolute inset-0 border-2 border-[#4ade80]/20 rounded-full"></div>
             <div className="absolute inset-0 border-2 border-[#4ade80] rounded-full border-t-transparent animate-spin"></div>
          </div>
          <h2 className="text-2xl font-extrabold tracking-tighter mb-2">Neural Processing</h2>
          <p className="text-[#a3b8ae] max-w-xs text-sm italic font-medium opacity-80">&quot;{statusMsg}&quot;</p>
        </div>
      )}
      
      <video ref={videoRef} className="hidden" muted playsInline />
    </div>
  );
}