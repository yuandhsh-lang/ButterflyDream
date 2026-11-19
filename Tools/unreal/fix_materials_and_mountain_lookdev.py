import unreal

ASSET_SUB = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
lib = unreal.MaterialEditingLibrary

def main():
    unreal.log("[LOOKDEV] Tuning all material instances in /Game/LuxGenerated/_V3Imp/...")
    all_assets = ASSET_SUB.list_assets("/Game/LuxGenerated/_V3Imp", recursive=True)
    
    tuned_count = 0
    for ap in all_assets:
        mat = ASSET_SUB.load_asset(ap)
        if not isinstance(mat, unreal.MaterialInstanceConstant):
            continue
            
        mname = mat.get_name()
        snames = [str(n) for n in lib.get_scalar_parameter_names(mat)]
        vnames = [str(n) for n in lib.get_vector_parameter_names(mat)]
        applied = False
        
        # 1. Mountain: Traditional Chinese ink wash
        if "Mountain" in mname or "InkMtn" in ap:
            if "EmissiveStrength" in snames:
                lib.set_material_instance_scalar_parameter_value(mat, "EmissiveStrength", 0.0)
                applied = True
            if "OcclusionStrength" in snames:
                lib.set_material_instance_scalar_parameter_value(mat, "OcclusionStrength", 1.0)
                applied = True
            if "RoughnessFactor" in snames:
                lib.set_material_instance_scalar_parameter_value(mat, "RoughnessFactor", 0.88)
                applied = True
            if "BaseColorFactor" in vnames:
                lib.set_material_instance_vector_parameter_value(mat, "BaseColorFactor", unreal.LinearColor(0.12, 0.16, 0.22, 1.0))
                applied = True
            unreal.log(f"[LOOKDEV] Tuned Ink Mountain: {mname}")
            
        # 2. Hero Butterfly: Deep midnight sapphire + golden filigree
        elif "Butterfly" in mname or "Wing" in ap or "Body" in ap:
            if "EmissiveStrength" in snames:
                lib.set_material_instance_scalar_parameter_value(mat, "EmissiveStrength", 0.22)
                applied = True
            if "OcclusionStrength" in snames:
                lib.set_material_instance_scalar_parameter_value(mat, "OcclusionStrength", 0.65)
                applied = True
            if "BaseColorFactor" in vnames:
                lib.set_material_instance_vector_parameter_value(mat, "BaseColorFactor", unreal.LinearColor(0.20, 0.45, 0.90, 1.0))
                applied = True
            unreal.log(f"[LOOKDEV] Tuned Butterfly: {mname}")
            
        # 3. Crystal Pagoda & Taiji Sphere: Translucent crystal refractions
        elif any(k in mname for k in ["Pagoda", "Taiji", "Garden"]):
            if "EmissiveStrength" in snames:
                lib.set_material_instance_scalar_parameter_value(mat, "EmissiveStrength", 0.04)
                applied = True
            if "OcclusionStrength" in snames:
                lib.set_material_instance_scalar_parameter_value(mat, "OcclusionStrength", 0.85)
                applied = True
            unreal.log(f"[LOOKDEV] Tuned Crystal/Taiji: {mname}")
            
        # 4. Standard architecture: Zero self-emission, full PBR relief
        else:
            if "EmissiveStrength" in snames:
                lib.set_material_instance_scalar_parameter_value(mat, "EmissiveStrength", 0.0)
                applied = True
            if "OcclusionStrength" in snames:
                lib.set_material_instance_scalar_parameter_value(mat, "OcclusionStrength", 1.0)
                applied = True
            unreal.log(f"[LOOKDEV] Tuned Architecture: {mname}")

        if applied:
            lib.update_material_instance(mat)
            ASSET_SUB.save_loaded_asset(mat, False)
            tuned_count += 1
            
    unreal.log(f"[LOOKDEV] Successfully tuned {tuned_count} material instances!")

if __name__ == "__main__":
    main()
