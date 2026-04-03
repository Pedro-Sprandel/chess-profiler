import json
import anthropic
from config import ANTHROPIC_API_KEY


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
Você é um analista de xadrez especializado em diagnóstico pedagógico estratégico.

Abaixo estão dados quantitativos brutos do perfil de fraquezas de um jogador,
coletados a partir da análise de {player_profile["total_games"]} partidas reais.

Sua tarefa NÃO é escrever um texto explicativo. É realizar um diagnóstico técnico
identificando padrões causais por trás dos sintomas detectados.

DADOS DO JOGADOR:
{json.dumps(profile_summary, indent=2, ensure_ascii=False)}

INSTRUÇÕES:
1. Analise as fraquezas e identifique se existe um padrão raiz que as conecta
2. Classifique cada fraqueza como: PRIMARY (causa principal), SECONDARY (sintoma de outra), NOISE (pouco relevante)
3. Determine a prioridade de estudo no Silman com base na causa raiz
4. Seja específico sobre o que o jogador NÃO está percebendo nas posições

Responda APENAS com JSON válido, sem texto antes ou depois:

{{
  "root_cause": {{
    "id": "identificador_snake_case",
    "name": "Nome do padrão identificado",
    "description": "Descrição técnica precisa do problema cognitivo/estratégico central"
  }},
  "weakness_classification": [
    {{
      "concept": "detection_key do conceito",
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
"""

    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}]
    )

    raw = response.content[0].text.strip()

    # Remove markdown code fences se presentes
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    diagnosis = json.loads(raw)

    # Enriquece o resultado com dados do Silman
    for item in diagnosis.get("study_priority", []):
        concept_key = item.get("concept")
        if concept_key in silman_concepts:
            sc = silman_concepts[concept_key]
            item["silman_name"] = sc.get("name")
            item["silman_page"] = sc.get("silman_page")
            item["silman_description"] = sc.get("description")

    return diagnosis
