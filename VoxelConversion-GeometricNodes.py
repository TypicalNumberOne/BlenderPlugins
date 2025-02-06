bl_info = {
    "name": "VoxelConversion-GeometricNodes",
    "blender": (3, 0, 0),
    "category": "Object",
    "description": "在物体体积内栅格化分布立方体",
}

import bpy
from bpy.props import FloatProperty, BoolProperty
from mathutils import Vector

class OBJECT_OT_add_volume_grid(bpy.types.Operator):
    """在物体体积内部实例化立方体"""
    bl_idname = "object.add_volume_grid"
    bl_label = "体素转换"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        spacing = scene.volume_grid_size  # 获取 UI 面板中的 spacing
        scale = scene.volume_grid_size  # 获取 UI 面板中的 scale
        realize_instances = scene.volume_grid_realize  # 获取是否需要实现实例
        
        # 筛选出所有选中的网格物体
        selected_meshes = [obj for obj in context.selected_objects if obj.type == 'MESH']
        if not selected_meshes:
            self.report({'WARNING'}, "请先选择至少一个网格物体！")
            return {'CANCELLED'}

        # 对每个网格物体进行操作
        for obj in selected_meshes:
            # 在这里添加你转换的代码，例如添加 Modifier 等操作
            print(f"正在处理: {obj.name}")
            # obj = context.object
            # if obj is None or obj.type != 'MESH':
            #     self.report({'WARNING'}, "请先选择一个网格物体！")
            #     return {'CANCELLED'}

            # 添加几何节点修饰器
            mod = obj.modifiers.new(name="VolumeGridInstance", type='NODES')
            node_group = mod.node_group
            if node_group is None:
                node_group = bpy.data.node_groups.new(name="VolumeGridInstance", type='GeometryNodeTree')
                mod.node_group = node_group

            # 清空节点
            for node in node_group.nodes:
                node_group.nodes.remove(node)

            # 创建输入节点
            node_group.inputs.new("NodeSocketGeometry", "Mesh")
            node_group.inputs.new("NodeSocketFloat", "Spacing")
            node_group.inputs.new("NodeSocketFloat", "Scale")
            # **确保 spacing 和 scale 变量有值**
            print(f"⚙️ 设置 Spacing: {spacing}, Scale: {scale}")  # 调试
            # **修改 node_group.inputs 的默认值**
            node_group.inputs["Spacing"].default_value = spacing        # 设置默认值
            node_group.inputs["Scale"].default_value = scale            # 设置默认值
            # 强制刷新接口
            node_group.interface_update(context)

            input_node = node_group.nodes.new(type='NodeGroupInput')
            input_node.location = (-400, 0)

            # 创建输出节点
            output_node = node_group.nodes.new(type='NodeGroupOutput')
            output_node.location = (400, 0)
            node_group.outputs.new("NodeSocketGeometry", "Geometry")

            # "Mesh to Volume" (网格转体积)
            mesh_to_volume = node_group.nodes.new(type='GeometryNodeMeshToVolume')
            mesh_to_volume.location = (-200, 100)

            # "Distribute Points in Volume" (在体积内部分布点)
            distribute_points = node_group.nodes.new(type='GeometryNodeDistributePointsInVolume') #在体积内部分布点
            distribute_points.location = (0, 100)
            # 设置分布模式为“GRID”
            distribute_points.mode = 'DENSITY_GRID'

            # "Instance on Points" (在点上实例化)
            instance_on_points = node_group.nodes.new(type='GeometryNodeInstanceOnPoints')
            instance_on_points.location = (200, 100)

            # "Cube" (实例立方体)
            cube = node_group.nodes.new(type='GeometryNodeMeshCube')
            cube.location = (0, -100)

            # "Set Material" (设置材质)
            set_material = node_group.nodes.new(type='GeometryNodeSetMaterial')
            set_material.location = (400, 100)

            # 连接节点
            links = node_group.links
            links.new(input_node.outputs["Mesh"], mesh_to_volume.inputs["Mesh"]) # 组输入(几何数据)->网格转体积(网格)
            links.new(mesh_to_volume.outputs["Volume"], distribute_points.inputs["Volume"]) # 网格转体积(体积)->在体积内部分布点(体积)
            links.new(distribute_points.outputs["Points"], instance_on_points.inputs["Points"]) # 在体积内部分布点(点)->(点)
            links.new(cube.outputs["Mesh"], instance_on_points.inputs["Instance"]) # 正方体(网格) -> 实例化于点上(实例)
            links.new(instance_on_points.outputs["Instances"], set_material.inputs["Geometry"]) # 实例化于点上(实例) -> 设置材质(几何数据)
            # 设置材质(几何数据) -> 组输出(几何数据)
            # 根据勾选状态判断是否插入 Realize Instances 节点
            if realize_instances:
                realize_node = node_group.nodes.new(type='GeometryNodeRealizeInstances')
                realize_node.location = (500, 100)
                links.new(set_material.outputs["Geometry"], realize_node.inputs["Geometry"])
                links.new(realize_node.outputs["Geometry"], output_node.inputs["Geometry"])
            else:
                links.new(set_material.outputs["Geometry"], output_node.inputs["Geometry"])

            # 连接 Value 控制
            links.new(input_node.outputs["Spacing"], distribute_points.inputs["Spacing"])
            links.new(input_node.outputs["Scale"], instance_on_points.inputs["Scale"])

            # 通过 Modifier 属性设置实际数值，使 Geometry Nodes 计算时使用正确的参数
            mod[node_group.inputs["Spacing"].identifier] = spacing
            mod[node_group.inputs["Scale"].identifier] = scale

            # 继承物体材质
            if obj.material_slots:
                set_material.inputs["Material"].default_value = obj.material_slots[0].material
        return {'FINISHED'}

    def invoke(self, context, event):
        """ 允许在 UI 面板中修改 spacing 和 scale """
        return context.window_manager.invoke_props_dialog(self)


class OBJECT_PT_volume_grid_instance(bpy.types.Panel):
    """面板 UI"""
    bl_label = "体积内实例化"
    bl_idname = "OBJECT_PT_volume_grid_instance"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = '工具'

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        # 添加属性调整控件
        layout.prop(scene, "volume_grid_size", text="大小")
        layout.prop(scene, "volume_grid_realize", text="实现实例")
        layout.separator()

        # 添加操作按钮
        layout.operator("object.add_volume_grid", text="体积内实例化立方体")

def register():
    bpy.utils.register_class(OBJECT_OT_add_volume_grid)
    bpy.utils.register_class(OBJECT_PT_volume_grid_instance)
    bpy.types.Scene.volume_grid_size = FloatProperty(
    name="大小",
    description="控制点的分布间隔和立方体缩放",
    default=0.5,
    min=0.01,
    max=100.0,
    )
    bpy.types.Scene.volume_grid_realize = BoolProperty(
        name="实现实例",
        description="连接实现实例的节点",
        default=False,
    )

def unregister():
    bpy.utils.unregister_class(OBJECT_OT_add_volume_grid)
    bpy.utils.unregister_class(OBJECT_PT_volume_grid_instance)
    del bpy.types.Scene.volume_grid_size
    del bpy.types.Scene.volume_grid_realize

if __name__ == "__main__":
    register()
