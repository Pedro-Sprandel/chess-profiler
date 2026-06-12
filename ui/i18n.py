import streamlit as st

TRANSLATIONS = {
    "en": {
        # Sidebar
        "nav.title": "♟ Chess Profiler",
        "nav.home": "🏠 Home",
        "nav.analyze": "🔍 Analyze",
        "nav.profile": "📊 Profile Dashboard",
        "nav.explorer": "♟ Game Explorer",
        "nav.diagnosis": "🧠 Diagnosis Report",
        "lang.label": "Language",
        "sidebar.profile": "Active Profile",
        "sidebar.no_profiles": "No profiles yet — run an analysis first.",
        "sidebar.delete": "🗑 Delete profile",
        "sidebar.delete_warn": "This permanently deletes **{name}** and its diagnosis. You can then re-run an analysis on the same nickname.",
        "sidebar.delete_confirm": "Yes, delete",
        "sidebar.deleted": "Deleted **{name}**.",

        # Home
        "home.title": "♟ Chess Strategic Profiler",
        "home.welcome": (
            "Welcome to the **Chess Strategic Profiler** — a personalized strategic diagnostic system "
            "for chess players based on Jeremy Silman's *The Amateur's Mind*.\n\n"
            "Use the sidebar to jump to any section:\n\n"
            "| Section | Description |\n"
            "|---------|-------------|\n"
            "| **Analyze** | Run a fresh analysis or load a saved profile |\n"
            "| **Profile Dashboard** | View weakness charts and error statistics |\n"
            "| **Game Explorer** | Inspect individual error positions on a chessboard |\n"
            "| **Diagnosis Report** | Read the AI-generated root cause diagnosis |"
        ),

        # Analyze
        "analyze.title": "🔍 Analyze",
        "analyze.tab.fresh": "Fresh Analysis",
        "analyze.tab.load": "Load Saved Profile",
        "analyze.fresh.subheader": "Run a new analysis",
        "analyze.source.label": "Source",
        "analyze.source.chesscom": "Chess.com username",
        "analyze.source.pgn": "Local PGN file",
        "analyze.username.label": "Chess.com username",
        "analyze.ngames.label": "Number of recent games to fetch",
        "analyze.depth.label": "Stockfish depth",
        "analyze.depth.help": "Search depth for move analysis. Higher is more accurate (fewer false positives) but slower.",
        "analyze.btn.run": "Run Analysis",
        "analyze.progress.starting": "Starting...",
        "analyze.progress.done": "Done!",
        "analyze.success": "Analysis complete!",
        "analyze.info.scroll": "Scroll down to **Profile Dashboard** or **Diagnosis Report** to explore results.",
        "analyze.error.no_user": "Please enter a username.",
        "analyze.error.failed": "Analysis failed: {e}",
        "analyze.pgn.label": "Upload a PGN file",
        "analyze.color.label": "Your color in the games",
        "analyze.color.white": "White",
        "analyze.color.black": "Black",
        "analyze.playername.label": "Player name (used for output filenames)",
        "analyze.error.no_pgn": "Please upload a PGN file.",
        "analyze.error.no_name": "Please enter a player name.",
        "analyze.load.subheader": "Load a saved profile",
        "analyze.load.no_profiles": "No saved profiles found in `output/`. Run a fresh analysis first.",
        "analyze.load.selected": "Selected: **{f}**",
        "analyze.load.info": "Scroll down to **Profile Dashboard** or **Game Explorer** to explore this profile.",

        # Profile
        "profile.title": "📊 Profile Dashboard",
        "profile.no_profiles": "No saved profiles found in `output/`. Run an analysis from the **Analyze** section first.",
        "profile.metric.games": "Games Analyzed",
        "profile.metric.positions": "Positions Analyzed",
        "profile.metric.errors": "Errors Detected",
        "profile.metric.missed_mates": "Missed Checkmates",
        "profile.metric.allowed_mates": "Allowed Checkmates",
        "profile.metric.error_rate": "Overall Error Rate",
        "profile.no_weaknesses": "No recurring weaknesses detected in this profile (minimum 3 occurrences required).",
        "profile.table.subheader": "Weakness Detail",
        "profile.col.concept": "Concept",
        "profile.col.error_occ": "Error Occurrences",
        "profile.col.total_occ": "Total Occurrences",
        "profile.col.error_rate": "Error Rate (%)",
        "profile.col.avg_error": "Avg Error (cp)",
        "chart.count.title": "Error Occurrences per Concept",
        "chart.count.y": "Error Count",
        "chart.magnitude.title": "Avg Error Magnitude per Concept (centipawns)",
        "chart.magnitude.y": "Avg Error (cp)",
        "chart.x_concept": "Concept",

        # Explorer
        "explorer.title": "♟ Game Explorer",
        "explorer.no_profiles": "No saved profiles found in `output/`. Run an analysis from the **Analyze** section first.",
        "explorer.no_positions": "No sample positions available in this profile.",
        "explorer.select_concept": "Select a weakness concept",
        "explorer.summary": "**{concept}** — {errors} errors ({rate:.0f}% error rate, avg {avg} cp loss)",
        "explorer.sample_positions": "Sample Positions ({n} shown)",
        "explorer.expander": "Position {i} — Game {game} · Error: {cp} cp",
        "explorer.no_fen": "No FEN available for this position.",
        "explorer.you": "⬅ you",
        "explorer.game": "**Game:** {v}",
        "explorer.error_cp": "**Error:** {v} centipawns",
        "explorer.move_played": "🔴 **Move played:** `{v}`",
        "explorer.best_same": "✅ **Best move (same):** `{v}`",
        "explorer.best_move": "🟢 **Best move:** `{v}`",
        "explorer.fen": "**FEN:** `{v}`",
        "explorer.ask_ai": "🤖 Ask AI why?",
        "explorer.ai_thinking": "Asking the AI...",
        "explorer.load_more": "➕ Load more ({shown} of {total})",

        # Diagnosis
        "diagnosis.title": "🧠 Diagnosis Report",
        "diagnosis.running": "Running AI diagnosis — your profile above is ready to explore while this loads...",
        "diagnosis.no_files": "No saved diagnoses found in `output/`. Run an analysis from the **Analyze** section first.",
        "diagnosis.root_cause": "Root Cause",
        "diagnosis.confidence": "**{name}** · Confidence: {conf}",
        "diagnosis.cognitive": "Cognitive Pattern to Change",
        "diagnosis.no_cognitive": "No cognitive pattern data available.",
        "diagnosis.weakness_class": "Weakness Classification",
        "diagnosis.no_weakness": "No weakness classification data available.",
        "diagnosis.study_plan": "Silman Study Plan",
        "diagnosis.study_item": "**#{rank} — {concept}** · Chapter {chapter}, p. {page}",
        "diagnosis.no_study": "No study priority data available.",
        "diagnosis.col.concept": "Concept",
        "diagnosis.col.classification": "Classification",
        "diagnosis.col.reasoning": "Reasoning",
    },

    "pt": {
        # Sidebar
        "nav.title": "♟ Perfilador de Xadrez",
        "nav.home": "🏠 Início",
        "nav.analyze": "🔍 Analisar",
        "nav.profile": "📊 Painel de Perfil",
        "nav.explorer": "♟ Explorador de Partidas",
        "nav.diagnosis": "🧠 Diagnóstico",
        "lang.label": "Idioma",
        "sidebar.profile": "Perfil Ativo",
        "sidebar.no_profiles": "Nenhum perfil ainda — execute uma análise primeiro.",
        "sidebar.delete": "🗑 Excluir perfil",
        "sidebar.delete_warn": "Isto exclui permanentemente **{name}** e seu diagnóstico. Depois você pode reexecutar uma análise no mesmo apelido.",
        "sidebar.delete_confirm": "Sim, excluir",
        "sidebar.deleted": "**{name}** excluído.",

        # Home
        "home.title": "♟ Perfilador Estratégico de Xadrez",
        "home.welcome": (
            "Bem-vindo ao **Perfilador Estratégico de Xadrez** — um sistema de diagnóstico estratégico "
            "personalizado para jogadores de xadrez, baseado no livro *The Amateur's Mind* de Jeremy Silman.\n\n"
            "Use a barra lateral para navegar entre as seções:\n\n"
            "| Seção | Descrição |\n"
            "|-------|-----------|\n"
            "| **Analisar** | Execute uma nova análise ou carregue um perfil salvo |\n"
            "| **Painel de Perfil** | Veja gráficos de fraquezas e estatísticas de erros |\n"
            "| **Explorador de Partidas** | Inspecione posições de erro no tabuleiro |\n"
            "| **Diagnóstico** | Leia o diagnóstico de causa raiz gerado pela IA |"
        ),

        # Analyze
        "analyze.title": "🔍 Analisar",
        "analyze.tab.fresh": "Nova Análise",
        "analyze.tab.load": "Carregar Perfil Salvo",
        "analyze.fresh.subheader": "Executar nova análise",
        "analyze.source.label": "Fonte",
        "analyze.source.chesscom": "Usuário do Chess.com",
        "analyze.source.pgn": "Arquivo PGN local",
        "analyze.username.label": "Usuário do Chess.com",
        "analyze.ngames.label": "Número de partidas recentes para buscar",
        "analyze.depth.label": "Profundidade do Stockfish",
        "analyze.depth.help": "Profundidade de análise dos lances. Maior é mais preciso (menos falsos positivos), porém mais lento.",
        "analyze.btn.run": "Executar Análise",
        "analyze.progress.starting": "Iniciando...",
        "analyze.progress.done": "Concluído!",
        "analyze.success": "Análise concluída!",
        "analyze.info.scroll": "Role para baixo até **Painel de Perfil** ou **Diagnóstico** para explorar os resultados.",
        "analyze.error.no_user": "Por favor, insira um nome de usuário.",
        "analyze.error.failed": "Análise falhou: {e}",
        "analyze.pgn.label": "Enviar arquivo PGN",
        "analyze.color.label": "Sua cor nas partidas",
        "analyze.color.white": "Brancas",
        "analyze.color.black": "Pretas",
        "analyze.playername.label": "Nome do jogador (usado nos arquivos de saída)",
        "analyze.error.no_pgn": "Por favor, envie um arquivo PGN.",
        "analyze.error.no_name": "Por favor, insira um nome de jogador.",
        "analyze.load.subheader": "Carregar perfil salvo",
        "analyze.load.no_profiles": "Nenhum perfil salvo encontrado em `output/`. Execute uma nova análise primeiro.",
        "analyze.load.selected": "Selecionado: **{f}**",
        "analyze.load.info": "Role para baixo até **Painel de Perfil** ou **Explorador de Partidas** para explorar este perfil.",

        # Profile
        "profile.title": "📊 Painel de Perfil",
        "profile.no_profiles": "Nenhum perfil salvo encontrado em `output/`. Execute uma análise na seção **Analisar** primeiro.",
        "profile.metric.games": "Partidas Analisadas",
        "profile.metric.positions": "Posições Analisadas",
        "profile.metric.errors": "Erros Detectados",
        "profile.metric.missed_mates": "Cheques-Mates Perdidos",
        "profile.metric.allowed_mates": "Cheques-Mates Sofridos",
        "profile.metric.error_rate": "Taxa de Erro Geral",
        "profile.no_weaknesses": "Nenhuma fraqueza recorrente detectada neste perfil (mínimo de 3 ocorrências necessárias).",
        "profile.table.subheader": "Detalhes das Fraquezas",
        "profile.col.concept": "Conceito",
        "profile.col.error_occ": "Ocorrências de Erro",
        "profile.col.total_occ": "Total de Ocorrências",
        "profile.col.error_rate": "Taxa de Erro (%)",
        "profile.col.avg_error": "Erro Médio (cp)",
        "chart.count.title": "Ocorrências de Erro por Conceito",
        "chart.count.y": "Contagem de Erros",
        "chart.magnitude.title": "Magnitude Média de Erro por Conceito (centipawns)",
        "chart.magnitude.y": "Erro Médio (cp)",
        "chart.x_concept": "Conceito",

        # Explorer
        "explorer.title": "♟ Explorador de Partidas",
        "explorer.no_profiles": "Nenhum perfil salvo encontrado em `output/`. Execute uma análise na seção **Analisar** primeiro.",
        "explorer.no_positions": "Nenhuma posição de exemplo disponível neste perfil.",
        "explorer.select_concept": "Selecionar conceito de fraqueza",
        "explorer.summary": "**{concept}** — {errors} erros ({rate:.0f}% de taxa de erro, média de {avg} cp perdidos)",
        "explorer.sample_positions": "Posições de Exemplo ({n} exibidas)",
        "explorer.expander": "Posição {i} — Partida {game} · Erro: {cp} cp",
        "explorer.no_fen": "FEN não disponível para esta posição.",
        "explorer.you": "⬅ você",
        "explorer.game": "**Partida:** {v}",
        "explorer.error_cp": "**Erro:** {v} centipeões",
        "explorer.move_played": "🔴 **Lance jogado:** `{v}`",
        "explorer.best_same": "✅ **Melhor lance (igual):** `{v}`",
        "explorer.best_move": "🟢 **Melhor lance:** `{v}`",
        "explorer.fen": "**FEN:** `{v}`",
        "explorer.ask_ai": "🤖 Perguntar à IA por quê?",
        "explorer.ai_thinking": "Perguntando à IA...",
        "explorer.load_more": "➕ Carregar mais ({shown} de {total})",

        # Diagnosis
        "diagnosis.title": "🧠 Diagnóstico",
        "diagnosis.running": "Executando diagnóstico da IA — seu perfil acima já pode ser explorado enquanto isto carrega...",
        "diagnosis.no_files": "Nenhum diagnóstico salvo encontrado em `output/`. Execute uma análise na seção **Analisar** primeiro.",
        "diagnosis.root_cause": "Causa Raiz",
        "diagnosis.confidence": "**{name}** · Confiança: {conf}",
        "diagnosis.cognitive": "Padrão Cognitivo a Mudar",
        "diagnosis.no_cognitive": "Dados de padrão cognitivo não disponíveis.",
        "diagnosis.weakness_class": "Classificação de Fraquezas",
        "diagnosis.no_weakness": "Dados de classificação de fraquezas não disponíveis.",
        "diagnosis.study_plan": "Plano de Estudo Silman",
        "diagnosis.study_item": "**#{rank} — {concept}** · Capítulo {chapter}, p. {page}",
        "diagnosis.no_study": "Dados de prioridade de estudo não disponíveis.",
        "diagnosis.col.concept": "Conceito",
        "diagnosis.col.classification": "Classificação",
        "diagnosis.col.reasoning": "Justificativa",
    },
}


def t(key: str, **kwargs) -> str:
    lang = st.session_state.get("lang", "pt")
    text = TRANSLATIONS.get(lang, TRANSLATIONS["pt"]).get(key, key)
    return text.format(**kwargs) if kwargs else text
