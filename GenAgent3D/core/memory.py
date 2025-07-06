import os
import json
import numpy as np
from typing import Dict, List, Optional
import faiss
import dataclasses
from dataclasses import asdict

class SceneMemory:
    """Memory system for storing and retrieving scene generation experiences."""
    
    def __init__(self, max_history: int = 1000, 
                 similarity_threshold: float = 0.8):
        """Initialize the memory system."""
        self.max_history = max_history
        self.similarity_threshold = similarity_threshold
        
        # Initialize FAISS index with simple bag-of-words embedding
        self.dimension = 100  # Fixed dimension for simple embeddings
        self.index = faiss.IndexFlatL2(self.dimension)
        
        # Load existing memories
        self.memories = self._load_memories()
        
        # Build index from existing memories
        if self.memories:
            embeddings = [self._simple_embed(m["instruction"]) for m in self.memories]
            self.index.add(np.array(embeddings).astype('float32'))
    
    def _simple_embed(self, text: str) -> np.ndarray:
        """Create a simple embedding using character frequencies."""
        # Create a simple embedding based on character frequencies
        embedding = np.zeros(self.dimension)
        for i, char in enumerate(text):
            if i < self.dimension:
                embedding[i] = ord(char) / 255.0  # Normalize to [0,1]
        return embedding
    
    def _load_memories(self) -> List[Dict]:
        """Load memories from disk."""
        memory_file = "data/memories.json"
        if os.path.exists(memory_file):
            with open(memory_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    
    def _save_memories(self):
        """Save memories to disk."""
        os.makedirs("data", exist_ok=True)
        with open("data/memories.json", 'w', encoding='utf-8') as f:
            json.dump(self.memories, f, ensure_ascii=False, indent=2)
    
    def add_memory(self, instruction: str, scene_plan: Dict, verification_result: Dict):
        """Add a new memory to the system."""
        # Create memory entry
        if dataclasses.is_dataclass(scene_plan):
            scene_plan = asdict(scene_plan)
        memory = {
            "instruction": instruction,
            "scene_plan": scene_plan,
            "verification_result": verification_result
        }
        
        # Add to memories list
        self.memories.append(memory)
        
        # Update FAISS index
        embedding = self._simple_embed(instruction)
        self.index.add(np.array([embedding]).astype('float32'))
        
        # Trim if exceeding max history
        if len(self.memories) > self.max_history:
            self.memories = self.memories[-self.max_history:]
            # Rebuild index
            embeddings = [self._simple_embed(m["instruction"]) for m in self.memories]
            self.index = faiss.IndexFlatL2(self.dimension)
            self.index.add(np.array(embeddings).astype('float32'))
        
        # Save to disk
        self._save_memories()
    
    def search_similar(self, instruction: str, k: int = 5) -> List[Dict]:
        """Search for similar past experiences."""
        # Get query embedding
        query_embedding = self._simple_embed(instruction)
        
        # Search in FAISS index
        distances, indices = self.index.search(
            np.array([query_embedding]).astype('float32'), 
            min(k, len(self.memories))
        )
        
        # Filter by similarity threshold
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx < len(self.memories) and dist < self.similarity_threshold:
                results.append(self.memories[idx])
        
        return results
    
    def analyze_patterns(self) -> Dict:
        """Analyze patterns in successful scene generations."""
        if not self.memories:
            return {
                "common_objects": [],
                "common_styles": [],
                "common_relationships": []
            }
        
        # Collect statistics
        objects = {}
        styles = {}
        relationships = {}
        
        for memory in self.memories:
            scene_plan = memory["scene_plan"]
            
            # Count objects
            for obj in scene_plan["objects"]:
                obj_type = obj["type"]
                objects[obj_type] = objects.get(obj_type, 0) + 1
            
            # Count styles
            if "style" in scene_plan:
                style = scene_plan["style"]
                styles[style] = styles.get(style, 0) + 1
            
            # Count relationships
            for rel in scene_plan.get("relationships", []):
                rel_type = rel["type"]
                relationships[rel_type] = relationships.get(rel_type, 0) + 1
        
        # Sort by frequency
        def sort_by_freq(d):
            return sorted(d.items(), key=lambda x: x[1], reverse=True)
        
        return {
            "common_objects": sort_by_freq(objects),
            "common_styles": sort_by_freq(styles),
            "common_relationships": sort_by_freq(relationships)
        } 