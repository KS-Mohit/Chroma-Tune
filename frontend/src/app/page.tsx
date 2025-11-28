"use client";

import { useState, ChangeEvent } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Music, Upload, Disc, Zap, Play, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";
import { toast } from "sonner"; // For notifications

export default function Home() {
  const [playlistId, setPlaylistId] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [isIngesting, setIsIngesting] = useState(false);
  const [isSearching, setIsSearching] = useState(false);
  const [results, setResults] = useState<any>(null);

  // --- 1. Ingest Logic (Connects to /ingest) ---
  const handleIngest = async () => {
    if (!playlistId) {
      toast.error("Missing ID", { description: "Please enter a Spotify Playlist ID." });
      return;
    }

    setIsIngesting(true);
    toast.info("Syncing Playlist...", { description: "This might take a moment to analyze songs." });

    try {
      const res = await fetch("http://localhost:8000/ingest", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ playlist_id: playlistId }),
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || "Failed to sync");
      }

      const data = await res.json();
      console.log(data);
      toast.success("Sync Complete! 🎧", { description: "Your songs are now in the AI vector store." });
    } catch (e: any) {
      console.error(e);
      toast.error("Sync Failed", { description: e.message || "Check your Playlist ID or console." });
    } finally {
      setIsIngesting(false);
    }
  };

  // --- 2. Search Logic (Connects to /search) ---
  const handleSearch = async () => {
    if (!searchQuery) {
      toast.warning("Empty Vibe", { description: "Describe a setting or upload a photo first." });
      return;
    }

    setIsSearching(true);
    // Use FormData to support both text and potential future file uploads
    const formData = new FormData();
    formData.append("text", searchQuery);
    
    try {
        const res = await fetch("http://localhost:8000/search", {
            method: "POST",
            body: formData
        });
        
        if (!res.ok) throw new Error("Search failed");
        
        const data = await res.json();
        setResults(data);
        toast.success("Vibe Matched ✨", { description: `Found ${data.songs.length} songs for you.` });
    } catch (e) {
        console.error(e);
        toast.error("Search Error", { description: "Could not find matches." });
    } finally {
        setIsSearching(false);
    }
  };

  return (
    <div className="min-h-screen bg-zinc-950 text-white selection:bg-green-500 selection:text-black font-sans overflow-hidden">
      {/* Background Gradients */}
      <div className="fixed top-0 left-0 w-full h-full overflow-hidden -z-10 pointer-events-none">
        <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-green-600/20 rounded-full blur-[120px]" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-purple-600/10 rounded-full blur-[120px]" />
      </div>

      <main className="max-w-4xl mx-auto px-6 py-12 flex flex-col gap-12">
        {/* Header */}
        <motion.div 
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center gap-3"
        >
          <div className="p-3 bg-gradient-to-br from-green-400 to-green-600 rounded-xl shadow-lg shadow-green-900/20">
            <Music className="w-8 h-8 text-black" />
          </div>
          <h1 className="text-4xl font-bold tracking-tighter bg-clip-text text-transparent bg-gradient-to-r from-white to-zinc-500">
            Chroma-Tune
          </h1>
        </motion.div>

        {/* Ingest Section */}
        <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="grid grid-cols-1 md:grid-cols-3 gap-6"
        >
            <Card className="col-span-3 md:col-span-1 p-6 bg-zinc-900/50 border-zinc-800 backdrop-blur-xl flex flex-col gap-4">
                <div className="flex items-center gap-2 text-zinc-400">
                    <Disc className="w-5 h-5" />
                    <span className="text-sm font-medium">Connect Source</span>
                </div>
                <Input 
                    placeholder="Spotify Playlist ID" 
                    // FIX: Added text-white so input is visible
                    className="bg-zinc-950 border-zinc-800 focus-visible:ring-green-500 text-white placeholder:text-zinc-600"
                    value={playlistId}
                    onChange={(e: ChangeEvent<HTMLInputElement>) => setPlaylistId(e.target.value)}
                />
                <Button 
                    onClick={handleIngest}
                    disabled={isIngesting}
                    className="w-full bg-green-500 hover:bg-green-400 text-black font-bold transition-all"
                >
                    {isIngesting ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Syncing...
                      </>
                    ) : (
                      "Sync Playlist"
                    )}
                </Button>
            </Card>

            {/* Vibe Check Section */}
            <Card className="col-span-3 md:col-span-2 p-6 bg-zinc-900/50 border-zinc-800 backdrop-blur-xl flex flex-col gap-4 min-h-[300px] justify-center relative overflow-hidden group">
                 {/* Decorative Swoosh */}
                 <div className="absolute inset-0 bg-gradient-to-r from-transparent via-zinc-800/10 to-transparent -translate-x-full group-hover:translate-x-full transition-transform duration-1000" />
                 
                 <div className="flex flex-col gap-2 z-10">
                    <h2 className="text-2xl font-bold text-white">How's the vibe?</h2>
                    <p className="text-zinc-400">Upload a photo or describe the setting.</p>
                 </div>

                 <div className="flex gap-2 z-10">
                    <Input 
                        placeholder="e.g. 'Late night drive in Tokyo'" 
                        // FIX: Added text-white so input is visible
                        className="bg-zinc-950/80 border-zinc-700 h-12 text-lg text-white placeholder:text-zinc-600"
                        value={searchQuery}
                        onChange={(e: ChangeEvent<HTMLInputElement>) => setSearchQuery(e.target.value)}
                        onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                    />
                    <Button 
                        size="icon" 
                        className="h-12 w-12 bg-white text-black hover:bg-zinc-200 shrink-0"
                        onClick={handleSearch}
                        disabled={isSearching}
                    >
                         {isSearching ? <Loader2 className="h-5 w-5 animate-spin" /> : <Zap className="w-5 h-5" />}
                    </Button>
                 </div>
                 
                 <div className="mt-4 border-2 border-dashed border-zinc-800 rounded-lg p-8 text-center text-zinc-600 hover:text-zinc-400 hover:border-zinc-600 transition-colors cursor-pointer">
                    <Upload className="w-6 h-6 mx-auto mb-2" />
                    <span className="text-sm">Drop an image here for AI Vision analysis</span>
                 </div>
            </Card>
        </motion.div>

        {/* Results Section */}
        <AnimatePresence>
            {results && results.songs && (
                <motion.div
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0 }}
                    className="space-y-4 pb-20"
                >
                    <div className="flex items-center justify-between">
                        <h3 className="text-xl font-semibold text-white">AI Recommendations</h3>
                        <span className="text-xs font-mono text-green-500 border border-green-500/20 px-2 py-1 rounded bg-green-500/10">
                            GEMINI-2.5-FLASH
                        </span>
                    </div>

                    <div className="grid gap-3">
                        {results.songs.map((song: any, i: number) => (
                            <motion.div 
                                key={i}
                                initial={{ opacity: 0, x: -20 }}
                                animate={{ opacity: 1, x: 0 }}
                                transition={{ delay: i * 0.1 }}
                                className="group flex items-center justify-between p-4 rounded-xl bg-zinc-900/40 hover:bg-zinc-800 border border-transparent hover:border-zinc-700 transition-all cursor-pointer"
                                onClick={() => window.open(song.url, '_blank')}
                            >
                                <div className="flex items-center gap-4">
                                    <div className="w-10 h-10 rounded bg-zinc-800 flex items-center justify-center text-zinc-500 group-hover:text-green-500 transition-colors">
                                        <Play className="w-4 h-4 fill-current" />
                                    </div>
                                    <div>
                                        <div className="font-medium text-white group-hover:text-green-400 transition-colors">
                                            {song.name}
                                        </div>
                                        <div className="text-sm text-zinc-500">
                                            {song.artist}
                                        </div>
                                    </div>
                                </div>
                                <div className="text-zinc-600 text-sm font-mono">
                                    Match: {Math.round(100 - (song.score * 10))}% 
                                </div>
                            </motion.div>
                        ))}
                    </div>
                </motion.div>
            )}
        </AnimatePresence>
      </main>
    </div>
  );
}