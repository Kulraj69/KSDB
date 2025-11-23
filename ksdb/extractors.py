from typing import List, Dict, Any
import warnings

# Suppress warnings from transformers/torch
warnings.filterwarnings("ignore")

try:
    from gliner import GLiNER
except ImportError:
    GLiNER = None

class GraphExtractor:
    def __init__(self, model_name: str = "urchade/gliner_small-v2.1"):
        self.enabled = False
        if GLiNER:
            try:
                print(f"Loading GLiNER model: {model_name}...")
                self.model = GLiNER.from_pretrained(model_name)
                self.enabled = True
                print("GLiNER loaded successfully.")
            except Exception as e:
                print(f"Failed to load GLiNER: {e}")
        else:
            print("GLiNER not installed. Auto-extraction disabled.")

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
