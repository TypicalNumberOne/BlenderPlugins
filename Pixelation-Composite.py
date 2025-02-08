bl_info = {
    "name": "Pixelation-Composite",
    "blender": (3, 0, 0),
    "category": "Compositing",
    "description": "一键生成像素化合成节点",
}

import bpy
from bpy.props import FloatProperty

# 操作类：生成像素化合成节点树
class NODE_OT_add_pixelate_composite(bpy.types.Operator):
    """生成像素化合成节点树"""
    bl_idname = "node.add_pixelate_composite"
    bl_label = "一键生成像素化节点"

    def execute(self, context):
        scene = context.scene
        # 确保使用合成节点
        scene.use_nodes = True
        tree = scene.node_tree

        # 清空已有节点
        for node in tree.nodes:
            tree.nodes.remove(node)

        # --- 创建节点 ---
        # 1. Render Layers 节点
        rl = tree.nodes.new(type="CompositorNodeRLayers")
        rl.location = (-800, 0)

        # 2. Blur 节点（默认大小设置为5）
        blur = tree.nodes.new(type="CompositorNodeBlur")
        blur.location = (-600, 0)
        blur.size_x = 5
        blur.size_y = 5

        # 3. 缩放（下采样）节点：使用相对模式，缩放比例由 UI 控制
        scale_down = tree.nodes.new(type="CompositorNodeScale")
        scale_down.location = (-400, 0)
        scale_down.space = 'RELATIVE'
        # 当缩放比例小于1时，下采样效果更明显
        scale_down.inputs["X"].default_value = scene.pixel_scale
        scale_down.inputs["Y"].default_value = scene.pixel_scale

        # 4. 分离 HSVA 节点
        sep_hsva = tree.nodes.new(type="CompositorNodeSepHSVA")
        sep_hsva.location = (0, 100)

        # 5. 对明度（Value）进行量化处理
        # 5.1 乘法节点：将明度乘以 UI 数值（乘法因子默认为30）
        mult = tree.nodes.new(type="CompositorNodeMath")
        mult.location = (200, 150)
        mult.operation = 'MULTIPLY'
        mult.inputs[1].default_value = scene.pixel_mult

        # 5.2 取整节点：将乘积结果取整
        round_node = tree.nodes.new(type="CompositorNodeMath")
        round_node.location = (400, 150)
        round_node.operation = 'ROUND'

        # 5.3 除法节点：再除以相同的因子，恢复至 0~1 区间（默认为100）
        div_node = tree.nodes.new(type="CompositorNodeMath")
        div_node.location = (600, 150)
        div_node.operation = 'DIVIDE'
        div_node.inputs[1].default_value = scene.pixel_div

        # 6. 合并 HSVA 节点
        comb_hsva = tree.nodes.new(type="CompositorNodeCombHSVA")
        comb_hsva.location = (800, 100)

        # 7. Composite 节点
        comp = tree.nodes.new(type="CompositorNodeComposite")
        comp.location = (1000, 0)
        comp.use_alpha = True

        # 8. Viewer 节点
        viewer = tree.nodes.new(type="CompositorNodeViewer")
        viewer.location = (1000, -200)

        # --- 连接节点 ---
        links = tree.links
        # Render Layers -> Blur
        links.new(rl.outputs["Image"], blur.inputs["Image"])
        # Blur -> Scale Down
        links.new(blur.outputs["Image"], scale_down.inputs["Image"])
        # Scale Down -> 分离 HSVA
        links.new(scale_down.outputs["Image"], sep_hsva.inputs["Image"])
        # 分离 HSVA 的 H、S、A 直接传给合并节点
        links.new(sep_hsva.outputs["H"], comb_hsva.inputs["H"])
        links.new(sep_hsva.outputs["S"], comb_hsva.inputs["S"])
        links.new(sep_hsva.outputs["A"], comb_hsva.inputs["A"])
        # 对 V 通道：分离 -> 乘法 -> 取整 -> 除法 -> 合并
        links.new(sep_hsva.outputs["V"], mult.inputs[0])
        links.new(mult.outputs[0], round_node.inputs[0])
        links.new(round_node.outputs[0], div_node.inputs[0])
        links.new(div_node.outputs[0], comb_hsva.inputs["V"])
        # 合并后的图像输出到 Composite 与 Viewer
        links.new(comb_hsva.outputs["Image"], comp.inputs["Image"])
        links.new(comb_hsva.outputs["Image"], viewer.inputs["Image"])

        self.report({'INFO'}, "像素化合成节点已生成！")
        return {'FINISHED'}

# 面板类：在节点编辑器中提供 UI 控件
class NODE_PT_pixelate_composite(bpy.types.Panel):
    bl_label = "像素化节点"
    bl_idname = "NODE_PT_pixelate_composite"
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'UI'
    bl_category = '像素化'

    @classmethod
    def poll(cls, context):
        # 仅在当前节点树为合成节点树时显示
        return context.space_data.tree_type == 'CompositorNodeTree'

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        layout.prop(scene, "pixel_scale", text="缩放比例")
        layout.prop(scene, "pixel_mult", text="乘法因子")
        layout.prop(scene, "pixel_div", text="除法因子")
        layout.operator("node.add_pixelate_composite", text="生成像素化节点")

# 注册属性和类
def register():
    bpy.utils.register_class(NODE_OT_add_pixelate_composite)
    bpy.utils.register_class(NODE_PT_pixelate_composite)
    bpy.types.Scene.pixel_scale = FloatProperty(
        name="缩放比例",
        description="控制下采样时的缩放比例（小于1更明显）",
        default=0.05,
        min=0.01,
        max=100.0,
    )
    bpy.types.Scene.pixel_mult = FloatProperty(
        name="乘法因子",
        description="用于对明度通道进行乘法操作",
        default=30,
        min=0.01,
        max=1000.0,
    )
    bpy.types.Scene.pixel_div = FloatProperty(
        name="除法因子",
        description="用于对明度通道进行除法操作",
        default=100,
        min=0.01,
        max=1000.0,
    )

def unregister():
    bpy.utils.unregister_class(NODE_OT_add_pixelate_composite)
    bpy.utils.unregister_class(NODE_PT_pixelate_composite)
    del bpy.types.Scene.pixel_scale
    del bpy.types.Scene.pixel_mult
    del bpy.types.Scene.pixel_div

if __name__ == "__main__":
    register()
