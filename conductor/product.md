# Initial Concept

Chess Strategic Profiler — a system that analyzes a player's chess games in PGN format, detects recurring strategic weakness patterns using deterministic rules (python-chess + Stockfish), and uses an LLM to identify the root cause behind the detected symptoms, connecting the diagnosis to the pedagogical concepts from Jeremy Silman's book "The Amateur's Mind".

---

# Product Guide

## Overview
Chess Strategic Profiler is a personalized strategic diagnostic system for chess players.
It analyzes a set of games from a single player, detects recurring positional and strategic
mistakes, and produces a structured diagnosis that maps those weaknesses to concepts from
Jeremy Silman's "The Amateur's Mind" — providing targeted, prioritized study recommendations.

## Target Users
Amateur chess players (roughly 800–1800 Elo) who want to improve their strategic understanding
beyond tactical puzzles. Also serves as an academic demonstration of a hybrid AI architecture
for the TCC (undergraduate thesis) in Information Systems at FACCAT.

## Core Goals
1. Identify which strategic concepts a player consistently mishandles.
2. Distinguish between root causes and secondary symptoms.
3. Provide a prioritized, Silman-aligned study plan based on quantitative evidence from real games.

## Key Features
- **PGN Ingestion:** Load and iterate over games from a `.pgn` file.
- **Deterministic Concept Detection:** Rule-based detection of 7 strategic concepts per position
  (weak squares, open files, isolated pawns, bishop pair, knight outposts, king safety, space advantage).
- **Stockfish Validation:** For each position where the player moved, compare the played move
  against the engine's best move to determine if an error occurred (threshold: 50 centipawns).
- **Profile Building:** Aggregate error data across all games to identify recurring weaknesses
  (minimum 3 occurrences to qualify).
- **AI Diagnosis:** Use Claude (claude-opus-4-6) to perform root-cause analysis on the quantitative
  profile, classify weaknesses as PRIMARY / SECONDARY / NOISE, and produce a structured JSON diagnosis.
- **Structured Output:** Save player profile and diagnosis as JSON files in the `output/` directory.

## Architecture
Three-layer hybrid architecture:
1. **Deterministic layer** (python-chess): position feature extraction
2. **Quantitative layer** (Stockfish): move quality validation
3. **Reasoning layer** (LLM / Claude): causal pattern identification

## Out of Scope
- Real-time game analysis
- Multi-player comparison
- Opening or endgame theory analysis
- GUI or web interface
