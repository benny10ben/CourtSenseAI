// 1. Define the "Shape" of our Data (TypeScript Interface)
interface Match {
  id: number;
  videoFilename: string;
  totalShots: number;
  durationSeconds: number;
  totalRallies: number;
  avgRallyLengthSeconds: number;
  harderHitter: string;
  geminiInsight: string;
  createdAt: string;
}

// 2. Fetch the data from Spring Boot
async function getMatches(): Promise<Match[]> {
  try {
    // cache: 'no-store' ensures we always get fresh data from the DB
    const res = await fetch('http://localhost:8080/api/matches', { cache: 'no-store' });
    if (!res.ok) throw new Error('Failed to fetch matches');
    return res.json();
  } catch (error) {
    console.error("Backend might be down:", error);
    return [];
  }
}

// 3. The main UI Component (Notice it is an 'async' function!)
export default async function Home() {
  const matches = await getMatches();

  return (
    <main className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-5xl mx-auto">
        <h1 className="text-4xl font-bold text-gray-900 mb-2">
          CourtSenseAI Dashboard
        </h1>
        <p className="text-gray-500 mb-8">
          Match history and tactical analysis.
        </p>

        {/* 4. Display Logic: Empty State vs Populated State */}
        {matches.length === 0 ? (
          <div className="bg-white p-6 rounded-lg shadow border border-gray-200 text-gray-700">
            No matches found. Run your python pipeline and trigger the API!
          </div>
        ) : (
          <div className="space-y-6">
            {matches.map((match) => (
              <div key={match.id} className="bg-white p-6 rounded-lg shadow border border-gray-200">
                
                {/* Header Row */}
                <div className="flex justify-between items-start mb-4">
                  <div>
                    <h2 className="text-xl font-semibold text-gray-800">Video #{match.id}</h2>
                    <p className="text-sm text-gray-500">{new Date(match.createdAt).toLocaleDateString()}</p>
                  </div>
                  <span className="bg-blue-100 text-blue-800 text-xs font-medium px-2.5 py-0.5 rounded">
                    {match.totalShots} Shots
                  </span>
                </div>
                
                {/* Stats Grid */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                  <div className="bg-gray-50 p-3 rounded border border-gray-100">
                    <p className="text-xs text-gray-500 uppercase font-bold tracking-wider mb-1">Duration</p>
                    <p className="text-lg text-gray-900 font-semibold">{match.durationSeconds}s</p>
                  </div>
                  <div className="bg-gray-50 p-3 rounded border border-gray-100">
                    <p className="text-xs text-gray-500 uppercase font-bold tracking-wider mb-1">Harder Hitter</p>
                    <p className="text-lg text-gray-900 font-semibold uppercase">{match.harderHitter.replace('_', ' ')}</p>
                  </div>
                   <div className="bg-gray-50 p-3 rounded border border-gray-100">
                    <p className="text-xs text-gray-500 uppercase font-bold tracking-wider mb-1">Avg Rally</p>
                    <p className="text-lg text-gray-900 font-semibold">{match.avgRallyLengthSeconds}s</p>
                  </div>
                  <div className="bg-gray-50 p-3 rounded border border-gray-100">
                    <p className="text-xs text-gray-500 uppercase font-bold tracking-wider mb-1">Video File</p>
                    <p className="text-sm text-gray-900 font-semibold truncate" title={match.videoFilename}>
                      {match.videoFilename}
                    </p>
                  </div>
                </div>

                {/* AI Insight Section */}
                <div className="border-t border-gray-100 pt-4">
                  <div className="flex items-center gap-2 mb-3">
                    <span className="text-lg">🤖</span>
                    <h3 className="text-sm font-bold text-gray-900 uppercase tracking-wider">Coach Gemini Says:</h3>
                  </div>
                  {/* whitespace-pre-line ensures the paragraph breaks show up */}
                  <p className="text-gray-700 whitespace-pre-line text-sm bg-blue-50/50 p-4 rounded-lg border border-blue-100 leading-relaxed">
                    {match.geminiInsight}
                  </p>
                </div>

              </div>
            ))}
          </div>
        )}
      </div>
    </main>
  );
}