import json
import time
import anthropic
from config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL, ANTHROPIC_MAX_TOKENS

# Quantas vezes reenviar a requisição em erros transitórios (rate limit / 5xx / conexão)
_MAX_RETRIES = 3
_RETRY_BASE_DELAY = 2.0  # segundos; backoff exponencial


def _extract_json(raw: str) -> dict:
    """
    Extrai o objeto JSON da resposta do modelo de forma robusta.

    Lida com texto cercado por blocos markdown (```json ... ```), com ou sem
    a tag de linguagem, e com texto extra antes/depois. Levanta ValueError com
    um trecho da resposta caso não seja possível parsear.
    """
    text = raw.strip()

    # Remove cerca de código markdown se presente em qualquer posição
    if "```" in text:
        parts = text.split("```")
        # O conteúdo entre o primeiro e o segundo ``` é o bloco de código
        if len(parts) >= 2:
            text = parts[1]
            if text.lstrip().lower().startswith("json"):
                text = text.lstrip()[4:]
    text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Fallback: recorta do primeiro '{' ao último '}'
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                pass
        snippet = raw[:300].replace("\n", " ")
        raise ValueError(
            f"Resposta da IA não é um JSON válido. Início da resposta: {snippet!r}"
        )


def load_silman_concepts(path: str = "data/silman_concepts.json") -> dict:
    """
    Carrega a base de conhecimento do Silman e retorna um dict
    indexado por detection_key.
    """
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {c["detection_key"]: c for c in data["concepts"]}


def diagnose(player_profile: dict, silman_concepts: dict) -> dict:
    """
    Usa o Claude para identificar a causa raiz das fraquezas recorrentes.

    O LLM recebe os dados quantitativos brutos e deve:
    1. Identificar o padrão subjacente (causa raiz)
    2. Classificar as fraquezas detectadas em primárias e secundárias
    3. Determinar quais fraquezas são sintomas de um problema maior
    4. Indicar prioridade de estudo no Silman

    Retorna JSON estruturado com o diagnóstico.
    """
    if not ANTHROPIC_API_KEY:
        raise RuntimeError(
            "ANTHROPIC_API_KEY não configurada. Defina-a no arquivo .env "
            "(veja .env.example) antes de rodar o diagnóstico da IA."
        )

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    weaknesses_with_context = []
    for weakness in player_profile["weaknesses"]:
        concept_key = weakness["concept"]
        silman_info = silman_concepts.get(concept_key, {})
        weaknesses_with_context.append({
            **weakness,
            "silman_name": silman_info.get("name", concept_key),
            "silman_chapter": silman_info.get("silman_chapter"),
            "silman_category": silman_info.get("silman_category"),
            "silman_implications": silman_info.get("strategic_implications")
        })

    profile_summary = {
        "total_games": player_profile["total_games"],
        "total_positions_analyzed": player_profile["total_positions_analyzed"],
        "overall_error_rate": player_profile["overall_error_rate"],
        "weaknesses": weaknesses_with_context
    }

    prompt = f"""
You are a chess analyst specialized in strategic pedagogical diagnosis.

Below are raw quantitative data from a player's weakness profile,
collected from the analysis of {player_profile["total_games"]} real games.

Your task is NOT to write explanatory text. It is to perform a technical diagnosis
identifying causal patterns behind the detected symptoms.

PLAYER DATA:
{json.dumps(profile_summary, indent=2, ensure_ascii=False)}

INSTRUCTIONS:
1. Analyze the weaknesses and identify whether a root pattern connects them
2. Classify each weakness as: PRIMARY (main cause), SECONDARY (symptom of another), NOISE (low relevance)
3. Determine the Silman study priority based on the root cause
4. Be specific about what the player is NOT perceiving in the positions

Respond ONLY with valid JSON containing both "en" (English) and "pt" (Brazilian Portuguese)
translations of all descriptive text. No text before or after the JSON.

Structural fields (MUST be identical in both languages):
  root_cause.id, weakness_classification[].concept, weakness_classification[].classification,
  study_priority[].concept, study_priority[].silman_chapter, study_priority[].priority_rank,
  confidence

Free-text fields (translate appropriately for each language):
  root_cause.name, root_cause.description, weakness_classification[].reasoning,
  study_priority[].reason, cognitive_pattern

{{
  "en": {{
    "root_cause": {{
      "id": "snake_case_identifier",
      "name": "Name of the identified pattern",
      "description": "Precise technical description of the central cognitive/strategic problem"
    }},
    "weakness_classification": [
      {{
        "concept": "detection_key",
        "classification": "PRIMARY|SECONDARY|NOISE",
        "reasoning": "Why this classification"
      }}
    ],
    "study_priority": [
      {{
        "concept": "detection_key",
        "silman_chapter": 0,
        "priority_rank": 1,
        "reason": "Why study this first"
      }}
    ],
    "cognitive_pattern": "Description of the thinking pattern the player must change",
    "confidence": "HIGH|MEDIUM|LOW"
  }},
  "pt": {{
    "root_cause": {{
      "id": "snake_case_identifier",
      "name": "Nome do padrão identificado",
      "description": "Descrição técnica precisa do problema cognitivo/estratégico central"
    }},
    "weakness_classification": [
      {{
        "concept": "detection_key",
        "classification": "PRIMARY|SECONDARY|NOISE",
        "reasoning": "Por que essa classificação"
      }}
    ],
    "study_priority": [
      {{
        "concept": "detection_key",
        "silman_chapter": 0,
        "priority_rank": 1,
        "reason": "Por que estudar isso primeiro"
      }}
    ],
    "cognitive_pattern": "Descrição do padrão de pensamento que o jogador deve mudar",
    "confidence": "HIGH|MEDIUM|LOW"
  }}
}}
"""

    # Chamada à API com retry em erros transitórios (rate limit, 5xx, conexão)
    response = None
    last_error = None
    for attempt in range(_MAX_RETRIES):
        try:
            response = client.messages.create(
                model=ANTHROPIC_MODEL,
                max_tokens=ANTHROPIC_MAX_TOKENS,
                messages=[{"role": "user", "content": prompt}],
            )
            break
        except (anthropic.RateLimitError, anthropic.APIConnectionError,
                anthropic.InternalServerError) as e:
            last_error = e
            if attempt < _MAX_RETRIES - 1:
                time.sleep(_RETRY_BASE_DELAY * (2 ** attempt))
    if response is None:
        raise RuntimeError(
            f"Falha ao chamar a API da Anthropic após {_MAX_RETRIES} tentativas: {last_error}"
        )

    # Extrai o texto da resposta, validando que há um bloco de texto.
    # (blocos de texto têm .text como string; blocos de tool_use não.)
    text_blocks = [t for b in response.content
                   if isinstance((t := getattr(b, "text", None)), str)]
    if not text_blocks:
        raise ValueError("Resposta da IA não contém nenhum bloco de texto.")
    raw = text_blocks[0]

    diagnosis = _extract_json(raw)

    if not isinstance(diagnosis, dict) or not diagnosis:
        raise ValueError("Diagnóstico da IA tem formato inesperado (não é um objeto JSON).")

    # Enrich both language sections with Silman metadata (page numbers, descriptions)
    for lang_data in diagnosis.values():
        if not isinstance(lang_data, dict):
            continue
        for item in lang_data.get("study_priority", []):
            concept_key = item.get("concept")
            if concept_key in silman_concepts:
                sc = silman_concepts[concept_key]
                item["silman_name"] = sc.get("name")
                item["silman_page"] = sc.get("silman_page")
                item["silman_description"] = sc.get("description")

    return diagnosis
