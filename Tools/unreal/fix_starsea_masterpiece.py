import unreal

def log(msg):
    unreal.log(f"[STARSEA_FIX] {msg}")

level_sub = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actor_sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
asset_sub = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
editor_sub = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
lib = unreal.MaterialEditingLibrary

map_path = "/Game/Maps/Lux_StarSeaDream"
log(f"Loading {map_path}...")
level_sub.load_level(map_path)

# 1. Build a truly magnificent, pristine 360° celestial aurora sky material
sky_pkg = "/Game/LuxGenerated/Materials/M_Lux_StarSeaSkyDome"
sky_mat = asset_sub.load_asset(sky_pkg)
if sky_mat:
    log("Rebuilding M_Lux_StarSeaSkyDome cleanly...")
    sky_mat.set_editor_property("is_sky", False)  # CRITICAL: Disable BadSky validation!
    sky_mat.set_editor_property("two_sided", True)
    sky_mat.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    sky_mat.set_editor_property("blend_mode", unreal.BlendMode.BLEND_OPAQUE)
    
    # Clear old expressions and build clean equirectangular celestial shader
    lib.delete_all_material_expressions(sky_mat)
    
    # Import or load panorama texture
    pano_tex = asset_sub.load_asset("/Game/LuxGenerated/Materials/T_OutdoorAuroraPano")
    if not pano_tex:
        # Load directly from JPG
        pano_jpg = "E:/紫萱2版/Assets/LuxGenerated/V2_Sanctuary/World_OutdoorAuroraSanctuary_3FO4K4REJBX6_pano.jpg"
        task = unreal.AssetImportTask()
        task.set_editor_property("filename", pano_jpg)
        task.set_editor_property("destination_path", "/Game/LuxGenerated/Materials")
        task.set_editor_property("destination_name", "T_OutdoorAuroraPano")
        task.set_editor_property("replace_existing", True)
        task.set_editor_property("automated", True)
        task.set_editor_property("save", True)
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        pano_tex = asset_sub.load_asset("/Game/LuxGenerated/Materials/T_OutdoorAuroraPano")
    
    if pano_tex:
        pano_tex.set_editor_property("srgb", True)
        pano_tex.set_editor_property("mip_gen_settings", unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS)
        pano_tex.set_editor_property("address_x", unreal.TextureAddress.TA_WRAP)
        pano_tex.set_editor_property("address_y", unreal.TextureAddress.TA_CLAMP)
        asset_sub.save_loaded_asset(pano_tex, False)
        
        # Build CameraVector equirectangular UV mapping:
        # u = frac(atan2(d.y, d.x) * 0.15915494 + 0.5)
        # v = acos(clamp(d.z, -1.0, 1.0)) * 0.31830989
        cam_vec = lib.create_material_expression(sky_mat, unreal.MaterialExpressionCameraVector, -800, 0)
        custom_uv = lib.create_material_expression(sky_mat, unreal.MaterialExpressionCustom, -580, 0)
        custom_uv.set_editor_property("description", "EquirectangularUV")
        custom_uv.set_editor_property("output_type", unreal.CustomMaterialOutputType.CMOT_FLOAT2)
        inp = unreal.CustomInput()
        inp.set_editor_property("input_name", "Dir")
        custom_uv.set_editor_property("inputs", [inp])
        custom_uv.set_editor_property(
            "code",
            "float3 d = normalize(Dir);\n"
            "float u = frac(atan2(d.y, d.x) * 0.15915494 + 0.5 + 0.72);\n"
            "float v = acos(clamp(d.z, -1.0, 1.0)) * 0.31830989;\n"
            "return float2(u, v);"
        )
        lib.connect_material_expressions(cam_vec, "", custom_uv, "Dir")
        
        tex_sample = lib.create_material_expression(sky_mat, unreal.MaterialExpressionTextureSample, -320, 0)
        tex_sample.set_editor_property("texture", pano_tex)
        lib.connect_material_expressions(custom_uv, "", tex_sample, "UVs")
        
        # Boost vibrance & celestial brilliance
        mul_node = lib.create_material_expression(sky_mat, unreal.MaterialExpressionMultiply, -100, 0)
        boost = lib.create_material_expression(sky_mat, unreal.MaterialExpressionConstant, -220, 120)
        boost.set_editor_property("r", 1.85)
        lib.connect_material_expressions(tex_sample, "RGB", mul_node, "A")
        lib.connect_material_expressions(boost, "", mul_node, "B")
        
        lib.connect_material_property(mul_node, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
        lib.recompile_material(sky_mat)
        asset_sub.save_loaded_asset(sky_mat, False)
        log("Equirectangular 360° panorama shader compiled successfully!")
    else:
        log("WARNING: Could not load pano_tex, falling back to gradient")

# 2. Iterate actors in Lux_StarSeaDream and fix transforms, fog, lights, postprocess
actors = actor_sub.get_all_level_actors()
log(f"Configuring {len(actors)} actors in Lux_StarSeaDream...")

for a in actors:
    lbl = a.get_actor_label()
    cls_name = a.get_class().get_name()
    
    # SkyDome: positive scale 4000, two-sided, centered at origin
    if "SkyDome" in lbl:
        a.set_actor_location(unreal.Vector(0.0, 0.0, 0.0), False, False)
        a.set_actor_scale3d(unreal.Vector(4000.0, 4000.0, 4000.0))
        smc = a.get_component_by_class(unreal.StaticMeshComponent)
        if smc:
            smc.set_cast_shadow(False)
            smc.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
            smc.set_editor_property("disallow_nanite", True)
        log(f"SkyDome configured: {lbl}")
        
    # Mirror Water: at Z = -140
    elif "Water" in lbl or "Mirror" in lbl:
        a.set_actor_location(unreal.Vector(0.0, 1200.0, -140.0), False, False)
        a.set_actor_scale3d(unreal.Vector(5000.0, 5000.0, 1.0))
        smc = a.get_component_by_class(unreal.StaticMeshComponent)
        if smc:
            smc.set_cast_shadow(False)
            smc.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
        log(f"Water configured: {lbl}")
        
    # ExponentialHeightFog: GENTLE, luminous, transparent in foreground!
    elif cls_name == "ExponentialHeightFog" or "Fog" in lbl:
        fc = a.component if hasattr(a, "component") else a.get_component_by_class(unreal.ExponentialHeightFogComponent)
        if fc:
            fc.set_editor_property("fog_density", 0.00015)  # Very light ethereal mist!
            fc.set_editor_property("fog_height_falloff", 0.05)
            fc.set_editor_property("start_distance", 3200.0)  # Complete clarity for first 32 meters!
            fc.set_editor_property("fog_inscattering_luminance", unreal.LinearColor(0.08, 0.16, 0.35, 1.0))
            fc.set_editor_property("fog_max_opacity", 0.45)
            log(f"ExponentialHeightFog tuned for clarity: {lbl}")
            
    # Floating Pavilion: Hero centerpiece towering at Y=2400, Z=180
    elif "FloatingPavilion" in lbl:
        a.set_actor_location(unreal.Vector(0.0, 2400.0, 180.0), False, False)
        smc = a.get_component_by_class(unreal.StaticMeshComponent)
        if smc:
            smc.set_cast_shadow(True)
            smc.set_editor_property("disallow_nanite", True)
        log(f"FloatingPavilion positioned: {lbl}")
        
    # Directional Light (Moon / Star key light)
    elif cls_name == "DirectionalLight" or "KeyLight" in lbl:
        dlc = a.light_component
        dlc.set_editor_property("intensity", 3.2)
        dlc.set_editor_property("light_color", unreal.Color(210, 230, 255, 255))
        a.set_actor_rotation(unreal.Rotator(-32.0, 42.0, 0.0), False)
        log(f"DirectionalLight tuned: {lbl}")
        
    # SkyLight
    elif cls_name == "SkyLight":
        slc = a.light_component
        slc.set_editor_property("real_time_capture", False)
        slc.set_editor_property("source_type", unreal.SkyLightSourceType.SLS_CAPTURED_SCENE)
        slc.set_editor_property("intensity", 1.35)
        slc.set_editor_property("light_color", unreal.Color(180, 205, 255, 255))
        slc.set_editor_property("lower_hemisphere_is_black", False)
        slc.set_editor_property("lower_hemisphere_color", unreal.LinearColor(0.04, 0.08, 0.18, 1.0))
        try:
            slc.recapture_sky()
        except Exception:
            pass
        log(f"SkyLight tuned & recaptured: {lbl}")
        
    # PostProcessVolume
    elif cls_name == "PostProcessVolume":
        pp = a.settings
        pp.set_editor_property("override_auto_exposure_bias", True)
        pp.set_editor_property("auto_exposure_bias", 0.0)
        pp.set_editor_property("override_auto_exposure_min_brightness", True)
        pp.set_editor_property("auto_exposure_min_brightness", 0.45)
        pp.set_editor_property("override_auto_exposure_max_brightness", True)
        pp.set_editor_property("auto_exposure_max_brightness", 1.80)
        pp.set_editor_property("override_bloom_intensity", True)
        pp.set_editor_property("bloom_intensity", 0.42)
        log(f"PostProcessVolume calibrated: {lbl}")

editor_sub.save_current_level()
log("Lux_StarSeaDream successfully saved with AAA celestial visuals!")
