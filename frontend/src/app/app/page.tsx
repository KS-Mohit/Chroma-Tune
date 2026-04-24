"use client";

import { useState, useEffect, ChangeEvent, useRef, DragEvent } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Music, Upload, Zap, Play, Loader2, ExternalLink, ArrowLeft, PlusCircle, Key, X, AlertTriangle, ImageIcon, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";
import { toast } from "sonner";
import Link from "next/link";

// The collaborative playlist
const PLAYLIST = {
  id: "5DYHhVIXo6PhfXqjIlu6rt",
  name: "Vibes",
  url: "https://open.spotify.com/playlist/5DYHhVIXo6PhfXqjIlu6rt",
  image: "https://mosaic.scdn.co/640/ab67616d00001e021c42b93f217c02977ae4c5d0ab67616d00001e029396544375bc5e09c33c89daab67616d00001e02d3c12724ab66f21170225d22ab67616d00001e02f5768db89dd8ac30fd0e414f"
};

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function AppPage() {
  const [searchQuery, setSearchQuery] = useState("");
  const [isSearching, setIsSearching] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);
  const [results, setResults] = useState<any>(null);
  const [songCount, setSongCount] = useState<number | null>(null);

  // Image upload state
  const [selectedImage, setSelectedImage] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // API key state
  const [needsApiKey, setNeedsApiKey] = useState(false);
  const [showApiKeyModal, setShowApiKeyModal] = useState(false);
  const [userApiKey, setUserApiKey] = useState("");
  const [savedApiKey, setSavedApiKey] = useState<string | null>(null);

  useEffect(() => {
    // Load saved API key from localStorage
    const stored = localStorage.getItem("chroma_tune_api_key");
    if (stored) setSavedApiKey(stored);

    fetchStats();
    checkApiStatus();
  }, []);

  const fetchStats = async () => {
    try {
      const res = await fetch(`${API_BASE}/stats`);
      if (res.ok) {
        const data = await res.json();
        setSongCount(data.song_count);
      }
    } catch (e) {
      console.error("Failed to fetch stats", e);
    }
  };

  const checkApiStatus = async () => {
    try {
      const res = await fetch(`${API_BASE}/api-status`);
      if (res.ok) {
        const data = await res.json();
        setNeedsApiKey(data.needs_user_key);
        if (data.needs_user_key && !localStorage.getItem("chroma_tune_api_key")) {
          setShowApiKeyModal(true);
        }
      }
    } catch (e) {
      console.error("Failed to check API status", e);
    }
  };

  const saveApiKey = () => {
    if (userApiKey.trim()) {
      localStorage.setItem("chroma_tune_api_key", userApiKey.trim());
      setSavedApiKey(userApiKey.trim());
      setUserApiKey("");
      setShowApiKeyModal(false);
      toast.success("API key saved", { description: "Google AI key stored locally." });
    }
  };

  const clearApiKey = () => {
    localStorage.removeItem("chroma_tune_api_key");
    setSavedApiKey(null);
    toast.info("API key removed");
  };

  const handleSync = async () => {
    setIsSyncing(true);
    try {
      const res = await fetch(`${API_BASE}/sync`, { method: "POST" });
      const data = await res.json();
      setSongCount(data.song_count);

      if (data.status === "error") {
        toast.error("Sync failed", { description: data.error });
      } else if (data.new_songs === 0) {
        toast.success("Already synced", { description: "No new songs to add." });
      } else {
        toast.success("Playlist synced!", { description: `Added ${data.new_songs} new songs.` });
      }
    } catch (e) {
      toast.error("Sync failed", { description: "Could not connect to server." });
    } finally {
      setIsSyncing(false);
    }
  };

  const handleImageSelect = (file: File) => {
    if (!file.type.startsWith('image/')) {
      toast.error("Invalid file", { description: "Please select an image file." });
      return;
    }
    setSelectedImage(file);
    setImagePreview(URL.createObjectURL(file));
  };

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) handleImageSelect(file);
  };

  const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const clearImage = () => {
    setSelectedImage(null);
    setImagePreview(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const handleSearch = async () => {
    if (!searchQuery && !selectedImage) {
      toast.error("Enter a vibe description or upload an image");
      return;
    }

    // Check if we need API key but don't have one
    if (needsApiKey && !savedApiKey) {
      setShowApiKeyModal(true);
      return;
    }

    setIsSearching(true);
    const formData = new FormData();
    if (searchQuery) formData.append("text", searchQuery);
    if (selectedImage) formData.append("file", selectedImage);
    formData.append("provider", "google");
    if (savedApiKey) {
      formData.append("user_api_key", savedApiKey);
    }

    try {
      const res = await fetch(`${API_BASE}/search`, { method: "POST", body: formData });

      if (res.status === 429) {
        toast.error("Rate limited", { description: "Too many requests. Please wait a minute." });
        return;
      }

      if (res.status === 503) {
        setNeedsApiKey(true);
        setShowApiKeyModal(true);
        toast.error("API unavailable", { description: "Please provide your own API key." });
        return;
      }

      if (!res.ok) {
        const error = await res.json();
        throw new Error(error.detail || "Search failed");
      }

      const data = await res.json();
      setResults(data);
      clearImage(); // Clear image after successful search

      if (data.used_user_key) {
        toast.info("Using your Google AI key");
      }
    } catch (e: any) {
      toast.error("Search Error", { description: e.message || "Make sure the backend is running." });
    } finally {
      setIsSearching(false);
    }
  };

  const hasApiKey = !!savedApiKey;

  return (
    <div className="min-h-screen bg-zinc-950 text-white font-sans selection:bg-green-500 selection:text-black pb-20">
      {/* Background Gradients */}
      <div className="fixed top-0 left-0 w-full h-full overflow-hidden -z-10 pointer-events-none">
        <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-green-600/20 rounded-full blur-[120px]" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-purple-600/10 rounded-full blur-[120px]" />
      </div>

      {/* API Key Modal */}
      <AnimatePresence>
        {showApiKeyModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4"
            onClick={() => setShowApiKeyModal(false)}
          >
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              onClick={(e) => e.stopPropagation()}
              className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 max-w-md w-full"
            >
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-yellow-500/10 rounded-lg">
                    <Key className="w-5 h-5 text-yellow-500" />
                  </div>
                  <h3 className="text-lg font-semibold">Add API Key</h3>
                </div>
                <button onClick={() => setShowApiKeyModal(false)} className="text-zinc-500 hover:text-white">
                  <X className="w-5 h-5" />
                </button>
              </div>

              <p className="text-zinc-400 text-sm mb-4">
                {needsApiKey
                  ? "Server API unavailable. Add your own Google AI key to continue."
                  : "Add your own Google AI key for search."}
              </p>

              <a
                href="https://aistudio.google.com/apikey"
                target="_blank"
                className="text-green-500 hover:underline text-sm mb-4 block"
              >
                Get a free Google AI API key →
              </a>

              <Input
                placeholder="Enter your Google AI API key"
                type="password"
                className="bg-zinc-950 border-zinc-700 text-white mb-4"
                value={userApiKey}
                onChange={(e: ChangeEvent<HTMLInputElement>) => setUserApiKey(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && saveApiKey()}
              />

              <Button onClick={saveApiKey} className="w-full bg-green-500 hover:bg-green-400 text-black font-bold">
                Save API Key
              </Button>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      <main className="max-w-4xl mx-auto px-6 py-12 flex flex-col gap-8">
        {/* Header */}
        <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-3 bg-gradient-to-br from-green-400 to-green-600 rounded-xl shadow-lg shadow-green-900/20">
              <Music className="w-8 h-8 text-black" />
            </div>
            <h1 className="text-4xl font-bold tracking-tighter bg-clip-text text-transparent bg-gradient-to-r from-white to-zinc-500">
              ChromaTune
            </h1>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowApiKeyModal(true)}
              className="text-zinc-500 hover:text-white"
            >
              <Key className="w-4 h-4 mr-1" />
              {hasApiKey ? "API Key" : "Add Key"}
            </Button>
            <Link href="/">
              <Button variant="ghost" className="text-zinc-400 hover:text-white">
                <ArrowLeft className="w-4 h-4 mr-2" />
                Back
              </Button>
            </Link>
          </div>
        </motion.div>

        {/* Saved Key Display */}
        {hasApiKey && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex items-center gap-2"
          >
            <span className="text-zinc-500 text-sm">Using:</span>
            <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full bg-zinc-800 text-xs text-blue-400">
              Google AI
              <button onClick={clearApiKey} className="hover:text-white ml-1">
                <X className="w-3 h-3" />
              </button>
            </span>
          </motion.div>
        )}

        {/* API Key Warning Banner */}
        {needsApiKey && !hasApiKey && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex items-center gap-3 p-4 rounded-xl bg-yellow-500/10 border border-yellow-500/20"
          >
            <AlertTriangle className="w-5 h-5 text-yellow-500 shrink-0" />
            <p className="text-yellow-200 text-sm flex-1">
              Server API quota reached. Add your own API key to continue.
            </p>
            <Button size="sm" onClick={() => setShowApiKeyModal(true)} className="bg-yellow-500 hover:bg-yellow-400 text-black">
              Add Key
            </Button>
          </motion.div>
        )}

        {/* Collaborative Playlist Card */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
          <Card className="p-6 bg-zinc-900/50 border-zinc-800 backdrop-blur-xl">
            <div className="flex items-center gap-4">
              {PLAYLIST.image && (
                <img src={PLAYLIST.image} alt={PLAYLIST.name} className="w-16 h-16 rounded-lg object-cover" />
              )}
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <h2 className="text-xl font-bold text-white">{PLAYLIST.name}</h2>
                  <span className="px-2 py-0.5 text-xs rounded-full bg-green-500/10 text-green-400 border border-green-500/20">
                    Collaborative
                  </span>
                </div>
                <p className="text-zinc-400 text-sm">
                  {songCount !== null ? `${songCount} songs indexed` : "Loading..."} • Add songs on Spotify, then sync
                </p>
              </div>
              <div className="flex gap-2">
                <a href={PLAYLIST.url} target="_blank">
                  <Button variant="outline" className="border-zinc-700 hover:bg-zinc-800">
                    <PlusCircle className="w-4 h-4 mr-2" />
                    Add Songs
                  </Button>
                </a>
                <Button onClick={handleSync} disabled={isSyncing} variant="outline" className="border-zinc-700 hover:bg-zinc-800">
                  {isSyncing ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
                </Button>
              </div>
            </div>
          </Card>
        </motion.div>

        {/* Search Box */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
          <Card className="p-8 bg-zinc-900/50 border-zinc-800 backdrop-blur-xl flex flex-col gap-6 relative overflow-hidden group">
            <div className="absolute inset-0 bg-gradient-to-r from-transparent via-zinc-800/10 to-transparent -translate-x-full group-hover:translate-x-full transition-transform duration-1000 pointer-events-none" />

            <div>
              <h2 className="text-2xl font-bold text-white">Vibe Check</h2>
              <p className="text-zinc-400">Describe a mood, scene, or feeling to find matching songs.</p>
            </div>

            <div className="flex gap-3">
              <Input
                placeholder="e.g., Cyberpunk rainy city at night..."
                className="bg-zinc-950/80 border-zinc-700 h-14 text-lg text-white"
                value={searchQuery}
                onChange={(e: ChangeEvent<HTMLInputElement>) => setSearchQuery(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSearch()}
              />
              <Button size="icon" className="h-14 w-14 bg-green-500 hover:bg-green-400 text-black shrink-0" onClick={handleSearch} disabled={isSearching}>
                {isSearching ? <Loader2 className="animate-spin" /> : <Zap />}
              </Button>
            </div>

            {/* Image Upload */}
            <input
              type="file"
              ref={fileInputRef}
              accept="image/*"
              className="hidden"
              onChange={(e) => e.target.files?.[0] && handleImageSelect(e.target.files[0])}
            />

            {imagePreview ? (
              <div className="relative rounded-lg overflow-hidden border border-zinc-700">
                <img src={imagePreview} alt="Selected" className="w-full h-48 object-cover" />
                <button
                  onClick={clearImage}
                  className="absolute top-2 right-2 p-1 bg-black/60 rounded-full hover:bg-black/80 transition-colors"
                >
                  <X className="w-4 h-4" />
                </button>
                <div className="absolute bottom-2 left-2 px-2 py-1 bg-black/60 rounded text-xs flex items-center gap-1">
                  <ImageIcon className="w-3 h-3" />
                  {selectedImage?.name}
                </div>
              </div>
            ) : (
              <div
                onDrop={handleDrop}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onClick={() => fileInputRef.current?.click()}
                className={`border-2 border-dashed rounded-lg p-6 text-center transition-colors cursor-pointer ${
                  isDragging
                    ? "border-green-500 bg-green-500/10 text-green-400"
                    : "border-zinc-800 text-zinc-600 hover:text-zinc-400 hover:border-zinc-600"
                }`}
              >
                <Upload className="w-6 h-6 mx-auto mb-2" />
                <span className="text-sm">
                  {isDragging ? "Drop image here" : "Drag & Drop or Click to Upload Image"}
                </span>
              </div>
            )}

            {/* Example Prompts */}
            <div className="flex flex-wrap gap-2">
              <span className="text-xs text-zinc-500">Try:</span>
              {["Late night coding", "Beach sunset vibes", "Rainy day melancholy", "Workout energy"].map((prompt) => (
                <button
                  key={prompt}
                  onClick={() => setSearchQuery(prompt)}
                  className="px-3 py-1 text-xs rounded-full bg-zinc-800/50 text-zinc-400 hover:bg-zinc-700 hover:text-white transition-colors"
                >
                  {prompt}
                </button>
              ))}
            </div>
          </Card>
        </motion.div>

        {/* Results List */}
        <AnimatePresence>
          {results && results.songs && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-xl font-semibold text-white">AI Picks</h3>
                <span className="text-xs font-mono text-green-500 bg-green-500/10 px-2 py-1 rounded">
                  {results.provider?.toUpperCase() || "GEMINI"}
                </span>
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
                    <div className="flex items-center gap-3">
                      <div className="text-zinc-600 font-mono text-sm">{Math.round(100 - (song.score * 10))}%</div>
                      <ExternalLink className="w-4 h-4 text-zinc-600 group-hover:text-green-500" />
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
