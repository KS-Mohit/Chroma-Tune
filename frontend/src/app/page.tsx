"use client";

import { motion } from "framer-motion";
import { Music, Plus, Zap, Search, Sparkles, Github, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import Link from "next/link";

export default function Home() {
  return (
    <div className="min-h-screen bg-zinc-950 text-white font-sans selection:bg-green-500 selection:text-black">
      {/* Background Gradients */}
      <div className="fixed top-0 left-0 w-full h-full overflow-hidden -z-10 pointer-events-none">
        <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-green-600/20 rounded-full blur-[120px]" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-purple-600/10 rounded-full blur-[120px]" />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[60%] h-[60%] bg-green-500/5 rounded-full blur-[150px]" />
      </div>

      {/* Hero Landing Section */}
      <section className="min-h-screen flex flex-col items-center justify-center px-6 relative">
        {/* Navigation */}
        <nav className="absolute top-0 left-0 right-0 p-6 flex items-center justify-between max-w-7xl mx-auto w-full">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-gradient-to-br from-green-400 to-green-600 rounded-lg">
              <Music className="w-5 h-5 text-black" />
            </div>
            <span className="text-xl font-bold tracking-tight">Chroma-Tune</span>
          </div>
          <a
            href="https://github.com/KS-Mohit/Chroma-Tune"
            target="_blank"
            className="p-2 rounded-lg hover:bg-zinc-800 transition-colors"
          >
            <Github className="w-5 h-5" />
          </a>
        </nav>

        {/* Hero Content */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8 }}
          className="text-center max-w-4xl"
        >
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ delay: 0.2, type: "spring", stiffness: 200 }}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-green-500/10 border border-green-500/20 text-green-400 text-sm mb-8"
          >
            <Sparkles className="w-4 h-4" />
            AI-Powered Music Discovery
          </motion.div>

          <h1 className="text-5xl md:text-7xl font-bold tracking-tighter mb-6">
            Find Music That
            <br />
            <span className="bg-gradient-to-r from-green-400 via-green-500 to-emerald-400 bg-clip-text text-transparent">
              Matches Your Vibe
            </span>
          </h1>

          <p className="text-xl text-zinc-400 max-w-2xl mx-auto mb-10">
            Describe a mood, scene, or feeling. Our AI searches a community-curated
            Spotify playlist to find the perfect tracks. Anyone can add songs!
          </p>

          <Link href="/app">
            <Button
              size="lg"
              className="bg-green-500 hover:bg-green-400 text-black font-bold text-lg px-8 py-6 rounded-xl"
            >
              Try It Now
              <ChevronRight className="w-5 h-5 ml-2" />
            </Button>
          </Link>
        </motion.div>

        {/* Features Grid */}
        <motion.div
          initial={{ opacity: 0, y: 40 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4, duration: 0.8 }}
          className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-4xl w-full mt-20"
        >
          <div className="p-6 rounded-2xl bg-zinc-900/50 border border-zinc-800 backdrop-blur-sm flex flex-col items-center justify-center text-center">
            <div className="w-12 h-12 rounded-xl bg-green-500/10 flex items-center justify-center mb-4">
              <Plus className="w-6 h-6 text-green-500" />
            </div>
            <h3 className="text-lg font-semibold mb-2">Community Playlist</h3>
            <p className="text-zinc-500 text-sm">One shared collaborative playlist. Add songs via Spotify, we index them with AI.</p>
          </div>

          <div className="p-6 rounded-2xl bg-zinc-900/50 border border-zinc-800 backdrop-blur-sm flex flex-col items-center justify-center text-center">
            <div className="w-12 h-12 rounded-xl bg-purple-500/10 flex items-center justify-center mb-4">
              <Search className="w-6 h-6 text-purple-500" />
            </div>
            <h3 className="text-lg font-semibold mb-2">Describe Your Vibe</h3>
            <p className="text-zinc-500 text-sm">"Rainy coffee shop" or "Epic road trip sunset" - just type it.</p>
          </div>

          <div className="p-6 rounded-2xl bg-zinc-900/50 border border-zinc-800 backdrop-blur-sm flex flex-col items-center justify-center text-center">
            <div className="w-12 h-12 rounded-xl bg-blue-500/10 flex items-center justify-center mb-4">
              <Zap className="w-6 h-6 text-blue-500" />
            </div>
            <h3 className="text-lg font-semibold mb-2">Get AI Matches</h3>
            <p className="text-zinc-500 text-sm">Gemini AI finds tracks that perfectly match your description.</p>
          </div>
        </motion.div>
      </section>

      {/* Footer */}
      <footer className="border-t border-zinc-900 py-8 px-6">
        <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-gradient-to-br from-green-400 to-green-600 rounded-lg">
              <Music className="w-4 h-4 text-black" />
            </div>
            <span className="font-semibold">Chroma-Tune</span>
          </div>
          <p className="text-zinc-600 text-sm">
            Built with Gemini AI, Pinecone, and Spotify API
          </p>
        </div>
      </footer>
    </div>
  );
}
