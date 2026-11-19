import unreal

EDITOR_SUB = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
LEVEL_SUB = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
ASSET_SUB = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
ACTOR_SUB = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
lib = unreal.MaterialEditingLibrary

MAP_PATHS = [
    "/Game/Maps/F06_SakuraDream",
    "/Game/Maps/Lux_StarSeaDream",
    "/Game/Maps/Lux_InkCloudDream",
    "/Game/Maps/Lux_CrystalMirageDream",
    "/Game/Maps/Lux_TaijiAwakeningDream",
]

def log(msg):
    unreal.log(f"[AAA_FIX] {msg}")

def fix_skydome_materials():
    log("Fixing SkyDome materials to is_sky=True, two_sided=True...")
    sky_mat_paths = [
        "/Game/ThirdParty/F06/Custom/M_F06_SkyDome",
        "/Game/LuxGenerated/Materials/M_Lux_StarSeaSkyDome",
        "/Game/LuxGenerated/Materials/M_Lux_InkCloudSkyDome",
        "/Game/LuxGenerated/Materials/M_Lux_CrystalMirageSkyDome",
        "/Game/LuxGenerated/Materials/M_Lux_TaijiCosmosSkyDome",
    ]
    for sp in sky_mat_paths:
        mat = ASSET_SUB.load_asset(sp)
        if mat and isinstance(mat, unreal.Material):
            mat.set_editor_property("is_sky", True)
            mat.set_editor_property("two_sided", True)
            mat.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
            lib.recompile_material(mat)
            ASSET_SUB.save_loaded_asset(mat, False)
            log(f"Configured is_sky=True, two_sided=True for {sp}")

def fix_map_actors(map_path):
    log(f"=== Fixing Map: {map_path} ===")
    if not LEVEL_SUB.load_level(map_path):
        log(f"Failed loading {map_path}")
        return
        
    actors = ACTOR_SUB.get_all_level_actors()
    log(f"Loaded {len(actors)} actors in {map_path}")
    
    is_f06 = ("F06" in map_path)
    is_starsea = ("StarSea" in map_path)
    is_inkcloud = ("InkCloud" in map_path)
    is_crystal = ("CrystalMirage" in map_path)
    is_taiji = ("TaijiAwakening" in map_path)
    
    for a in actors:
        label = a.get_actor_label()
        cls_name = a.get_class().get_name()
        loc = a.get_actor_location()
        
        # 1. SkyDome - 4km radius, negative X to invert normals inward
        if "SkyDome" in label:
            a.set_actor_location(unreal.Vector(0.0, 0.0, 0.0), False, False)
            a.set_actor_scale3d(unreal.Vector(-8000.0, 8000.0, 8000.0))
            smc = a.get_component_by_class(unreal.StaticMeshComponent)
            if smc:
                smc.set_cast_shadow(False)
                smc.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
            log(f"Set {label} scale to (-8000, 8000, 8000)")
            
        # 2. MirrorWater - seamless 2.5km plane at Z=-140
        elif "MirrorWater" in label or ("Water" in label and "Sky" not in label):
            a.set_actor_location(unreal.Vector(0.0, 1200.0, -140.0), False, False)
            a.set_actor_scale3d(unreal.Vector(5000.0, 5000.0, 1.0))
            smc = a.get_component_by_class(unreal.StaticMeshComponent)
            if smc:
                smc.set_cast_shadow(False)
                smc.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
            log(f"Set {label} to Z=-140, scale=5000")
            
        # 3. SkyLight: ensure no real-time capture red warning
        elif cls_name == "SkyLight":
            slc = a.light_component
            slc.set_editor_property("real_time_capture", False)
            slc.set_editor_property("source_type", unreal.SkyLightSourceType.SLS_CAPTURED_SCENE)
            slc.set_editor_property("lower_hemisphere_is_black", False)
            slc.set_editor_property("lower_hemisphere_color", unreal.LinearColor(0.04, 0.06, 0.10, 1.0))
            slc.set_editor_property("intensity", 1.15)
            try:
                slc.recapture_sky()
            except Exception:
                pass
            log(f"Recaptured SkyLight on {label}")
            
        # 4. PostProcessVolume
        elif cls_name == "PostProcessVolume":
            pp = a.settings
            pp.set_editor_property("override_auto_exposure_bias", True)
            pp.set_editor_property("auto_exposure_bias", -0.15)
            pp.set_editor_property("override_auto_exposure_min_brightness", True)
            pp.set_editor_property("auto_exposure_min_brightness", 0.40)
            pp.set_editor_property("override_auto_exposure_max_brightness", True)
            pp.set_editor_property("auto_exposure_max_brightness", 1.60)
            pp.set_editor_property("override_bloom_intensity", True)
            pp.set_editor_property("bloom_intensity", 0.35)
            log(f"Tuned PostProcess on {label}")
            
        # 5. Return Gates: move far behind
        elif "ReturnGate" in label and "Dais" not in label:
            a.set_actor_location(unreal.Vector(0.0, -3200.0, 40.0), False, False)
            rot = unreal.Rotator(0.0, 270.0, 0.0)
            a.set_actor_rotation(rot, False)
            try:
                a.set_editor_property("ResonanceDistance", 800.0)
            except Exception:
                pass
            log(f"Moved ReturnGate {label} to Y=-3200")
            
        elif "ReturnGateDais" in label:
            a.set_actor_location(unreal.Vector(0.0, -3200.0, -140.0), False, False)
            
        # 6. PlayerStarts
        elif cls_name == "PlayerStart":
            if is_f06:
                new_loc = unreal.Vector(0.0, -1450.0, 80.0)
                new_rot = unreal.Rotator(-4.0, 90.0, 0.0)
            else:
                new_loc = unreal.Vector(0.0, -1200.0, 240.0)
                new_rot = unreal.Rotator(-6.0, 90.0, 0.0)
            a.set_actor_location(new_loc, False, False)
            a.set_actor_rotation(new_rot, False)
            log(f"Moved PlayerStart to {new_loc}")
            
        # 7. Elevation of Submerged Landmarks
        elif is_starsea:
            if "CelestialBridge" in label:
                a.set_actor_location(unreal.Vector(0.0, 480.0, 35.0), False, False)
                log(f"Elevated CelestialBridge to Z=35")
            elif "DragonPillar" in label:
                a.set_actor_location(unreal.Vector(loc.x, loc.y, -30.0), False, False)
                log(f"Elevated {label} to Z=-30")
            elif "FloatingPavilion" in label:
                a.set_actor_location(unreal.Vector(0.0, 2680.0, 220.0), False, False)
                log(f"Elevated FloatingPavilion to Z=220")
            elif "ForwardStarGate" in label:
                a.set_actor_location(unreal.Vector(0.0, 1660.0, 140.0), False, False)
                log(f"Elevated ForwardStarGate to Z=140")
            elif "ForwardGateDais" in label:
                a.set_actor_location(unreal.Vector(0.0, 1660.0, -135.0), False, False)
            elif "HeroGuardian" in label:
                a.set_actor_location(unreal.Vector(520.0, -360.0, 60.0), False, False)
                
        elif is_inkcloud:
            if "CentralMountainSanctuary" in label:
                a.set_actor_location(unreal.Vector(0.0, 2750.0, 120.0), False, False)
                log(f"Elevated CentralMountainSanctuary to Z=120")
            elif "FlankMountain" in label:
                a.set_actor_location(unreal.Vector(loc.x, 2080.0, 180.0), False, False)
            elif "Guqin" in label or "Bridge" in label:
                a.set_actor_location(unreal.Vector(0.0, 480.0, 50.0), False, False)
                log(f"Elevated Guqin Bridge to Z=50")
            elif "Forward" in label and "Gate" in label:
                a.set_actor_location(unreal.Vector(0.0, 1660.0, 140.0), False, False)
            elif "ForwardGateDais" in label:
                a.set_actor_location(unreal.Vector(0.0, 1660.0, -135.0), False, False)
                
        elif is_crystal:
            if "Pagoda" in label:
                a.set_actor_location(unreal.Vector(0.0, 2750.0, 240.0), False, False)
                log(f"Elevated Crystal Pagoda to Z=240")
            elif "Garden" in label:
                a.set_actor_location(unreal.Vector(0.0, 520.0, 80.0), False, False)
                log(f"Elevated Crystal Garden to Z=80")
            elif "Forward" in label and "Gate" in label:
                a.set_actor_location(unreal.Vector(0.0, 1660.0, 140.0), False, False)
            elif "ForwardGateDais" in label:
                a.set_actor_location(unreal.Vector(0.0, 1660.0, -135.0), False, False)
                
        elif is_taiji:
            if "Taiji" in label or "Sphere" in label:
                if "SkyDome" not in label:
                    a.set_actor_location(unreal.Vector(0.0, 2600.0, 680.0), False, False)
                    a.set_actor_scale3d(unreal.Vector(14.0, 14.0, 14.0))
                    log(f"Positioned Taiji Star Sphere at Z=680, scale=14")
            elif "ScrollGate" in label or ("Forward" in label and "Gate" in label):
                a.set_actor_location(unreal.Vector(0.0, 1500.0, 140.0), False, False)
                log(f"Positioned Celestial Scroll Gate at Z=140")

    LEVEL_SUB.save_current_level()
    log(f"Saved {map_path} successfully")

def main():
    log("=== STARTING REALMS AAA VISUALS FIX ===")
    fix_skydome_materials()
    for mp in MAP_PATHS:
        fix_map_actors(mp)
    log("=== COMPLETED REALMS AAA VISUALS FIX ===")

if __name__ == "__main__":
    raise RuntimeError("Disabled: legacy five-realm visual polish is incompatible with the current four-realm rebuild.")
