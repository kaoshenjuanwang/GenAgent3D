import bpy
from math import radians

# 清除现有对象
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# 创建三个不同尺寸的箱子
box_sizes = [(2, 2, 1), (1.5, 1.5, 0.8), (1, 1, 0.5)]  # 分别为大、中、小箱子的尺寸
box_names = ["Large_Box", "Medium_Box", "Small_Box"]

boxes = []
for i, size in enumerate(box_sizes):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0))
    box = bpy.context.object
    box.name = box_names[i]
    box.scale = size
    boxes.append(box)

large_box = boxes[0]
medium_box = boxes[1]
small_box = boxes[2]

# 设置堆叠位置
z_large = large_box.dimensions.z / 2
z_medium = z_large + medium_box.dimensions.z / 2
z_small = z_medium + small_box.dimensions.z / 2

large_box.location = (0, 0, z_large)
medium_box.location = (0, 0, z_medium)
small_box.location = (0, 0, z_small)

# 添加光源（方向光）
light_data = bpy.data.lights.new(name="Directional_Light", type='SUN')
light_data.energy = 1.5
light_data.shadow_soft_size = 0.1
light_object = bpy.data.objects.new(name="Directional_Light", object_data=light_data)
bpy.context.collection.objects.link(light_object)
light_object.location = (5, -5, 10)

# 调整相机视角
camera = bpy.data.objects["Camera"]
camera.location = (6, -6, 4)
camera.rotation_euler = (radians(45), 0, radians(45))

# 设置渲染引擎和采样数
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.samples = 64

# 设置世界背景颜色
world = bpy.data.worlds["World"]
world.use_nodes = True
bg_node = world.node_tree.nodes["Background"]
bg_node.inputs["Color"].default_value = (0.1, 0.1, 0.1, 1)  # 深灰色背景