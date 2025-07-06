from typing import Dict, List, Optional
import json
from dataclasses import dataclass
from pathlib import Path
import os
from openai import OpenAI

@dataclass
class SceneObject:
    type: str
    position: str
    attributes: Dict[str, str]
    relationships: List[Dict[str, str]]

@dataclass
class ScenePlan:
    objects: List[SceneObject]
    lighting: Dict[str, str]
    style: str
    constraints: List[Dict[str, str]]

class PlannerAgent:
    """Agent responsible for planning scene construction from natural language instructions."""
    
    def __init__(self, config=None):
        """Initialize the planner agent."""
        self.config = config or {}
        self.model = self.config.get('agents', {}).get('planner_model', 'qwen-plus')
        self.api_key = self.config.get('api', {}).get('api_key', 'sk-e4beeb344fee48cd98a6d2b600fe15fa')
        self.base_url = self.config.get('api', {}).get('base_url', 'https://dashscope.aliyuncs.com/compatible-mode/v1')
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
    
    def _load_prompts(self):
        """Load prompt templates from file."""
        prompt_path = Path(__file__).parent.parent / "utils" / "prompts.py"
        # TODO: Implement prompt loading
    
    def _parse_instruction(self, instruction: str) -> Dict:
        """Parse natural language instruction into structured format."""
        messages = [
            {
                "role": "system",
                "content": """You are an expert 3D scene planner. Your task is to output a JSON object that describes a scene plan.
The JSON must strictly follow this format:
{
    "objects": [
        {
            "type": "string",
            "position": "string",
            "attributes": {
                "color": "string",
                "material": "string",
                "scale": {"x": float, "y": float, "z": float}
            },
            "relationships": [
                {
                    "type": "string",
                    "target": "string",
                    "offset": float
                }
            ]
        }
    ],
    "lighting": {
        "type": "string",
        "position": {"x": float, "y": float, "z": float},
        "energy": float,
        "color": [float, float, float]
    },
    "style": "string",
    "constraints": [
        {
            "type": "string",
            "value": "string"
        }
    ]
}"""
            },
            {
                "role": "user",
                "content": f"""Create a scene plan for this instruction: {instruction}

Remember to output ONLY the JSON object, nothing else."""
            }
        ]
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature
            )
            
            # Get the response content
            content = response.choices[0].message.content.strip()
            
            # Try to find JSON in the response
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                content = json_match.group(0)
            
            # Parse JSON
            try:
                return json.loads(content)
            except json.JSONDecodeError as e:
                print(f"Raw API response: {content}")
                print(f"JSON parse error: {str(e)}")
                raise ValueError("Failed to parse Qwen response as JSON")
                
        except Exception as e:
            print(f"API call error: {str(e)}")
            raise ValueError(f"Failed to get response from Qwen API: {str(e)}")
    
    def _validate_plan(self, plan: Dict) -> bool:
        """Validate the generated plan meets requirements."""
        required_keys = ["objects", "lighting", "style"]
        return all(key in plan for key in required_keys)
    
    def plan(self, user_input, reflection=None):
        """Generate a scene plan from natural language instruction."""
        prompt = f"""
你是一个3D场景推理与代码生成专家。请分两步完成任务：
1. 先详细推理用户需求，输出推理链（包括物体数量、类型、关系、空间布局、物理约束等）。
2. 再根据推理链，生成可直接在Blender中运行的Python脚本。
输出格式如下：
推理链:
...
Blender脚本:
```python
# 这里是完整代码
```
用户需求：{user_input}
"""
        if reflection:
            prompt += f"\n请注意结合以下历史反思，避免重复犯错：\n{reflection}\n"
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}]
        )
        content = response.choices[0].message.content
        reasoning, script = "", ""
        if "Blender脚本:" in content:
            parts = content.split("Blender脚本:")
            reasoning = parts[0].replace("推理链:", "").strip()
            if "```python" in parts[1]:
                script = parts[1].split("```python")[-1].split("```", 1)[0].strip()
            else:
                script = parts[1].strip()
        else:
            script = content
        return reasoning, script
    
    def refine_plan(self, plan: ScenePlan, feedback: str) -> ScenePlan:
        """Refine existing plan based on feedback."""
        # TODO: Implement plan refinement
        pass 