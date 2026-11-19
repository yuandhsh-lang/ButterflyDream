import unreal
import os

MAP_PATHS = [
    "/Game/Maps/F06_SakuraDream",
    "/Game/Maps/Lux_StarSeaDream",
    "/Game/Maps/Lux_InkCloudDream",
    "/Game/Maps/Lux_CrystalMirageDream",
    "/Game/Maps/Lux_TaijiAwakeningDream",
]

EDITOR_SUB = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
LEVEL_SUB = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
ASSET_TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
SYSTEM_LIB = unreal.SystemLibrary()

def log(msg: str):
    unreal.log(f"[AAA_POLISH] {msg}")

def safe_set_prop(obj, prop_name: str, val):
    try:
        obj.set_editor_property(prop_name, val)
        return True
    except Exception as e:
        log(f"Warning: Failed to set {prop_name} on {obj}: {e}")
        return False

def reimport_butterfly():
    log("Reimporting G1 Celestial Butterfly assets...")
    ready_dir = r"E:\紫萱2版\Assets\LuxGenerated\V2_Butterfly\Ready"
    parts = [
        ("Butterfly_Body.glb", "/Game/LuxGenerated/Butterfly_B01", "Butterfly_Body"),
        ("Wing_L.glb", "/Game/LuxGenerated/Butterfly_B01", "Wing_L"),
        ("Wing_R.glb", "/Game/LuxGenerated/Butterfly_B01", "Wing_R"),
    ]
    for glb_fn, dest_path, asset_name in parts:
        glb_file = os.path.join(ready_dir, glb_fn)
        if not os.path.exists(glb_file):
            log(f"Missing file: {glb_file}")
            continue
        
        task = unreal.AssetImportTask()
        task.set_editor_property("filename", glb_file)
        task.set_editor_property("destination_path", dest_path)
        task.set_editor_property("destination_name", asset_name)
        task.set_editor_property("replace_existing", True)
        task.set_editor_property("automated", True)
        task.set_editor_property("save", True)
        
        ASSET_TOOLS.import_asset_tasks([task])
        log(f"Imported {asset_name} from {glb_fn}")

def polish_materials():
    log("Polishing material instances for rich dark PBR contrast and zero whiteout...")
    mat_lib = unreal.MaterialEditingLibrary
    
    # Update M_LuxButterfly_V2
    butterfly_mat = unreal.load_asset("/Game/LuxGenerated/Materials/M_LuxButterfly_V2.M_LuxButterfly_V2")
    if butterfly_mat:
        mat_lib.set_material_instance_scalar_parameter_value(butterfly_mat, "EmissiveStrength", 0.28)
        mat_lib.set_material_instance_scalar_parameter_value(butterfly_mat, "OcclusionStrength", 0.65)
        mat_lib.update_material_instance(butterfly_mat)
        unreal.EditorAssetLibrary.save_loaded_asset(butterfly_mat)
        log("Updated M_LuxButterfly_V2 emissive to 0.28")

    # Update architectural materials
    mats_to_darken = [
        "/Game/LuxGenerated/Materials/M_Ink_Cloud_Mountain_Complex.M_Ink_Cloud_Mountain_Complex",
        "/Game/LuxGenerated/Materials/M_Floating_Pavilion.M_Floating_Pavilion",
        "/Game/LuxGenerated/Materials/M_Celestial_Bridge.M_Celestial_Bridge",
        "/Game/LuxGenerated/Materials/M_Luminous_Guqin_Bridge.M_Luminous_Guqin_Bridge",
        "/Game/LuxGenerated/Materials/M_Floating_Crystal_Garden.M_Floating_Crystal_Garden",
        "/Game/LuxGenerated/Materials/M_Dragon_Pillar.M_Dragon_Pillar",
        "/Game/LuxGenerated/Materials/M_Celestial_Guardian.M_Celestial_Guardian",
        "/Game/LuxGenerated/Materials/M_Seven_Tier_Crystal_Pagoda.M_Seven_Tier_Crystal_Pagoda",
        "/Game/LuxGenerated/Materials/M_Taiji_Star_Sphere.M_Taiji_Star_Sphere",
    ]
    for mpath in mats_to_darken:
        mat = unreal.load_asset(mpath)
        if mat:
            em = 0.10 if ("Pagoda" in mpath or "Taiji" in mpath) else 0.02
            mat_lib.set_material_instance_scalar_parameter_value(mat, "EmissiveStrength", em)
            mat_lib.set_material_instance_scalar_parameter_value(mat, "OcclusionStrength", 0.85)
            if "Mountain" in mpath:
                # Deep Chinese ink-wash tint
                mat_lib.set_material_instance_vector_parameter_value(mat, "BaseColorTint", unreal.LinearColor(0.12, 0.16, 0.22, 1.0))
            mat_lib.update_material_instance(mat)
            unreal.EditorAssetLibrary.save_loaded_asset(mat)
            log(f"Darkened material {mpath} (Emissive={em})")

def polish_realm_map(map_path: str):
    log(f"--- Polishing Map: {map_path} ---")
    EDITOR_SUB.load_map(map_path)
    world = EDITOR_SUB.get_editor_world()
    
    actor_sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    all_actors = actor_sub.get_all_level_actors()
    
    is_f06 = ("F06" in map_path)
    
    for a in all_actors:
        cls_name = a.get_class().get_name()
        label = a.get_actor_label()
        
        # 1. SkyLight: Kill real-time capture red warning
        if cls_name == "SkyLight":
            slc = a.light_component
            safe_set_prop(slc, "real_time_capture", False)
            safe_set_prop(slc, "source_type", unreal.SkyLightSourceType.SLS_CAPTURED_SCENE)
            safe_set_prop(slc, "lower_hemisphere_is_black", False)
            safe_set_prop(slc, "lower_hemisphere_color", unreal.LinearColor(0.04, 0.06, 0.10, 1.0))
            safe_set_prop(slc, "intensity", 0.95)
            slc.recapture_sky()
            log(f"Recaptured SkyLight on {label} (real_time_capture=False)")
            
        # 2. DirectionalLight: soften intensity
        elif cls_name == "DirectionalLight":
            dlc = a.light_component
            safe_set_prop(dlc, "intensity", 1.45)
            log(f"Set DirectionalLight intensity to 1.45 on {label}")
            
        # 3. PostProcessVolume: auto exposure & bloom
        elif cls_name == "PostProcessVolume":
            pp = a.settings
            safe_set_prop(pp, "override_auto_exposure_bias", True)
            safe_set_prop(pp, "auto_exposure_bias", -0.32 if not is_f06 else -0.28)
            safe_set_prop(pp, "override_auto_exposure_max_brightness", True)
            safe_set_prop(pp, "auto_exposure_max_brightness", 1.35)
            safe_set_prop(pp, "override_bloom_intensity", True)
            safe_set_prop(pp, "bloom_intensity", 0.22)
            safe_set_prop(pp, "override_bloom_threshold", True)
            safe_set_prop(pp, "bloom_threshold", 1.25)
            log(f"Set PostProcess exposure & bloom on {label}")
            
        # 4. Return Gates: Relocate behind player to eliminate giant pipe photobombing
        elif "ReturnGate" in label and "Dais" not in label:
            curr_loc = a.get_actor_location()
            # Move behind player (player is at Y = -1380, so put return gate at Y = -2550)
            new_loc = unreal.Vector(0.0, -2550.0, curr_loc.z)
            new_rot = unreal.Rotator()
            new_rot.pitch = 0.0
            new_rot.yaw = 270.0 # pointing back along -Y
            new_rot.roll = 0.0
            a.set_actor_location(new_loc, False, False)
            a.set_actor_rotation(new_rot, False)
            safe_set_prop(a, "ResonanceDistance", 900.0)
            log(f"Moved {label} to {new_loc} (Yaw=270, Resonance=900)")
            
        elif "ReturnGateDais" in label:
            curr_loc = a.get_actor_location()
            new_loc = unreal.Vector(0.0, -2550.0, curr_loc.z)
            new_rot = unreal.Rotator()
            new_rot.pitch = 0.0
            new_rot.yaw = 270.0
            new_rot.roll = 0.0
            a.set_actor_location(new_loc, False, False)
            a.set_actor_rotation(new_rot, False)
            log(f"Moved {label} to {new_loc}")
            
        # 5. In F06: lift PlayerStart slightly to clear stairs
        elif is_f06 and cls_name == "PlayerStart":
            new_loc = unreal.Vector(-0.07, -2420.0, -35.0)
            new_rot = unreal.Rotator()
            new_rot.pitch = 4.2
            new_rot.yaw = 90.0
            new_rot.roll = 0.0
            a.set_actor_location(new_loc, False, False)
            a.set_actor_rotation(new_rot, False)
            log(f"Adjusted F06 PlayerStart to {new_loc}")

    EDITOR_SUB.save_current_level()
    log(f"Saved {map_path} successfully")

def main():
    log("=== STARTING FIVE REALMS AAA POLISH ===")
    reimport_butterfly()
    polish_materials()
    for mp in MAP_PATHS:
        polish_realm_map(mp)
    log("=== COMPLETED FIVE REALMS AAA POLISH ===")

if __name__ == "__main__":
    raise RuntimeError("Disabled: legacy five-realm polish can restore F06 and overwrite current material work.")
