import os

def generate_blender_script(task_desc, filename="gen_scene.py", llm_client=None, model="qwen-plus"):
    prompt = f"""
你是一个Blender 3D场景脚本生成专家。请根据如下用户需求，生成一份可直接在Blender中运行的Python脚本，要求：
- 场景物体不重叠、不遮挡，布局合理，光照充足，相机能看到所有物体。
- 每个物体有明显的颜色和尺寸。
- 包含地面、后墙、主要物体、光源、相机设置和渲染设置。
- 只输出完整的Python代码，不要有解释说明。

用户需求：{task_desc}
"""
    script = None
    if llm_client is not None:
        response = llm_client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}]
        )
        script = response.choices[0].message.content
    if not script:
        script = mini_blender_script_template(task_desc)
    with open(filename, "w", encoding="utf-8") as f:
        f.write(script)
    print(f"Blender 脚本已保存到 {filename}")
    return filename

def mini_blender_script_template(task_desc):
    return f'''
import bpy
import math

# 清空场景
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

# 地面
bpy.ops.mesh.primitive_plane_add(size=10, location=(0, 0, 0))
ground = bpy.context.active_object
ground.name = "Ground"

# 沙发
bpy.ops.mesh.primitive_cube_add(size=2, location=(0, -1, 1))
sofa = bpy.context.active_object
sofa.name = "Sofa"
sofa.scale = (2, 1, 1)
mat_sofa = bpy.data.materials.new(name="SofaMat")
mat_sofa.diffuse_color = (0.5, 0.5, 0.5, 1)
sofa.data.materials.append(mat_sofa)

# 茶几
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 1, 0.5))
table = bpy.context.active_object
table.name = "CoffeeTable"
table.scale = (1, 0.5, 0.5)
mat_table = bpy.data.materials.new(name="TableMat")
mat_table.diffuse_color = (0.9, 0.9, 0.9, 1)
table.data.materials.append(mat_table)

# 电视
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 3, 0.6))
tv = bpy.context.active_object
tv.name = "TV"
tv.scale = (1.5, 0.1, 0.6)
mat_tv = bpy.data.materials.new(name="TVMat")
mat_tv.diffuse_color = (0.1, 0.1, 0.1, 1)
tv.data.materials.append(mat_tv)

# 后墙
bpy.ops.mesh.primitive_cube_add(size=8, location=(0, -4, 1.5))
back_wall = bpy.context.active_object
back_wall.scale = (4, 0.1, 1.5)
mat_wall = bpy.data.materials.new(name="WallMat")
mat_wall.diffuse_color = (1, 1, 1, 1)
back_wall.data.materials.append(mat_wall)

# 光源
bpy.ops.object.light_add(type='SUN', location=(0, 0, 5))
sun = bpy.context.active_object
sun.data.energy = 10

# 相机
if "Camera" not in bpy.data.objects:
    bpy.ops.object.camera_add(location=(0, -8, 3))
    camera = bpy.context.active_object
    camera.name = "Camera"
else:
    camera = bpy.data.objects["Camera"]
camera.location = (0, -8, 3)
camera.data.angle = math.radians(60)
camera.rotation_euler = (math.radians(75), 0, 0)
bpy.context.scene.camera = camera

# 渲染设置
bpy.context.scene.render.engine = 'CYCLES'
bpy.context.scene.cycles.samples = 64
bpy.context.scene.render.resolution_x = 800
bpy.context.scene.render.resolution_y = 600
bpy.context.scene.render.filepath = "//gen_scene.png"
bpy.ops.render.render(write_still=True)
print("渲染完成，图片保存在Blender项目目录下 gen_scene.png")
''' 