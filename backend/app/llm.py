import google.generativeai as genai
from app.config import settings
import logging

genai.configure(api_key=settings.GEMINI_API_KEY)
logger = logging.getLogger(__name__)


def call_llm(system_prompt: str, user_prompt: str) -> str:
    model = genai.GenerativeModel(
        model_name=settings.GEMINI_MODEL,
        system_instruction=system_prompt,
    )
    try:
        response = model.generate_content(user_prompt)
        return response.text or ""
    except Exception as e:
        logger.exception("Gemini call failed")
        return f"LLM error: {e}"


def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Use Gemini embedding model to convert a list of texts into embedding vectors.
    Returns a list of vectors (one per text).
    """
    if not texts:
        return []
    
    try:
        model = settings.GEMINI_EMBEDDING_MODEL
        embeddings: list[list[float]] = []
        
        # Process in batches
        batch_size = 100
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            
            try:
                # Call the embedding API
                result = genai.embed_content(
                    model=model,
                    content=batch,
                    task_type="retrieval_document",
                )
                
                # The Google Generative AI SDK returns a dict with key 'embedding' (singular)
                # The value is a list of embedding vectors: [[vec1], [vec2], ...]
                # Each vector is a flat list of floats
                
                batch_embeddings_raw = None
                
                # Extract embeddings from the response
                if isinstance(result, dict):
                    if 'embedding' in result:
                        # This is the correct format: {'embedding': [[...], [...], ...]}
                        batch_embeddings_raw = result['embedding']
                    elif 'embeddings' in result:
                        # Fallback for other formats
                        batch_embeddings_raw = result['embeddings']
                elif hasattr(result, 'embedding'):
                    batch_embeddings_raw = result.embedding
                elif hasattr(result, 'embeddings'):
                    batch_embeddings_raw = result.embeddings
                elif isinstance(result, list):
                    batch_embeddings_raw = result
                else:
                    logger.error(f"Unexpected embedding response format. Type: {type(result)}")
                    raise RuntimeError(f"Unexpected embedding response format: {type(result)}")
                
                if batch_embeddings_raw is None:
                    raise RuntimeError("Could not extract embeddings from response")
                
                # Process each embedding in the batch
                # batch_embeddings_raw should be a list of lists: [[float, ...], [float, ...], ...]
                if not isinstance(batch_embeddings_raw, list):
                    raise RuntimeError(f"Expected list of embeddings, got {type(batch_embeddings_raw)}")
                
                for emb_idx, emb in enumerate(batch_embeddings_raw):
                    try:
                        # Each emb should be a list of floats
                        if isinstance(emb, list):
                            # Convert all elements to float
                            emb_vector = [float(x) for x in emb]
                            if emb_vector:
                                embeddings.append(emb_vector)
                            else:
                                logger.warning(f"Empty embedding vector for batch item {emb_idx}")
                        else:
                            logger.warning(f"Unexpected embedding type at index {emb_idx}: {type(emb)}")
                            continue
                            
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Error converting embedding {emb_idx} to floats: {e}")
                        continue
                    except Exception as e:
                        logger.warning(f"Error processing embedding {emb_idx}: {e}")
                        continue
                
            except Exception as e:
                logger.error(f"Error embedding batch starting at index {i}: {e}")
                # Continue with next batch instead of failing completely
                continue
        
        if len(embeddings) != len(texts):
            logger.warning(
                f"Embedding count mismatch: expected {len(texts)}, got {len(embeddings)}. "
                f"Some embeddings may have failed."
            )
        
        if not embeddings:
            raise RuntimeError("Failed to extract any embeddings from the API response")
        
        return embeddings
        
    except Exception as e:
        logger.exception(f"Embedding failed: {e}")
        raise RuntimeError(f"Failed to embed texts: {e}") from e