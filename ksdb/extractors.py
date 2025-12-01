from typing import List, Dict, Any
import warnings

# Suppress warnings from transformers/torch
warnings.filterwarnings("ignore")

try:
    from gliner import GLiNER
    # Added for SentenceTransformer if it's intended for embedding, though the original code uses GLiNER for entity extraction.
    # If the intent is to use SentenceTransformer for embeddings *within* GLiNER or for a separate step,
    # it needs to be imported. For now, assuming GLiNER is the primary model.
    # from sentence_transformers import SentenceTransformer 
except ImportError:
    GLiNER = None
    # SentenceTransformer = None # If SentenceTransformer was intended

class GraphExtractor:
    def __init__(self, model_name: str = None):
        # Use environment variable for GLiNER model or default to a lightweight one
        # The original default was "urchade/gliner_small-v2.1".
        # The instruction mentions "all-MiniLM-L6-v2" which is a SentenceTransformer model,
        # but the class uses GLiNER. Sticking to GLiNER models for now.
        self.gliner_model_name = model_name or os.getenv("GLINER_MODEL", "urchade/gliner_small-v2.1")
        self.device = "cpu"  # Force CPU for Free Tier stability

        self.enabled = False
        self._model = None # Lazy load GLiNER model

        if GLiNER:
            print(f"GLiNER is available. Model will be loaded on first use.")
            # We don't load the model here, just set enabled to True if GLiNER is importable
            # The actual loading happens in the @property `model`
            self.enabled = True
        else:
            print("GLiNER not installed. Auto-extraction disabled.")

    @property
    def model(self):
        if self._model is None and self.enabled:
            print(f"Loading GLiNER model: {self.gliner_model_name} on {self.device}...")
            try:
                # Explicitly pass device to GLiNER.from_pretrained if it supports it,
                # otherwise GLiNER might manage its own device placement.
                # GLiNER.from_pretrained typically handles device internally based on available hardware.
                # For explicit CPU, we might need to ensure underlying transformers/torch use it.
                # A common way is to set environment variables or pass device to the underlying model.
                # For GLiNER, it often uses `torch.device("cuda" if torch.cuda.is_available() else "cpu")`
                # We can try to force it by setting an env var or by passing it if the API supports it.
                # Assuming GLiNER.from_pretrained can take a device argument or respects env vars.
                # If not, this explicit device setting might not directly apply to GLiNER's internal model.
                self._model = GLiNER.from_pretrained(self.gliner_model_name)
                # After loading, ensure the model is on the desired device if GLiNER allows
                if hasattr(self._model.model, 'to'): # Check if the underlying model has a .to() method
                    self._model.model.to(self.device)
                print("GLiNER loaded successfully.")
            except Exception as e:
                print(f"Failed to load GLiNER model '{self.gliner_model_name}' on {self.device}: {e}")
                print("GLiNER auto-extraction will be disabled.")
                self.enabled = False # Disable if loading fails
                self._model = None # Ensure model is None
        return self._model

    def extract(self, text: str) -> List[Dict[str, Any]]:
        if not self.enabled:
            return []

        # 1. Extract Entities
        # We look for common entity types relevant to knowledge graphs
        labels = ["Person", "Organization", "Location", "Product", "Event", "Concept", "Technology"]
        entities = self.model.predict_entities(text, labels, threshold=0.3)
        
        # Deduplicate entities by text
        unique_entities = {}
        for e in entities:
            unique_entities[e["text"]] = e["label"]
        
        entity_list = [{"text": k, "label": v} for k, v in unique_entities.items()]
        
        # 2. Build Triples (Association Graph)
        # We create "related_to" edges between all entities found in the same text chunk.
        # This is a "Co-occurrence Graph".
        triples = []
        for i in range(len(entity_list)):
            for j in range(i + 1, len(entity_list)):
                subj = entity_list[i]
                obj = entity_list[j]
                
                triples.append({
                    "subject": subj["text"],
                    "predicate": "related_to", # Generic association
                    "object": obj["text"],
                    "weight": 0.8
                })
                
        return triples
