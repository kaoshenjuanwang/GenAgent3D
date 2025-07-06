import os
import yaml
from pathlib import Path
from dotenv import load_dotenv
from agents.planner import PlannerAgent
from agents.executor import ExecutorAgent
from agents.verifier import VerifierAgent
from core.memory import SceneMemory
from core.script_generator import generate_blender_script
from openai import OpenAI
import base64
import re

def load_config():
    """Load configuration from yaml file."""
    config_path = Path(__file__).parent / "config" / "config.yaml"
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def setup_blender():
    """Set up Blender environment."""
    import bpy
    # 设置Blender的Python路径
    blender_path = os.path.dirname(os.path.dirname(bpy.__file__))
    if blender_path not in os.environ["PATH"]:
        os.environ["PATH"] = blender_path + os.pathsep + os.environ["PATH"]

def generate_reasoning_and_script(task_desc, llm_client, model="qwen-plus"):
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
用户需求：{task_desc}
"""
    response = llm_client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}]
    )
    content = response.choices[0].message.content
    reasoning, script = "", ""
    if "Blender脚本:" in content:
        parts = content.split("Blender脚本:")
        reasoning = parts[0].replace("推理链:", "").strip()
        # 提取代码块
        if "```python" in parts[1]:
            script = parts[1].split("```python")[-1].split("```", 1)[0].strip()
        else:
            script = parts[1].strip()
    else:
        script = content
    return reasoning, script

def analyze_image_and_optimize_script(image_path, task_desc, script_content, llm_client, model="qwen-vl-max"):
    with open(image_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode("utf-8")
    prompt = f"""
你是一个3D场景优化专家。请分析下图是否符合如下描述，并给出改进建议（如物体遮挡、布局、光照、相机等）：
描述：{task_desc}
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
    response = llm_client.chat.completions.create(
        model=model,
        messages=messages
    )
    analysis = response.choices[0].message.content
    print("图片分析与建议：\n", analysis)
    # 提取分数
    score = None
    suggestion = ""
    score_match = re.search(r"匹配度分数[：: ]*([0-9]+)", analysis)
    if score_match:
        score = int(score_match.group(1))
    # 提取优化建议代码片段
    suggestion_match = re.search(r"优化建议[：: ]*(?:\n)?([\s\S]*)", analysis)
    if suggestion_match:
        suggestion = suggestion_match.group(1).strip()
    return analysis, score, suggestion

def reflect_on_memory(memory: SceneMemory):
    """
    总结历史所有失败点和优化建议，生成反思内容。
    """
    if not memory.memories:
        return ""
    problems = []
    for m in memory.memories:
        vr = m.get("verification_result", {})
        if isinstance(vr, dict):
            score = vr.get("score") or vr.get("overall_score")
            suggestion = vr.get("suggestion") or vr.get("suggestions")
            if score is not None and score < 85 and suggestion:
                problems.append(f"分数: {score}, 问题/建议: {suggestion}")
    if not problems:
        return ""
    return "请避免以下历史问题：\n" + "\n".join(problems)

def generate_optimized_script(task_desc, last_script, analysis, llm_client, memory=None, model="qwen-plus"):
    """
    基于上次用户需求、上轮Blender脚本和分析结果，结合历史反思，生成新的完整Blender脚本。
    """
    reflection = ""
    if memory is not None:
        reflection = reflect_on_memory(memory)
    prompt = f"""
你是一个3D场景优化与代码生成专家。请根据以下信息，输出可直接在Blender中运行的完整Python脚本：
1. 用户需求：{task_desc}
2. 上一版Blender脚本：
```python
{last_script}
```
3. 上轮图片分析与建议：
{analysis}
{reflection}
请直接输出完整的Blender脚本，务必保证可独立运行。
输出格式：
```python
# 这里是完整代码
```
"""
    response = llm_client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}]
    )
    content = response.choices[0].message.content
    # 提取代码块
    script = ""
    if "```python" in content:
        script = content.split("```python")[-1].split("```", 1)[0].strip()
    else:
        script = content.strip()
    return script

def fix_script_with_error(script: str, error: str, llm_client=None, model="qwen-plus"):
    """
    用LLM根据原脚本和报错信息生成修正版脚本。
    """
    if llm_client is None:
        from openai import OpenAI
        llm_client = OpenAI(
            api_key="sk-e4beeb344fee48cd98a6d2b600fe15fa",
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
    prompt = f"""
你是一个Blender Python脚本修复专家。以下是原始脚本和运行时报错信息，请修正脚本使其能在Blender中无报错运行。
原始脚本：
```python
{script}
```
报错信息：
{error}
请输出修正后的完整Blender脚本。
输出格式：
```python
# 这里是完整代码
```
"""
    response = llm_client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}]
    )
    content = response.choices[0].message.content
    # 提取代码块
    new_script = ""
    if "```python" in content:
        new_script = content.split("```python")[-1].split("```", 1)[0].strip()
    else:
        new_script = content.strip()
    return new_script

def main():
    # 配置Blender路径
    config = {
        "render": {
            "blender_path": r"C:\\Users\\86199\\Desktop\\SceneCraft\\blender-4.4.0-windows-x64\\blender-4.4.0-windows-x64\\blender.exe"
        }
    }
    user_input = input("请输入你的3D场景需求：")
    memory = SceneMemory()
    planner = PlannerAgent(config)
    executor = ExecutorAgent(config)
    verifier = VerifierAgent(config)

    # 1. 规划+生成脚本
    reflection = None
    reasoning, script = planner.plan(user_input, reflection)
    print("推理链:\n", reasoning)
    executor.save_script(script)
    print("Blender 脚本已保存到 gen_scene.py，请在Blender中运行。")
    memory.add_memory(user_input, {"reasoning": reasoning}, {"script": script})

    # 2.5 脚本报错修正循环
    from openai import OpenAI
    llm_client = OpenAI(
        api_key="sk-e4beeb344fee48cd98a6d2b600fe15fa",
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    )
    while True:
        error = input("如有Blender脚本报错请粘贴报错信息（无报错请直接回车）：").strip()
        if not error:
            break
        script = fix_script_with_error(script, error, llm_client)
        executor.save_script(script)
        print("已根据报错优化脚本，请重新在Blender中运行 gen_scene.py。")

    # 3. 反馈-反思-优化循环
    while True:
        image_path = input("请上传渲染图片的本地路径：").strip().strip('"').strip("'")
        score, suggestion, analysis = verifier.verify(image_path, user_input)
        print("图片分析与建议：\n", analysis)
        memory.add_memory(user_input, {"reasoning": reasoning}, {"analysis": analysis, "score": score, "suggestion": suggestion})
        if score is not None and score >= 85:
            print(f"匹配度分数已达{score}，任务完成！")
            break
        # 反思历史问题
        reflection = reflect_on_memory(memory)
        print("历史反思：\n", reflection)
        # 4. 计划优化+生成新脚本
        reasoning, script = planner.plan(user_input, reflection)
        print("优化后推理链:\n", reasoning)
        executor.save_script(script)
        print("已根据优化建议生成并保存新脚本，请重新在Blender中运行 gen_scene.py。")
        memory.add_memory(user_input, {"reasoning": reasoning}, {"script": script})
        # 再次进入报错修正循环
        while True:
            error = input("如有Blender脚本报错请粘贴报错信息（无报错请直接回车）：").strip()
            if not error:
                break
            script = fix_script_with_error(script, error, llm_client)
            executor.save_script(script)
            print("已根据报错优化脚本，请重新在Blender中运行 gen_scene.py。")

if __name__ == "__main__":
    main() 