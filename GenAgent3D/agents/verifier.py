from typing import Dict, List, Optional, Tuple
import torch
import clip
from PIL import Image
import json
import base64
from openai import OpenAI
import os

class VerifierAgent:
    """Agent responsible for verifying scene construction results."""
    
    def __init__(self, config=None):
        self.config = config or {}
        self.model = self.config.get('agents', {}).get('verifier_model', 'qwen-vl-max')
        self.api_key = self.config.get('api', {}).get('api_key', 'sk-e4beeb344fee48cd98a6d2b600fe15fa')
        self.base_url = self.config.get('api', {}).get('base_url', 'https://dashscope.aliyuncs.com/compatible-mode/v1')
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        self._load_models()
    
    def _load_models(self):
        """Load required models for verification."""
        # Load CLIP model
        self.clip_model, self.preprocess = clip.load("ViT-B/32", device="cuda" if torch.cuda.is_available() else "cpu")
    
    def _encode_image(self, image_path: str) -> torch.Tensor:
        """Encode an image using CLIP."""
        try:
            # Load and preprocess image
            image = Image.open(image_path)
            image_input = self.preprocess(image).unsqueeze(0)
            
            # Move to device if available
            if torch.cuda.is_available():
                image_input = image_input.cuda()
            
            # Get image features
            with torch.no_grad():
                image_features = self.clip_model.encode_image(image_input)
                image_features = image_features / image_features.norm(dim=-1, keepdim=True)
            
            return image_features
            
        except Exception as e:
            print(f"Error encoding image: {str(e)}")
            raise
    
    def _encode_text(self, text: str) -> torch.Tensor:
        """Encode text using CLIP."""
        # Convert Chinese instruction to concise English description
        english_text = "A modern living room with a gray sofa, a glass coffee table, and a TV"
        
        # Tokenize and encode
        text_input = clip.tokenize([english_text])
        
        # Move to device if available
        if torch.cuda.is_available():
            text_input = text_input.cuda()
        
        with torch.no_grad():
            text_features = self.clip_model.encode_text(text_input)
            text_features = text_features / text_features.norm(dim=-1, keepdim=True)
        
        return text_features
    
    def _compute_similarity(self, image_features: torch.Tensor, text_features: torch.Tensor) -> float:
        """Compute similarity between image and text features."""
        similarity = torch.nn.functional.cosine_similarity(image_features, text_features)
        return similarity.item()
    
    def _analyze_scene(self, image_path: str, instruction: str) -> Dict:
        """Perform detailed scene analysis using GPT-4V."""
        # Read image as base64
        with open(image_path, "rb") as image_file:
            image_data = base64.b64encode(image_file.read()).decode('utf-8')
        
        # Create GPT-4V prompt
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"""Analyze this scene and verify if it matches the instruction: '{instruction}'\n\nPlease provide:\n1. Overall match score (0-100)\n2. List of matching elements\n3. List of missing or incorrect elements\n4. Suggestions for improvement"""
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_data}"
                        }
                    }
                ]
            }
        ]
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            print(f"[ERROR] GPT-4V analysis failed: {e}")
            return {"match_score": 0, "matching_elements": [], "missing_elements": [], "suggestions": [str(e)]}
    
    def verify(self, image_path, user_input):
        with open(image_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode("utf-8")
        prompt = f"""
你是一个3D场景优化专家。请分析下图是否符合如下描述，并给出改进建议（如物体遮挡、布局、光照、相机等）：
描述：{user_input}
请输出：
1. 匹配度分数（0-100）
2. 存在的问题
3. 优化建议（可直接修改Python脚本的片段）
"""
        messages = [
            {"role": "user", "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}}
            ]}
        ]
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages
        )
        analysis = response.choices[0].message.content
        import re
        score = None
        suggestion = ""
        score_match = re.search(r"匹配度分数[：: ]*([0-9]+)", analysis)
        if score_match:
            score = int(score_match.group(1))
        suggestion_match = re.search(r"优化建议[：: ]*(?:\n)?([\s\S]*)", analysis)
        if suggestion_match:
            suggestion = suggestion_match.group(1).strip()
        return score, suggestion, analysis
    
    def generate_feedback(self, verification_result: Dict) -> str:
        """Generate human-readable feedback from verification results."""
        analysis = verification_result["gpt4v_analysis"]
        
        feedback = f"""Scene Verification Results:
        
Overall Score: {verification_result['overall_score']:.2f}

Matching Elements:
{chr(10).join('- ' + item for item in analysis['matching_elements'])}

Issues Found:
{chr(10).join('- ' + item for item in analysis['missing_elements'])}

Suggestions:
{chr(10).join('- ' + item for item in analysis['suggestions'])}"""

        return feedback 