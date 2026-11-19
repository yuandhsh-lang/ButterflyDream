import unreal

def log(msg):
    unreal.log(f"[MAT_INSPECT] {msg}")

asset_sub = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)

sky_mats = [
    "/Game/ThirdParty/F06/Custom/M_F06_SkyDome",
    "/Game/LuxGenerated/Materials/M_Lux_StarSeaSkyDome",
    "/Game/LuxGenerated/Materials/M_Lux_InkCloudSkyDome",
    "/Game/LuxGenerated/Materials/M_Lux_CrystalMirageSkyDome",
    "/Game/LuxGenerated/Materials/M_Lux_TaijiCosmosSkyDome",
]

for p in sky_mats:
    mat = asset_sub.load_asset(p)
    if not mat:
        log(f"MISSING: {p}")
        continue
    log(f"MAT {mat.get_name()}: shading_model={mat.get_editor_property('shading_model')} is_sky={mat.get_editor_property('is_sky')} two_sided={mat.get_editor_property('two_sided')} blend_mode={mat.get_editor_property('blend_mode')}")
    # Inspect material expressions
    exprs = mat.get_editor_property("expressions")
    log(f"  Expressions count: {len(exprs)}")
    for exp in exprs:
        log(f"    - {exp.get_class().get_name()}: {exp.get_name()}")
