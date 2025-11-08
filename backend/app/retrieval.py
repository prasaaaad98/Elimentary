from typing import List
from math import sqrt
from sqlalchemy.orm import Session

from app.models import DocumentChunk
from app.llm import embed_texts
import logging

logger = logging.getLogger(__name__)


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """
    Compute cosine similarity between two vectors.
    Returns a value between -1 and 1, where 1 means identical.
    """
    if len(a) != len(b):
        return 0.0
    
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sqrt(sum(x * x for x in a))
    norm_b = sqrt(sum(x * x for x in b))
    
    if norm_a == 0 or norm_b == 0:
        return 0.0
    
    return dot / (norm_a * norm_b)


def retrieve_relevant_chunks(
    db: Session,
    document_id: int,
    question: str,
    top_k: int = 10,
) -> List[str]:
    """
    Given a question and a document_id, retrieve the top_k most relevant text chunks
    using cosine similarity over embeddings, with keyword-based boosting for better results.
    Returns a list of chunk texts.
    """
    if not question.strip():
        return []
    
    try:
        # 1) Expand question for better retrieval (especially for management questions)
        question_lower = question.lower()
        expanded_question = question
        
        # For management-related questions, expand with synonyms and related terms
        if any(keyword in question_lower for keyword in ["reason", "why", "explain", "management", "factor"]):
            expanded_question = (
                f"{question} "
                "management discussion analysis MD&A explanation rationale strategy outlook risk opportunity "
                "performance factors growth challenges initiatives"
            )
        elif any(keyword in question_lower for keyword in ["revenue", "profit", "financial"]):
            expanded_question = (
                f"{question} "
                "financial statement balance sheet profit loss revenue income expense asset liability"
            )
        
        # Embed the expanded question for better retrieval
        q_vecs = embed_texts([expanded_question])
        if not q_vecs or len(q_vecs) == 0:
            logger.warning("Failed to embed question for document %s", document_id)
            return []
        q_vec = q_vecs[0]
        
        # 2) Load all chunks for this document
        chunks = (
            db.query(DocumentChunk)
            .filter(DocumentChunk.document_id == document_id)
            .all()
        )
        
        if not chunks:
            logger.info("No chunks found for document %s", document_id)
            return []
        
        # 3) Detect question type for keyword boosting
        question_lower = question.lower()
        is_management_question = any(keyword in question_lower for keyword in [
            "management", "reason", "explain", "why", "cause", "factor", "discussion",
            "analysis", "outlook", "strategy", "risk", "opportunity", "challenge"
        ])
        is_financial_question = any(keyword in question_lower for keyword in [
            "revenue", "profit", "asset", "liability", "cash flow", "margin", "ratio"
        ])
        
        # 4) Compute similarity scores with keyword boosting
        scored: list[tuple[float, str, int]] = []  # (score, text, page_number)
        for ch in chunks:
            if not ch.embedding:
                continue
            
            emb = ch.embedding  # JSON column stores list directly
            if not isinstance(emb, list) or len(emb) == 0:
                continue
            
            try:
                # Base similarity score
                base_score = _cosine_similarity(q_vec, emb)
                
                # Keyword-based boosting
                chunk_text_lower = ch.text.lower()
                boost = 0.0
                
                # Boost MD&A/management discussion chunks for management questions
                if is_management_question:
                    mda_keywords = [
                        "management discussion", "management's discussion", "mda", "md&a",
                        "management analysis", "outlook", "strategy", "risk factor",
                        "key factor", "reason", "explanation", "performance", "growth",
                        "challenge", "opportunity", "initiative"
                    ]
                    if any(keyword in chunk_text_lower for keyword in mda_keywords):
                        boost += 0.15  # Significant boost for MD&A content
                
                # Boost financial statement chunks for financial questions
                if is_financial_question:
                    financial_keywords = [
                        "statement of profit", "balance sheet", "cash flow",
                        "financial position", "revenue", "profit", "asset", "liability"
                    ]
                    if any(keyword in chunk_text_lower for keyword in financial_keywords):
                        boost += 0.1
                
                # Slight penalty for audit-only chunks when asking management questions
                if is_management_question and "auditor" in chunk_text_lower and "independent auditor" in chunk_text_lower:
                    boost -= 0.1
                
                final_score = base_score + boost
                scored.append((final_score, ch.text, ch.page_number or 0))
            except Exception as e:
                logger.warning("Error computing similarity for chunk %s: %s", ch.id, e)
                continue
        
        if not scored:
            logger.info("No chunks with valid embeddings for document %s", document_id)
            return []
        
        # 5) Sort by final score descending
        scored.sort(key=lambda x: x[0], reverse=True)
        
        # 6) Return top_k texts (deduplicate very similar chunks)
        result_texts = []
        seen_texts = set()
        for score, text, page_num in scored:
            # Simple deduplication: skip if very similar text already included
            text_snippet = text[:100].lower().strip()
            if text_snippet not in seen_texts:
                result_texts.append(text)
                seen_texts.add(text_snippet)
                if len(result_texts) >= top_k:
                    break
        
        logger.info(
            "Retrieved %d chunks for document %s (top similarity: %.4f, question type: %s)",
            len(result_texts),
            document_id,
            scored[0][0] if scored else 0.0,
            "management" if is_management_question else "financial" if is_financial_question else "general"
        )
        return result_texts
        
    except Exception as e:
        logger.exception("Error retrieving chunks for document %s: %s", document_id, e)
        return []

