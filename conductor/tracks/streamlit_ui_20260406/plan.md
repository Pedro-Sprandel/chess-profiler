# Plan: Streamlit Web UI

## Phase 1: Setup & Scaffolding

- [x] Task: Add new dependencies to `requirements.txt` [8ab94f2]
  - [x] Sub-task: Write a test that imports `streamlit`, `plotly`, and `chess.svg` and asserts no `ImportError`
  - [x] Sub-task: Add `streamlit` and `plotly` to `requirements.txt` and run `pip install -r requirements.txt` (chessboard uses built-in `chess.svg`)

- [x] Task: Create `ui/` directory structure and `app.py` entry point [59c5cb7]
  - [x] Sub-task: Write a test using `streamlit.testing.v1.AppTest` that loads `app.py` and asserts the page title is present and no exceptions are raised
  - [x] Sub-task: Create `ui/__init__.py`, `ui/components/__init__.py`, `ui/pages/__init__.py`, empty placeholder files for all pages, and implement `app.py` with `st.set_page_config` and sidebar navigation

- [ ] Task: Conductor - User Manual Verification 'Phase 1: Setup & Scaffolding' (Protocol in workflow.md)

---

## Phase 2: UI Helper Components

- [ ] Task: Implement `ui/components/weakness_chart.py`
  - [ ] Sub-task: Write unit tests for `build_error_count_chart(weaknesses)` and `build_error_magnitude_chart(weaknesses)` asserting they return valid Plotly `Figure` objects with correct data
  - [ ] Sub-task: Implement `build_error_count_chart` and `build_error_magnitude_chart` using `plotly.express.bar`

- [ ] Task: Implement `ui/components/diagnosis_card.py`
  - [ ] Sub-task: Write unit tests for `format_root_cause(diagnosis)`, `format_weakness_table(diagnosis)`, and `format_study_priority(diagnosis)` asserting correct structure and types
  - [ ] Sub-task: Implement the three formatting functions that return structured data ready for `st.dataframe` / `st.metric` / `st.markdown`

- [ ] Task: Conductor - User Manual Verification 'Phase 2: UI Helper Components' (Protocol in workflow.md)

---

## Phase 3: Input & Analysis Page

- [ ] Task: Implement `ui/pages/1_analyze.py`
  - [ ] Sub-task: Write `AppTest` tests asserting the page renders the username input, month slider, PGN uploader, color selector, and "Run Analysis" button without error; assert that loading an existing profile populates the profile selector
  - [ ] Sub-task: Implement the page with two tabs — "Fresh Analysis" (Chess.com username form + PGN upload form, both calling the respective pipeline function with `st.progress`) and "Load Saved Profile" (dropdown of `output/*_profile.json` files)

- [ ] Task: Conductor - User Manual Verification 'Phase 3: Input & Analysis Page' (Protocol in workflow.md)

---

## Phase 4: Profile Dashboard Page

- [ ] Task: Implement `ui/pages/2_profile.py`
  - [ ] Sub-task: Write `AppTest` tests with a fixture profile JSON asserting the metrics row shows correct values and the two Plotly charts are rendered
  - [ ] Sub-task: Implement the page: profile selector dropdown, metrics row (`st.metric`), error-count bar chart, error-magnitude bar chart, and color-coded error-rate table (`st.dataframe` with background gradient)

- [ ] Task: Conductor - User Manual Verification 'Phase 4: Profile Dashboard Page' (Protocol in workflow.md)

---

## Phase 5: Game Explorer Page

- [ ] Task: Implement `ui/pages/3_explorer.py`
  - [ ] Sub-task: Write `AppTest` tests with a fixture profile JSON asserting the concept selector populates correctly and the position section renders without error for a given FEN
  - [ ] Sub-task: Implement the page: profile selector, concept dropdown (only concepts with `sample_positions`), and for each sample position render the FEN via `chess.svg` + `st.components.v1.html`, the move played, the best move, and error magnitude

- [ ] Task: Conductor - User Manual Verification 'Phase 5: Game Explorer Page' (Protocol in workflow.md)

---

## Phase 6: Diagnosis Report Page

- [ ] Task: Implement `ui/pages/4_diagnosis.py`
  - [ ] Sub-task: Write `AppTest` tests with a fixture diagnosis JSON asserting root cause card, classification table, and study priority list all render correctly
  - [ ] Sub-task: Implement the page: diagnosis selector dropdown, root cause card (name + description + confidence badge via `st.info`/`st.success`/`st.warning`), weakness classification table, ranked study priority list with Silman chapter/page, and cognitive pattern block

- [ ] Task: Conductor - User Manual Verification 'Phase 6: Diagnosis Report Page' (Protocol in workflow.md)

---

## Phase 7: Integration & Final Verification

- [ ] Task: End-to-end integration test
  - [ ] Sub-task: Write an integration test that loads a real `output/*_profile.json` and `output/*_diagnosis.json` (if present) through the page components and asserts no exceptions
  - [ ] Sub-task: Manually verify `streamlit run app.py` launches and all four pages are reachable via sidebar navigation

- [ ] Task: Verify CLI remains unaffected
  - [ ] Sub-task: Run `python main.py --help` and assert exit code 0; run existing unit tests for `modules/` and assert all pass

- [ ] Task: Conductor - User Manual Verification 'Phase 7: Integration & Final Verification' (Protocol in workflow.md)
