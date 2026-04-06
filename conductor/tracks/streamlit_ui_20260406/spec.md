# Track Spec: Streamlit Web UI

## Overview
Add a Streamlit web interface to the Chess Strategic Profiler that exposes the
full analysis pipeline and its outputs through a multi-page dashboard. The UI
sits on top of the existing `modules/` layer without modifying it.

## Pages

### 1. Input Screen (`ui/pages/1_analyze.py`)
- Text input for Chess.com username + number-of-months slider
- File uploader for local `.pgn` files (with a color selector: white/black)
- "Run Analysis" button that calls `analyze_player_from_username` or
  `analyze_player` directly in-process, with a live `st.progress` bar
- Option to load an existing saved profile from `output/` instead of
  running a fresh analysis

### 2. Profile Dashboard (`ui/pages/2_profile.py`)
- Profile selector: lists all `*_profile.json` files in `output/`,
  user picks one from a dropdown
- Metrics row: total games, positions analyzed, overall error rate
- Bar chart (Plotly): error occurrences per concept, sorted descending
- Bar chart (Plotly): average error magnitude (centipawns) per concept
- Error rate % per concept as a color-coded table

### 3. Game Explorer (`ui/pages/3_explorer.py`)
- Loads sample positions from the selected profile's weakness data
- Weakness selector: dropdown of concepts that have sample positions
- For each sample position: renders the FEN as an SVG board using
  `chess.svg` displayed via `st.components.v1.html`, shows the move
  played vs. best move, and displays error magnitude in centipawns

### 4. Diagnosis Report (`ui/pages/4_diagnosis.py`)
- Profile selector: lists all `*_diagnosis.json` files in `output/`
- Root cause card: name, description, confidence badge
- Weakness classification table: concept | classification | reasoning
- Study priority list: ranked items with Silman chapter, page, and reason
- Cognitive pattern summary block

## Functional Requirements
- FR1: User can trigger a fresh analysis (Chess.com or PGN) from the UI
- FR2: Analysis progress is visible in real time via `st.progress` / `st.spinner`
- FR3: User can browse and load any previously saved profile from `output/`
- FR4: All charts are interactive (Plotly: hover tooltips, zoom)
- FR5: Chessboard renders any FEN position from the player's sample errors using `chess.svg` + `st.components.v1.html`
- FR6: UI never modifies files in `modules/` — read-only integration

## Non-Functional Requirements
- NFR1: Single `streamlit run app.py` command launches the full UI
- NFR2: No external web server or database required
- NFR3: All new dependencies added to `requirements.txt`

## New Dependencies
- `streamlit`
- `plotly`
- (chessboard rendering uses `chess.svg` from the existing `chess` library — no extra package needed)

## File Structure
```
app.py                        ← Streamlit entry point (home/nav)
ui/
  components/
    weakness_chart.py         ← Plotly chart helpers
    diagnosis_card.py         ← Diagnosis display helpers
  pages/
    1_analyze.py
    2_profile.py
    3_explorer.py
    4_diagnosis.py
```

## Acceptance Criteria
- [ ] `streamlit run app.py` launches without errors
- [ ] Fresh analysis can be triggered and completes successfully from the UI
- [ ] All saved profiles in `output/` appear in the profile selector
- [ ] Profile dashboard renders correct charts from loaded profile JSON
- [ ] Game Explorer renders at least one chessboard position per weakness
- [ ] Diagnosis report correctly displays root cause and study priority
- [ ] All existing CLI functionality (`python main.py`) remains unaffected

## Out of Scope
- User authentication
- Cloud deployment
- Real-time game streaming
- Mobile-specific layout optimization
- Editing or deleting saved profiles from the UI
