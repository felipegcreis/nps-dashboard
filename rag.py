import os
import pickle
import numpy as np

EMBEDDINGS_CACHE = "embeddings_cache.pkl"
EMBEDDING_MODEL = "gemini-embedding-001"

CSAT_LABELS = {
    'CS_Sis': 'Sistema',
    'CS_Sup': 'Suporte',
    'CS_Aca': 'Academy',
    'CS_Com': 'Comercial',
    'CS_Cld': 'Cloud',
}


def build_document(row: dict) -> str:
    """Cria representação textual rica de uma resposta da pesquisa."""
    parts = []
    parts.append(f"Produto: {row.get('Produto', 'N/A')}")
    parts.append(f"Infra: {row.get('Infra', 'N/A')}")
    parts.append(f"Cloud: {row.get('Cloud(S/N)', 'N/A')}")
    parts.append(f"NPS: {row.get('NPS_Cl', 'N/A')} (nota {row.get('NPS', 'N/A')})")

    for col, nome in CSAT_LABELS.items():
        val = row.get(col)
        if val and val != 'Não sei Informar':
            parts.append(f"CSAT {nome}: {val}")

    for campo, label in [
        ('Positivos', 'Elogios'),
        ('Melhorias', 'Sugestões de melhoria'),
        ('Uma_Melhoria', 'Principal melhoria'),
    ]:
        val = row.get(campo)
        if val:
            parts.append(f"{label}: {val}")

    return " | ".join(parts)


def _embed_text(client, text: str) -> np.ndarray:
    result = client.models.embed_content(model=EMBEDDING_MODEL, contents=text)
    return np.array(result.embeddings[0].values, dtype=np.float32)


def build_and_cache_index(data: list, client, cache_path: str = EMBEDDINGS_CACHE) -> dict:
    print(f"[RAG] Gerando embeddings para {len(data)} documentos...", flush=True)
    documents = []
    embeddings = []
    for row in data:
        doc_text = build_document(row)
        emb = _embed_text(client, doc_text)
        documents.append({'text': doc_text, 'meta': row})
        embeddings.append(emb)

    index = {'documents': documents, 'matrix': np.array(embeddings, dtype=np.float32)}
    with open(cache_path, 'wb') as f:
        pickle.dump(index, f)
    print(f"[RAG] Cache salvo em '{cache_path}'", flush=True)
    return index


def load_or_build_index(data: list, client, cache_path: str = EMBEDDINGS_CACHE) -> dict:
    if os.path.exists(cache_path):
        print(f"[RAG] Carregando embeddings do cache '{cache_path}'", flush=True)
        with open(cache_path, 'rb') as f:
            return pickle.load(f)
    return build_and_cache_index(data, client, cache_path)


def _cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    return float(np.dot(a, b) / denom) if denom > 0 else 0.0


def retrieve(query: str, client, index: dict, top_k: int = 6) -> list[tuple[float, dict]]:
    """Retorna top_k tuplas (score, doc) ordenadas por relevância."""
    q_emb = _embed_text(client, query)
    matrix = index['matrix']
    scores = (matrix @ q_emb) / (
        np.linalg.norm(matrix, axis=1) * np.linalg.norm(q_emb) + 1e-9
    )
    top_indices = np.argsort(scores)[::-1][:top_k]
    return [(float(scores[i]), index['documents'][i]) for i in top_indices]
