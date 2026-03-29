import Uploader from '@/components/Uploader';
import { cookies } from 'next/headers';
import ReactMarkdown from 'react-markdown';

interface Match {
  id: number;
  videoFilename: string;
  totalShots: number;
  durationSeconds: number;
  totalRallies: number;
  avgRallyLengthSeconds: number;
  harderHitter: string | null;
  geminiInsight: string | null;
  heatmapUrl: string | null;
  createdAt: string;
  status: string;
}

async function getMatches(): Promise<Match[]> {
  try {
    const cookieStore = await cookies();
    const sessionCookie = cookieStore.get('COURT_SESSION');
    const headers: HeadersInit = {};
    if (sessionCookie) {
      headers['Cookie'] = `${sessionCookie.name}=${sessionCookie.value}`;
    }

    // Use the environment variable for the backend URL
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';
    const res = await fetch(`${apiUrl}/api/matches`, {
      cache: 'no-store',
      headers: headers,
    });
    
    if (!res.ok) throw new Error('Failed to fetch matches');
    return res.json();
  } catch (error) {
    return [];
  }
}

export default async function Home() {
  const matches = await getMatches();

  return (
    <main className="relative min-h-screen bg-[#062016] text-[#e0e7e1] antialiased overflow-x-hidden">
      
      {/* ── ORGANIC BACKGROUND LAYER ── */}
      <div className="fixed inset-0 z-0 pointer-events-none">
        <div className="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] bg-[#04160f] rounded-full blur-[120px] opacity-80"></div>
        <div className="absolute bottom-[10%] right-[-5%] w-[40%] h-[40%] bg-[#082d1f] rounded-full blur-[100px] opacity-60"></div>
        <div className="absolute top-[40%] right-[20%] w-[30%] h-[30%] bg-[#03110b] rounded-full blur-[120px] opacity-90"></div>
        
        <div className="absolute inset-0 opacity-[0.04] mix-blend-overlay" 
             style={{ backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E")` }}>
        </div>
      </div>

      <div className="relative z-10 max-w-[1200px] mx-auto p-6 md:p-12">
        
        <header className="flex items-center justify-between mb-16">
          <div>
            <h1 className="text-5xl font-extrabold tracking-tighter text-[#f0f5f1]">
              Court<span className="text-[#4ade80]">SenseAI</span>
            </h1>
            <p className="text-[#a3b8ae] font-medium mt-1 tracking-tight text-lg">Tactical Intelligence Dashboard</p>
          </div>
          <div className="hidden md:block px-4 py-2 rounded-full border border-white/10 bg-white/5 backdrop-blur-md text-xs font-bold uppercase tracking-widest text-[#4ade80]">
            System Online
          </div>
        </header>

        <div className="mb-20">
          <Uploader />
        </div>

        <div className="space-y-10">
          <div className="flex items-center gap-4">
             <div className="h-[1px] flex-grow bg-white/10"></div>
             <h2 className="text-xs font-black text-[#a3b8ae] uppercase tracking-[0.3em]">Session History</h2>
             <div className="h-[1px] flex-grow bg-white/10"></div>
          </div>

          {matches.length === 0 ? (
            <div className="text-center py-20 bg-white/5 rounded-[40px] border border-white/10 backdrop-blur-sm">
              <p className="text-[#a3b8ae] text-lg font-medium italic">No performance data captured yet.</p>
            </div>
          ) : (
            <div className="space-y-24">
              {[...matches].sort((a,b) => b.id - a.id).map((match) => (
                <div key={match.id} className="group">
                  
                  <div className="flex justify-between items-end mb-8 px-4">
                    <div>
                      <h3 className="text-4xl font-bold tracking-tighter mb-1">Match #{match.id}</h3>
                      <p className="text-[#a3b8ae] font-medium">{new Date(match.createdAt).toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })}</p>
                    </div>
                    <div className="text-right">
                      <span className={`px-4 py-1.5 rounded-full text-[10px] font-black uppercase tracking-widest border transition-all ${match.status === 'COMPLETED' ? 'bg-[#4ade80] text-[#062016] border-[#4ade80]' : 'bg-transparent text-white/40 border-white/10'}`}>
                        {match.status}
                      </span>
                    </div>
                  </div>

                  {match.status !== 'COMPLETED' ? (
                    <div className="h-64 flex items-center justify-center bg-white/5 rounded-[40px] border border-white/10 italic text-white/30 text-center px-10">
                       Neural engine is currently analyzing spatial data and ball physics...
                    </div>
                  ) : (
                    <div className="space-y-10">
                      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                        {[
                          { label: 'Duration', val: `${match.durationSeconds}s`, color: 'text-white' },
                          { label: 'Total Shots', val: match.totalShots, color: 'text-[#4ade80]' },
                          { label: 'Avg Rally', val: `${match.avgRallyLengthSeconds}s`, color: 'text-white' },
                          { label: 'Hardest Hitter', val: match.harderHitter?.replace('_', ' ') || 'N/A', color: 'text-[#fb923c]' },
                        ].map((s, idx) => (
                          <div key={idx} className="bg-white/5 backdrop-blur-md p-8 rounded-[32px] border border-white/10 hover:bg-white/10 transition-colors">
                            <p className="text-[10px] font-black uppercase tracking-widest text-[#a3b8ae] mb-2">{s.label}</p>
                            <p className={`text-3xl font-bold tracking-tighter ${s.color}`}>{s.val}</p>
                          </div>
                        ))}
                      </div>

                      <div className="space-y-10">
                        {/* Heatmap Section */}
                        <div className="relative bg-black/40 rounded-[48px] overflow-hidden border border-white/10 shadow-2xl transition-transform group-hover:scale-[1.005] duration-500">
                           <div className="absolute top-6 left-8 z-20 flex items-center gap-2 px-3 py-1 bg-[#062016]/80 backdrop-blur-md rounded-full border border-white/10">
                              <div className="w-2 h-2 bg-[#4ade80] rounded-full animate-pulse"></div>
                              <span className="text-[10px] font-black uppercase tracking-wider">Spatial Density Map</span>
                           </div>
                           {match.heatmapUrl ? (
                             <img src={match.heatmapUrl} className="w-full h-auto object-contain min-h-[400px]" alt="Heatmap" />
                           ) : (
                             <div className="h-96 flex items-center justify-center text-white/20 uppercase tracking-[0.3em] text-xs">Visualization unavailable</div>
                           )}
                        </div>

                        {/* Insight Section */}
                        <div className="bg-white/5 backdrop-blur-xl p-10 md:p-14 rounded-[48px] border border-white/10 relative overflow-hidden">
                           <div className="absolute top-[-20%] right-[-10%] w-64 h-64 bg-[#4ade80]/10 rounded-full blur-[80px]"></div>
                           
                           <h4 className="text-xs font-black uppercase tracking-[0.4em] text-[#4ade80] mb-10">Gemini Tactical Insights</h4>
                           
                           <article className="prose prose-invert max-w-none">
                             <ReactMarkdown
                               components={{
                                 // Headings are now pure white
                                 h3: ({...props}) => <h3 className="text-white text-2xl font-bold tracking-tighter mb-4 mt-8 first:mt-0 flex items-center gap-2" {...props} />,
                                 // Text is now normal weight (no italic) and standard sans-serif
                                 p: ({...props}) => <p className="text-[#e0e7e1] text-lg md:text-xl font-medium leading-[1.7] mb-6 opacity-90" {...props} />,
                               }}
                             >
                               {match.geminiInsight || "Analysis unavailable."}
                             </ReactMarkdown>
                           </article>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </main>
  );
}