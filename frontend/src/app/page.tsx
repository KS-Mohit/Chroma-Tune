"use client";

import { useState, useEffect, ChangeEvent } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Music, Upload, Plus, Zap, Play, Loader2, ExternalLink, Library } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";
import { toast } from "sonner"; 

export default function Home() {
  const [playlistId, setPlaylistId] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [isIngesting, setIsIngesting] = useState(false);
  const [isSearching, setIsSearching] = useState(false);
  const [results, setResults] = useState<any>(null);
  const [savedPlaylists, setSavedPlaylists] = useState<any[]>([]);

  // 1. Fetch Saved Playlists on Load
  useEffect(() => {
    fetchPlaylists();
  }, []);

  const fetchPlaylists = async () => {
    try {
        const res = await fetch("http://localhost:8000/playlists");
        if (res.ok) {
            const data = await res.json();
            setSavedPlaylists(data);
        }
    } catch (e) {
        console.error("Failed to load playlists", e);
    }
  };

  const handleIngest = async () => {
    if (!playlistId) return;
    setIsIngesting(true);
    toast.info("Adding Playlist...", { description: "Processing songs and adding to your library." });

    try {
      const res = await fetch("http://localhost:8000/ingest", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ playlist_id: playlistId }),
      });

      if (!res.ok) throw new Error("Failed to sync");

      const data = await res.json();
      setSavedPlaylists(data.playlists); // Update list immediately
      setPlaylistId(""); // Clear input
      toast.success("Playlist Added! 📚", { description: "Your songs are now searchable." });
    } catch (e: any) {
      toast.error("Error", { description: "Could not add playlist." });
    } finally {
      setIsIngesting(false);
    }
  };

  const handleSearch = async () => {
    if (!searchQuery) return;
    setIsSearching(true);
    const formData = new FormData();
    formData.append("text", searchQuery);
    
    try {
        const res = await fetch("http://localhost:8000/search", { method: "POST", body: formData });
        const data = await res.json();
        setResults(data);
    } catch (e) {
        toast.error("Search Error");
    } finally {
        setIsSearching(false);
    }
  };

  return (
    <div className="min-h-screen bg-zinc-950 text-white font-sans selection:bg-green-500 selection:text-black pb-20">
      {/* Background Gradients */}
      <div className="fixed top-0 left-0 w-full h-full overflow-hidden -z-10 pointer-events-none">
        <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-green-600/20 rounded-full blur-[120px]" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-purple-600/10 rounded-full blur-[120px]" />
      </div>

      <main className="max-w-6xl mx-auto px-6 py-12 flex flex-col gap-12">
        {/* Header */}
        <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} className="flex items-center gap-3">
          <div className="p-3 bg-linear-to-br from-green-400 to-green-600 rounded-xl shadow-lg shadow-green-900/20">
            <Music className="w-8 h-8 text-black" />
          </div>
          <h1 className="text-4xl font-bold tracking-tighter bg-clip-text text-transparent bg-linear-to-r from-white to-zinc-500">
            Chroma-Tune
          </h1>
        </motion.div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
            {/* LEFT COLUMN: Controls (4 cols) */}
            <div className="lg:col-span-4 space-y-6">
                
                {/* 1. Add Playlist Card */}
                <Card className="p-6 bg-zinc-900/50 border-zinc-800 backdrop-blur-xl flex flex-col gap-4">
                    <div className="flex items-center gap-2 text-zinc-400 mb-2">
                        <Plus className="w-5 h-5" />
                        <span className="text-sm font-medium">Add to Library</span>
                    </div>
                    <Input 
                        placeholder="Spotify Playlist ID" 
                        className="bg-zinc-950 border-zinc-800 text-white"
                        value={playlistId}
                        onChange={(e: ChangeEvent<HTMLInputElement>) => setPlaylistId(e.target.value)}
                    />
                    <Button onClick={handleIngest} disabled={isIngesting} className="w-full bg-green-500 hover:bg-green-400 text-black font-bold">
                        {isIngesting ? <Loader2 className="animate-spin w-4 h-4" /> : "Add Playlist"}
                    </Button>
                </Card>

                {/* 2. Connected Library List */}
                <Card className="p-6 bg-zinc-900/30 border-zinc-800/50 backdrop-blur-xl flex flex-col gap-4 max-h-[400px] overflow-y-auto custom-scrollbar">
                    <div className="flex items-center gap-2 text-zinc-400 mb-2 sticky top-0">
                        <Library className="w-5 h-5" />
                        <span className="text-sm font-medium">Your Library ({savedPlaylists.length})</span>
                    </div>
                    
                    {savedPlaylists.length === 0 ? (
                        <div className="text-center py-8 text-zinc-600 text-sm">
                            No playlists connected yet.
                        </div>
                    ) : (
                        <div className="space-y-3">
                            {savedPlaylists.map((pl, i) => (
                                <div key={i} className="flex items-center gap-3 p-3 rounded-lg bg-zinc-950/50 border border-zinc-800 hover:border-zinc-700 transition-colors group">
                                    {pl.image ? (
                                        <img src={pl.image} alt={pl.name} className="w-10 h-10 rounded object-cover opacity-80 group-hover:opacity-100" />
                                    ) : (
                                        <div className="w-10 h-10 rounded bg-zinc-800 flex items-center justify-center"><Music className="w-4 h-4 text-zinc-600"/></div>
                                    )}
                                    <div className="flex-1 min-w-0">
                                        <h4 className="text-sm font-medium text-zinc-300 truncate group-hover:text-white">{pl.name}</h4>
                                        <a href={pl.url} target="_blank" className="text-xs text-green-500 hover:underline flex items-center gap-1">
                                            Open Spotify <ExternalLink className="w-3 h-3" />
                                        </a>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </Card>
            </div>

            {/* RIGHT COLUMN: Search & Results (8 cols) */}
            <div className="lg:col-span-8 space-y-6">
                {/* Search Box */}
                <Card className="p-8 bg-zinc-900/50 border-zinc-800 backdrop-blur-xl flex flex-col gap-6 relative overflow-hidden group">
                     <div className="absolute inset-0 bg-linear-to-r from-transparent via-zinc-800/10 to-transparent -translate-x-full group-hover:translate-x-full transition-transform duration-1000 pointer-events-none" />
                     
                     <div>
                        <h2 className="text-2xl font-bold text-white">Vibe Check</h2>
                        <p className="text-zinc-400">Describe the setting (e.g., "Cyberpunk rainy city") or upload a photo.</p>
                     </div>

                     <div className="flex gap-3">
                        <Input 
                            placeholder="Type your vibe here..." 
                            className="bg-zinc-950/80 border-zinc-700 h-14 text-lg text-white"
                            value={searchQuery}
                            onChange={(e: ChangeEvent<HTMLInputElement>) => setSearchQuery(e.target.value)}
                            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                        />
                        <Button size="icon" className="h-14 w-14 bg-white text-black hover:bg-zinc-200 shrink-0" onClick={handleSearch} disabled={isSearching}>
                             {isSearching ? <Loader2 className="animate-spin" /> : <Zap />}
                        </Button>
                     </div>
                     
                     <div className="border-2 border-dashed border-zinc-800 rounded-lg p-6 text-center text-zinc-600 hover:text-zinc-400 hover:border-zinc-600 transition-colors cursor-pointer">
                        <Upload className="w-6 h-6 mx-auto mb-2" />
                        <span className="text-sm">Drag & Drop Image (Coming Soon)</span>
                     </div>
                </Card>

                {/* Results List */}
                <AnimatePresence>
                    {results && results.songs && (
                        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="space-y-4">
                            <div className="flex items-center justify-between">
                                <h3 className="text-xl font-semibold text-white">AI Picks</h3>
                                <span className="text-xs font-mono text-green-500 bg-green-500/10 px-2 py-1 rounded">GEMINI-2.5-FLASH</span>
                            </div>

                            <div className="grid gap-3">
                                {results.songs.map((song: any, i: number) => (
                                    <motion.div 
                                        key={i}
                                        initial={{ opacity: 0, y: 10 }}
                                        animate={{ opacity: 1, y: 0 }}
                                        transition={{ delay: i * 0.05 }}
                                        className="group flex items-center justify-between p-4 rounded-xl bg-zinc-900/40 hover:bg-zinc-800 border border-transparent hover:border-zinc-700 transition-all cursor-pointer"
                                        onClick={() => window.open(song.url, '_blank')}
                                    >
                                        <div className="flex items-center gap-4">
                                            <div className="w-12 h-12 rounded bg-zinc-800 flex items-center justify-center text-zinc-500 group-hover:text-green-500 transition-colors">
                                                <Play className="w-5 h-5 fill-current" />
                                            </div>
                                            <div>
                                                <div className="font-medium text-white text-lg group-hover:text-green-400 transition-colors">{song.name}</div>
                                                <div className="text-zinc-500">{song.artist}</div>
                                            </div>
                                        </div>
                                        <div className="text-zinc-600 font-mono text-sm">{Math.round(100 - (song.score * 10))}% Match</div>
                                    </motion.div>
                                ))}
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>
        </div>
      </main>
    </div>
  );
}