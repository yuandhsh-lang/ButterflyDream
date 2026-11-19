import unreal

mat = unreal.load_asset("/Game/LuxGenerated/Materials/M_Lux_StarSeaSkyDome.M_Lux_StarSeaSkyDome")
unreal.log(f"MAT: {mat}")
if mat:
    unreal.log(f"two_sided: {mat.get_editor_property('two_sided')}")
    unreal.log(f"shading_model: {mat.get_editor_property('shading_model')}")
    unreal.log(f"is_sky: {mat.get_editor_property('is_sky')}")
    for exp in mat.get_editor_property("expressions"):
        unreal.log(f"EXP: [{exp.get_class().get_name()}] {exp.get_name()} desc={exp.get_editor_property('desc') if hasattr(exp, 'desc') else ''}")
        if isinstance(exp, unreal.MaterialExpressionCustom):
            unreal.log(f"  CUSTOM CODE:\n{exp.get_editor_property('code')}")
            for inp in exp.get_editor_property('inputs'):
                unreal.log(f"  INPUT: {inp.get_editor_property('input_name')}")

sphere = unreal.load_asset("/Engine/BasicShapes/Sphere")
if sphere:
    box = sphere.get_bounding_box()
    unreal.log(f"SPHERE BOUNDS: min={box.min} max={box.max}")
