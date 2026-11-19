import json
import traceback
from pathlib import Path
import unreal

REPORT_PATH = Path("C:/Users/LENOVO/.gemini/antigravity/brain/07ecec93-b615-4bfa-9387-541e0966b261/scratch/parity_apply_report.json")

level_sub = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actor_sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
sm_sub = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
eal = unreal.EditorAssetLibrary
mel = unreal.MaterialEditingLibrary
asset_tools = unreal.AssetToolsHelpers.get_asset_tools()


def log(msg):
    unreal.log(f"[PARITY] {msg}")


def get_or_create_material(pkg_dir, mat_name):
    pkg_path = f"{pkg_dir}/{mat_name}"
    if eal.does_asset_exist(pkg_path):
        mat = eal.load_asset(pkg_path)
        mel.delete_all_material_expressions(mat)
    else:
        eal.make_directory(pkg_dir)
        mat = asset_tools.create_asset(mat_name, pkg_dir, unreal.Material, unreal.MaterialFactoryNew())
    return mat


def make_const(mat, val, x=-400, y=0):
    c = mel.create_material_expression(mat, unreal.MaterialExpressionConstant, x, y)
    c.set_editor_property("r", float(val))
    return c


def make_vec3(mat, r, g, b, x=-400, y=0):
    c = mel.create_material_expression(mat, unreal.MaterialExpressionConstant3Vector, x, y)
    c.set_editor_property("constant", unreal.LinearColor(float(r), float(g), float(b), 1.0))
    return c


def disable_nanite_on_mesh(mesh_path, report_list):
    sm = eal.load_asset(mesh_path)
    if not sm:
        report_list.append({"mesh": mesh_path, "status": "NOT_FOUND"})
        return
    ns = sm_sub.get_nanite_settings(sm)
    if ns.enabled:
        ns.enabled = False
        sm_sub.set_nanite_settings(sm, ns, apply_changes=True)
        eal.save_loaded_asset(sm)
        report_list.append({"mesh": mesh_path, "nanite_disabled": True})
    else:
        report_list.append({"mesh": mesh_path, "nanite_disabled": False, "already_off": True})


def cleanup_parity_actors():
    removed = []
    for a in list(actor_sub.get_all_level_actors()):
        if a.get_actor_label().startswith("Parity_"):
            removed.append(a.get_actor_label())
            actor_sub.destroy_actor(a)
    return removed


def spawn_labeled(cls, label, loc=(0.0, 0.0, 0.0), rot=(0.0, 0.0, 0.0)):
    a = actor_sub.spawn_actor_from_class(cls, unreal.Vector(*loc), unreal.Rotator(*rot))
    a.set_actor_label(label)
    return a


def setup_post_process(label, exposure_bias, bloom_intensity, vignette_intensity):
    ppv = spawn_labeled(unreal.PostProcessVolume, label)
    ppv.set_actor_scale3d(unreal.Vector(1.0, 1.0, 1.0))
    ppv.set_editor_property("unbound", True)
    s = ppv.get_editor_property("settings")
    s.set_editor_property("override_auto_exposure_method", True)
    s.set_editor_property("auto_exposure_method", unreal.AutoExposureMethod.AEM_HISTOGRAM)
    s.set_editor_property("override_auto_exposure_min_brightness", True)
    s.set_editor_property("auto_exposure_min_brightness", 1.0)
    s.set_editor_property("override_auto_exposure_max_brightness", True)
    s.set_editor_property("auto_exposure_max_brightness", 1.0)
    s.set_editor_property("override_auto_exposure_bias", True)
    s.set_editor_property("auto_exposure_bias", float(exposure_bias))
    s.set_editor_property("override_bloom_intensity", True)
    s.set_editor_property("bloom_intensity", float(bloom_intensity))
    s.set_editor_property("override_vignette_intensity", True)
    s.set_editor_property("vignette_intensity", float(vignette_intensity))
    ppv.set_editor_property("settings", s)
    return ppv


# ============================================================
# CUSTOM MATERIALS
# ============================================================

def build_f06_moon_material():
    mat = get_or_create_material("/Game/ThirdParty/F06/Custom", "M_F06_Moon")
    mat.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
    mat.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    mat.set_editor_property("two_sided", True)

    tex_asset = eal.load_asset("/Game/ThirdParty/F06/04-main/04-main/Textures/moon-21366391")
    ts = mel.create_material_expression(mat, unreal.MaterialExpressionTextureSample, -700, 0)
    ts.set_editor_property("texture", tex_asset)

    c_min = make_const(mat, 0.50, -680, 220)
    c_max = make_const(mat, 0.78, -680, 300)
    ss = mel.create_material_expression(mat, unreal.MaterialExpressionSmoothStep, -460, 220)
    assert mel.connect_material_expressions(c_min, "", ss, "Min")
    assert mel.connect_material_expressions(c_max, "", ss, "Max")
    assert mel.connect_material_expressions(ts, "A", ss, "Value")

    # Radial UV falloff guaranteed to zero out 100% of background card corners
    uv = mel.create_material_expression(mat, unreal.MaterialExpressionTextureCoordinate, -860, 440)
    cx = make_const(mat, 0.50, -860, 520)
    cy = make_const(mat, 0.468, -860, 580)
    center = mel.create_material_expression(mat, unreal.MaterialExpressionAppendVector, -700, 540)
    assert mel.connect_material_expressions(cx, "", center, "A")
    assert mel.connect_material_expressions(cy, "", center, "B")

    dist = mel.create_material_expression(mat, unreal.MaterialExpressionDistance, -540, 480)
    assert mel.connect_material_expressions(uv, "", dist, "A")
    assert mel.connect_material_expressions(center, "", dist, "B")

    r_in = make_const(mat, 0.27, -540, 580)
    r_out = make_const(mat, 0.34, -540, 640)
    r_ss = mel.create_material_expression(mat, unreal.MaterialExpressionSmoothStep, -360, 500)
    assert mel.connect_material_expressions(r_in, "", r_ss, "Min")
    assert mel.connect_material_expressions(r_out, "", r_ss, "Max")
    assert mel.connect_material_expressions(dist, "", r_ss, "Value")

    r_mask = mel.create_material_expression(mat, unreal.MaterialExpressionOneMinus, -200, 500)
    assert mel.connect_material_expressions(r_ss, "", r_mask, "")

    final_alpha = mel.create_material_expression(mat, unreal.MaterialExpressionMultiply, -180, 280)
    assert mel.connect_material_expressions(ss, "", final_alpha, "A")
    assert mel.connect_material_expressions(r_mask, "", final_alpha, "B")

    tint = make_vec3(mat, 1.18, 1.15, 1.48, -520, -120)
    mul_col = mel.create_material_expression(mat, unreal.MaterialExpressionMultiply, -280, -60)
    assert mel.connect_material_expressions(ts, "RGB", mul_col, "A")
    assert mel.connect_material_expressions(tint, "", mul_col, "B")

    mul_em = mel.create_material_expression(mat, unreal.MaterialExpressionMultiply, -80, -40)
    assert mel.connect_material_expressions(mul_col, "", mul_em, "A")
    assert mel.connect_material_expressions(final_alpha, "", mul_em, "B")

    assert mel.connect_material_property(mul_em, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    assert mel.connect_material_property(final_alpha, "", unreal.MaterialProperty.MP_OPACITY)
    mel.recompile_material(mat)
    eal.save_loaded_asset(mat)
    return mat


def build_f06_gradient_material():
    mat = get_or_create_material("/Game/ThirdParty/F06/Custom", "M_F06_Gradient")
    mat.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
    mat.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    mat.set_editor_property("two_sided", True)

    wp = mel.create_material_expression(mat, unreal.MaterialExpressionWorldPosition, -780, 120)
    mask_z = mel.create_material_expression(mat, unreal.MaterialExpressionComponentMask, -580, 120)
    mask_z.set_editor_property("r", False)
    mask_z.set_editor_property("g", False)
    mask_z.set_editor_property("b", True)
    mask_z.set_editor_property("a", False)
    assert mel.connect_material_expressions(wp, "", mask_z, "")

    z_min = make_const(mat, -280.0, -580, 260)
    z_max = make_const(mat, 650.0, -580, 340)
    ss = mel.create_material_expression(mat, unreal.MaterialExpressionSmoothStep, -380, 180)
    assert mel.connect_material_expressions(z_min, "", ss, "Min")
    assert mel.connect_material_expressions(z_max, "", ss, "Max")
    assert mel.connect_material_expressions(mask_z, "", ss, "Value")

    one_m = mel.create_material_expression(mat, unreal.MaterialExpressionOneMinus, -220, 180)
    assert mel.connect_material_expressions(ss, "", one_m, "")

    op_scale = make_const(mat, 0.24, -220, 300)
    mul_op = mel.create_material_expression(mat, unreal.MaterialExpressionMultiply, -80, 200)
    assert mel.connect_material_expressions(one_m, "", mul_op, "A")
    assert mel.connect_material_expressions(op_scale, "", mul_op, "B")

    em_col = make_vec3(mat, 0.48, 0.40, 0.82, -320, -100)
    assert mel.connect_material_property(em_col, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    assert mel.connect_material_property(mul_op, "", unreal.MaterialProperty.MP_OPACITY)
    mel.recompile_material(mat)
    eal.save_loaded_asset(mat)
    return mat


def build_sky_dome_material(pkg_dir, mat_name, low_rgb, high_rgb, z_low=-1000.0, z_high=16000.0):
    mat = get_or_create_material(pkg_dir, mat_name)
    mat.set_editor_property("blend_mode", unreal.BlendMode.BLEND_OPAQUE)
    mat.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    mat.set_editor_property("two_sided", True)

    wp = mel.create_material_expression(mat, unreal.MaterialExpressionWorldPosition, -780, 100)
    mask_z = mel.create_material_expression(mat, unreal.MaterialExpressionComponentMask, -580, 100)
    mask_z.set_editor_property("r", False)
    mask_z.set_editor_property("g", False)
    mask_z.set_editor_property("b", True)
    mask_z.set_editor_property("a", False)
    assert mel.connect_material_expressions(wp, "", mask_z, "")

    z0 = make_const(mat, z_low, -580, 240)
    z1 = make_const(mat, z_high, -580, 320)
    ss = mel.create_material_expression(mat, unreal.MaterialExpressionSmoothStep, -380, 160)
    assert mel.connect_material_expressions(z0, "", ss, "Min")
    assert mel.connect_material_expressions(z1, "", ss, "Max")
    assert mel.connect_material_expressions(mask_z, "", ss, "Value")

    col_a = make_vec3(mat, *low_rgb, -380, -140)
    col_b = make_vec3(mat, *high_rgb, -380, -20)
    lerp = mel.create_material_expression(mat, unreal.MaterialExpressionLinearInterpolate, -140, 20)
    assert mel.connect_material_expressions(col_a, "", lerp, "A")
    assert mel.connect_material_expressions(col_b, "", lerp, "B")
    assert mel.connect_material_expressions(ss, "", lerp, "Alpha")

    assert mel.connect_material_property(lerp, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    mel.recompile_material(mat)
    eal.save_loaded_asset(mat)
    return mat


def set_local_light_radius(lc, radius):
    try:
        lc.set_editor_property("attenuation_radius", float(radius))
    except Exception:
        pass
    try:
        lc.set_attenuation_radius(float(radius))
    except Exception:
        pass


def configure_light_optics(lc, radius, specular_scale=None, inner_cone=None, outer_cone=None):
    """Apply finite attenuation radius plus optional specular and spotlight cone limits safely."""
    set_local_light_radius(lc, radius)
    if specular_scale is not None:
        try:
            lc.set_editor_property("specular_scale", float(specular_scale))
        except Exception:
            pass
    if inner_cone is not None:
        for fn in (lambda v: lc.set_editor_property("inner_cone_angle", v), getattr(lc, "set_inner_cone_angle", None)):
            if fn:
                try:
                    fn(float(inner_cone))
                except Exception:
                    pass
    if outer_cone is not None:
        for fn in (lambda v: lc.set_editor_property("outer_cone_angle", v), getattr(lc, "set_outer_cone_angle", None)):
            if fn:
                try:
                    fn(float(outer_cone))
                except Exception:
                    pass


def tune_post_process_grading(label, contrast=1.0, shadow_gamma=None, slope=None, toe=None, shoulder=None):
    for a in actor_sub.get_all_level_actors():
        if isinstance(a, unreal.PostProcessVolume) and a.get_actor_label() == label:
            s = a.settings
            s.override_color_contrast = True
            s.color_contrast = unreal.Vector4(contrast, contrast, contrast, 1.0)
            if shadow_gamma is not None:
                s.override_color_gamma_shadows = True
                s.color_gamma_shadows = unreal.Vector4(*shadow_gamma)
            if slope is not None:
                s.override_film_slope = True
                s.film_slope = float(slope)
            if toe is not None:
                s.override_film_toe = True
                s.film_toe = float(toe)
            if shoulder is not None:
                s.override_film_shoulder = True
                s.film_shoulder = float(shoulder)
            a.settings = s
            break


def build_f09_water_material():
    mat = get_or_create_material("/Game/ThirdParty/F09/Custom", "M_F09_Water")
    mat.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
    mat.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_DEFAULT_LIT)
    # Render ONLY top water surface; hide vertical sides and submerged bottom of 5.37m water box
    mat.set_editor_property("two_sided", False)
    try:
        mat.set_editor_property("translucency_lighting_mode", unreal.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING)
    except Exception:
        try:
            mat.set_editor_property("translucency_lighting_mode", unreal.TranslucencyLightingMode.TLM_SURFACE)
        except Exception:
            pass

    # 1. Top-face mask via PixelNormalWS.Z > 0.35
    pn = mel.create_material_expression(mat, unreal.MaterialExpressionPixelNormalWS, -1100, 420)
    pn_z = mel.create_material_expression(mat, unreal.MaterialExpressionComponentMask, -900, 420)
    pn_z.set_editor_property("r", False)
    pn_z.set_editor_property("g", False)
    pn_z.set_editor_property("b", True)
    pn_z.set_editor_property("a", False)
    assert mel.connect_material_expressions(pn, "", pn_z, "")

    top_ss = mel.create_material_expression(mat, unreal.MaterialExpressionSmoothStep, -700, 420)
    assert mel.connect_material_expressions(make_const(mat, 0.35, -880, 500), "", top_ss, "Min")
    assert mel.connect_material_expressions(make_const(mat, 0.65, -880, 560), "", top_ss, "Max")
    assert mel.connect_material_expressions(pn_z, "", top_ss, "Value")

    # 2. Optical depth absorption: SceneDepth - PixelDepth (cm underwater column)
    sd = mel.create_material_expression(mat, unreal.MaterialExpressionSceneDepth, -1120, 120)
    pd = mel.create_material_expression(mat, unreal.MaterialExpressionPixelDepth, -1120, 220)
    diff = mel.create_material_expression(mat, unreal.MaterialExpressionSubtract, -920, 160)
    assert mel.connect_material_expressions(sd, "R", diff, "A")
    assert mel.connect_material_expressions(pd, "R", diff, "B")

    diff_pos = mel.create_material_expression(mat, unreal.MaterialExpressionMax, -760, 160)
    assert mel.connect_material_expressions(diff, "", diff_pos, "A")
    assert mel.connect_material_expressions(make_const(mat, 0.0, -900, 260), "", diff_pos, "B")

    norm_depth = mel.create_material_expression(mat, unreal.MaterialExpressionDivide, -600, 160)
    assert mel.connect_material_expressions(diff_pos, "", norm_depth, "A")
    assert mel.connect_material_expressions(make_const(mat, 145.0, -760, 260), "", norm_depth, "B")

    sat_depth = mel.create_material_expression(mat, unreal.MaterialExpressionSaturate, -450, 160)
    assert mel.connect_material_expressions(norm_depth, "", sat_depth, "")

    depth_t = mel.create_material_expression(mat, unreal.MaterialExpressionPower, -300, 160)
    assert mel.connect_material_expressions(sat_depth, "", depth_t, "Base")
    assert mel.connect_material_expressions(make_const(mat, 0.65, -450, 260), "", depth_t, "Exp")

    # 3. Color: shallow emerald-cyan (cleft glow) -> deep abyssal dark emerald -> Fresnel reflection
    fres = mel.create_material_expression(mat, unreal.MaterialExpressionFresnel, -560, -280)
    fres.set_editor_property("exponent", 4.0)
    fres.set_editor_property("base_reflect_fraction", 0.04)

    col_shallow = make_vec3(mat, 0.008, 0.28, 0.24, -560, -140)
    col_abyss = make_vec3(mat, 0.001, 0.022, 0.026, -560, -20)
    lerp_depth_col = mel.create_material_expression(mat, unreal.MaterialExpressionLinearInterpolate, -280, -80)
    assert mel.connect_material_expressions(col_shallow, "", lerp_depth_col, "A")
    assert mel.connect_material_expressions(col_abyss, "", lerp_depth_col, "B")
    assert mel.connect_material_expressions(depth_t, "", lerp_depth_col, "Alpha")

    col_graz = make_vec3(mat, 0.018, 0.135, 0.145, -280, -240)
    lerp_col = mel.create_material_expression(mat, unreal.MaterialExpressionLinearInterpolate, -100, -140)
    assert mel.connect_material_expressions(lerp_depth_col, "", lerp_col, "A")
    assert mel.connect_material_expressions(col_graz, "", lerp_col, "B")
    assert mel.connect_material_expressions(fres, "", lerp_col, "Alpha")

    # 4. Opacity: semi-clear in shallow canyon cleft (~0.56), near-opaque in deep ocean (~0.985), * top_mask
    lerp_depth_op = mel.create_material_expression(mat, unreal.MaterialExpressionLinearInterpolate, -300, 320)
    assert mel.connect_material_expressions(make_const(mat, 0.56, -480, 300), "", lerp_depth_op, "A")
    assert mel.connect_material_expressions(make_const(mat, 0.985, -480, 360), "", lerp_depth_op, "B")
    assert mel.connect_material_expressions(depth_t, "", lerp_depth_op, "Alpha")

    mul_fres_op = mel.create_material_expression(mat, unreal.MaterialExpressionMultiply, -300, 440)
    assert mel.connect_material_expressions(fres, "", mul_fres_op, "A")
    assert mel.connect_material_expressions(make_const(mat, 0.98, -480, 460), "", mul_fres_op, "B")

    max_op = mel.create_material_expression(mat, unreal.MaterialExpressionMax, -140, 360)
    assert mel.connect_material_expressions(lerp_depth_op, "", max_op, "A")
    assert mel.connect_material_expressions(mul_fres_op, "", max_op, "B")

    final_op = mel.create_material_expression(mat, unreal.MaterialExpressionMultiply, 20, 380)
    assert mel.connect_material_expressions(max_op, "", final_op, "A")
    assert mel.connect_material_expressions(top_ss, "", final_op, "B")

    # 5. Dual-scale VectorNoise ripple tangent normal (WorldPos * 0.015 + WorldPos * 0.065)
    wp_n = mel.create_material_expression(mat, unreal.MaterialExpressionWorldPosition, -1100, -480)
    sc1 = mel.create_material_expression(mat, unreal.MaterialExpressionMultiply, -900, -520)
    assert mel.connect_material_expressions(wp_n, "", sc1, "A")
    assert mel.connect_material_expressions(make_const(mat, 0.015, -1080, -580), "", sc1, "B")
    vn1 = mel.create_material_expression(mat, unreal.MaterialExpressionVectorNoise, -720, -520)
    try:
        vn1.set_editor_property("noise_function", unreal.VectorNoiseFunction.VNF_VECTOR_ALU)
    except Exception:
        pass
    assert mel.connect_material_expressions(sc1, "", vn1, "World Position")

    sc2 = mel.create_material_expression(mat, unreal.MaterialExpressionMultiply, -900, -400)
    assert mel.connect_material_expressions(wp_n, "", sc2, "A")
    assert mel.connect_material_expressions(make_const(mat, 0.065, -1080, -380), "", sc2, "B")
    vn2 = mel.create_material_expression(mat, unreal.MaterialExpressionVectorNoise, -720, -400)
    try:
        vn2.set_editor_property("noise_function", unreal.VectorNoiseFunction.VNF_VECTOR_ALU)
    except Exception:
        pass
    assert mel.connect_material_expressions(sc2, "", vn2, "World Position")

    vn2_w = mel.create_material_expression(mat, unreal.MaterialExpressionMultiply, -540, -400)
    assert mel.connect_material_expressions(vn2, "", vn2_w, "A")
    assert mel.connect_material_expressions(make_const(mat, 0.45, -700, -320), "", vn2_w, "B")

    vn_sum = mel.create_material_expression(mat, unreal.MaterialExpressionAdd, -380, -480)
    assert mel.connect_material_expressions(vn1, "", vn_sum, "A")
    assert mel.connect_material_expressions(vn2_w, "", vn_sum, "B")

    vn_xy = mel.create_material_expression(mat, unreal.MaterialExpressionComponentMask, -240, -480)
    vn_xy.set_editor_property("r", True)
    vn_xy.set_editor_property("g", True)
    vn_xy.set_editor_property("b", False)
    vn_xy.set_editor_property("a", False)
    assert mel.connect_material_expressions(vn_sum, "", vn_xy, "")

    vn_xy_s = mel.create_material_expression(mat, unreal.MaterialExpressionMultiply, -110, -480)
    assert mel.connect_material_expressions(vn_xy, "", vn_xy_s, "A")
    assert mel.connect_material_expressions(make_const(mat, 0.055, -240, -380), "", vn_xy_s, "B")

    norm_app = mel.create_material_expression(mat, unreal.MaterialExpressionAppendVector, 30, -480)
    assert mel.connect_material_expressions(vn_xy_s, "", norm_app, "A")
    assert mel.connect_material_expressions(make_const(mat, 1.0, -100, -380), "", norm_app, "B")

    rough = make_const(mat, 0.08, 20, 40)
    spec = make_const(mat, 0.94, 20, 120)
    met = make_const(mat, 0.06, 20, -220)

    assert mel.connect_material_property(lerp_col, "", unreal.MaterialProperty.MP_BASE_COLOR)
    assert mel.connect_material_property(met, "", unreal.MaterialProperty.MP_METALLIC)
    assert mel.connect_material_property(spec, "", unreal.MaterialProperty.MP_SPECULAR)
    assert mel.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
    assert mel.connect_material_property(final_op, "", unreal.MaterialProperty.MP_OPACITY)
    assert mel.connect_material_property(norm_app, "", unreal.MaterialProperty.MP_NORMAL)
    mel.recompile_material(mat)
    eal.save_loaded_asset(mat)
    return mat


def build_f09_card_material():
    """Translucent card material with parameterized alpha smoothstep cutoff to remove box border haze."""
    mat = get_or_create_material("/Game/ThirdParty/F09/Custom", "M_F09_CardAlpha")
    mat.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
    mat.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_DEFAULT_LIT)
    mat.set_editor_property("two_sided", True)
    try:
        mat.set_editor_property("translucency_lighting_mode", unreal.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING)
    except Exception:
        pass

    tex_p = mel.create_material_expression(mat, unreal.MaterialExpressionTextureSampleParameter2D, -720, 0)
    tex_p.set_editor_property("parameter_name", "BaseColorTexture")
    default_tex = eal.load_asset("/Game/ThirdParty/F09/White_Lands_ue/Textures/Cloud")
    if default_tex:
        tex_p.set_editor_property("texture", default_tex)

    cut_min = mel.create_material_expression(mat, unreal.MaterialExpressionScalarParameter, -720, 220)
    cut_min.set_editor_property("parameter_name", "CutMin")
    cut_min.set_editor_property("default_value", 0.16)

    cut_max = mel.create_material_expression(mat, unreal.MaterialExpressionScalarParameter, -720, 300)
    cut_max.set_editor_property("parameter_name", "CutMax")
    cut_max.set_editor_property("default_value", 0.88)

    ss = mel.create_material_expression(mat, unreal.MaterialExpressionSmoothStep, -480, 200)
    assert mel.connect_material_expressions(cut_min, "", ss, "Min")
    assert mel.connect_material_expressions(cut_max, "", ss, "Max")
    assert mel.connect_material_expressions(tex_p, "A", ss, "Value")

    op_sc = mel.create_material_expression(mat, unreal.MaterialExpressionScalarParameter, -480, 340)
    op_sc.set_editor_property("parameter_name", "OpacityScale")
    op_sc.set_editor_property("default_value", 0.92)

    op_mul = mel.create_material_expression(mat, unreal.MaterialExpressionMultiply, -240, 240)
    assert mel.connect_material_expressions(ss, "", op_mul, "A")
    assert mel.connect_material_expressions(op_sc, "", op_mul, "B")

    base_tint = mel.create_material_expression(mat, unreal.MaterialExpressionVectorParameter, -720, -180)
    base_tint.set_editor_property("parameter_name", "BaseColorFactor")
    base_tint.set_editor_property("default_value", unreal.LinearColor(0.95, 0.98, 1.0, 1.0))

    bc_mul = mel.create_material_expression(mat, unreal.MaterialExpressionMultiply, -340, -80)
    assert mel.connect_material_expressions(tex_p, "RGB", bc_mul, "A")
    assert mel.connect_material_expressions(base_tint, "", bc_mul, "B")

    em_tint = mel.create_material_expression(mat, unreal.MaterialExpressionVectorParameter, -720, -340)
    em_tint.set_editor_property("parameter_name", "EmissiveFactor")
    em_tint.set_editor_property("default_value", unreal.LinearColor(0.25, 0.35, 0.38, 1.0))

    em_mul = mel.create_material_expression(mat, unreal.MaterialExpressionMultiply, -180, -240)
    assert mel.connect_material_expressions(bc_mul, "", em_mul, "A")
    assert mel.connect_material_expressions(em_tint, "", em_mul, "B")

    em_mask = mel.create_material_expression(mat, unreal.MaterialExpressionMultiply, -40, -180)
    assert mel.connect_material_expressions(em_mul, "", em_mask, "A")
    assert mel.connect_material_expressions(op_mul, "", em_mask, "B")

    rough = make_const(mat, 0.85, -240, 80)

    assert mel.connect_material_property(bc_mul, "", unreal.MaterialProperty.MP_BASE_COLOR)
    assert mel.connect_material_property(em_mask, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    assert mel.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
    assert mel.connect_material_property(op_mul, "", unreal.MaterialProperty.MP_OPACITY)
    mel.recompile_material(mat)
    eal.save_loaded_asset(mat)
    return mat


# ============================================================
# APPLY F09 PARITY
# ============================================================

def apply_f09():
    log("Applying F09 visual parity...")
    level_sub.load_level("/Game/Maps/F09_Unawakened")
    rep = {"removed_parity_actors": cleanup_parity_actors(), "nanite_updates": [], "lights_updated": [], "material_updates": []}

    # Disable Nanite on translucent meshes so water, clouds, wakes, birds render reliably
    for mpath in [
        "/Game/ThirdParty/F09/White_Lands_ue/StaticMeshes/water",
        "/Game/ThirdParty/F09/White_Lands_ue/StaticMeshes/Cloud",
        "/Game/ThirdParty/F09/White_Lands_ue/StaticMeshes/Cloud_006",
        "/Game/ThirdParty/F09/White_Lands_ue/StaticMeshes/Cloud_007",
        "/Game/ThirdParty/F09/White_Lands_ue/StaticMeshes/Cloud_010",
        "/Game/ThirdParty/F09/White_Lands_ue/StaticMeshes/Cloud_011",
        "/Game/ThirdParty/F09/White_Lands_ue/StaticMeshes/Cloud_012",
        "/Game/ThirdParty/F09/White_Lands_ue/StaticMeshes/Birds",
        "/Game/ThirdParty/F09/White_Lands_ue/StaticMeshes/Birds_001",
        "/Game/ThirdParty/F09/White_Lands_ue/StaticMeshes/Birds_002",
        "/Game/ThirdParty/F09/White_Lands_ue/StaticMeshes/Birds_003",
        "/Game/ThirdParty/F09/White_Lands_ue/StaticMeshes/white_water_stuff",
        "/Game/ThirdParty/F09/White_Lands_ue/StaticMeshes/white_water_stuff_002",
    ]:
        disable_nanite_on_mesh(mpath, rep["nanite_updates"])

    # Custom water material + card cutoff material + apply to water/clouds/wakes/birds
    m_water = build_f09_water_material()
    sm_water = eal.load_asset("/Game/ThirdParty/F09/White_Lands_ue/StaticMeshes/water")
    if sm_water:
        sm_water.set_material(0, m_water)
        eal.save_loaded_asset(sm_water)

    # Glacier rock/snow albedo parity (bright sunlit glacier white while filmic shoulder preserves ridge sculpt)
    for mpath, bcol, rough, nscale in [
        ("/Game/ThirdParty/F09/White_Lands_ue/Materials/snow_01", (0.84, 0.89, 0.92, 1.0), 0.72, 7.5),
        ("/Game/ThirdParty/F09/White_Lands_ue/Materials/snow_02", (0.80, 0.85, 0.89, 1.0), 0.76, 3.0),
    ]:
        mi = eal.load_asset(mpath)
        if mi:
            mel.set_material_instance_vector_parameter_value(mi, "BaseColorFactor", unreal.LinearColor(*bcol))
            mel.set_material_instance_scalar_parameter_value(mi, "RoughnessFactor", rough)
            mel.set_material_instance_scalar_parameter_value(mi, "NormalScale", nscale)
            mel.update_material_instance(mi)
            eal.save_loaded_asset(mi)
            rep["material_updates"].append({"mat": mpath, "BaseColorFactor": list(bcol), "NormalScale": nscale})

    # Clean card alpha smoothing (removes 30/255 rectangular haze on Cloud_007 & ship wakes)
    m_card = build_f09_card_material()
    card_tuning = {
        "/Game/ThirdParty/F09/White_Lands_ue/Materials/birds1": (0.18, 0.82, 0.95, (0.95, 0.98, 1.0, 1.0), (0.35, 0.42, 0.48, 1.0)),
        "/Game/ThirdParty/F09/White_Lands_ue/Materials/birds1_001": (0.18, 0.82, 0.95, (0.95, 0.98, 1.0, 1.0), (0.30, 0.36, 0.42, 1.0)),
        "/Game/ThirdParty/F09/White_Lands_ue/Materials/birds1_002": (0.18, 0.82, 0.95, (0.95, 0.98, 1.0, 1.0), (0.30, 0.36, 0.42, 1.0)),
        "/Game/ThirdParty/F09/White_Lands_ue/Materials/birds1_003": (0.18, 0.82, 0.95, (0.95, 0.98, 1.0, 1.0), (0.30, 0.36, 0.42, 1.0)),
        "/Game/ThirdParty/F09/White_Lands_ue/Materials/Cloud": (0.18, 0.90, 0.72, (0.95, 0.98, 1.0, 1.0), (0.14, 0.18, 0.22, 1.0)),
        "/Game/ThirdParty/F09/White_Lands_ue/Materials/Cloud_001": (0.20, 0.90, 0.74, (0.85, 0.95, 0.98, 1.0), (0.16, 0.24, 0.28, 1.0)),
        "/Game/ThirdParty/F09/White_Lands_ue/Materials/ship_wake": (0.12, 0.84, 0.88, (0.90, 0.96, 0.98, 1.0), (0.15, 0.26, 0.30, 1.0)),
        "/Game/ThirdParty/F09/White_Lands_ue/Materials/ship_wake_002": (0.14, 0.84, 0.90, (0.92, 0.98, 1.0, 1.0), (0.17, 0.28, 0.32, 1.0)),
    }
    for mpath, (cmin, cmax, op_s, bc_f, em_f) in card_tuning.items():
        mi = eal.load_asset(mpath)
        if mi:
            tex = mel.get_material_instance_texture_parameter_value(mi, "BaseColorTexture")
            mel.set_material_instance_parent(mi, m_card)
            if tex:
                mel.set_material_instance_texture_parameter_value(mi, "BaseColorTexture", tex)
            mel.set_material_instance_scalar_parameter_value(mi, "CutMin", cmin)
            mel.set_material_instance_scalar_parameter_value(mi, "CutMax", cmax)
            mel.set_material_instance_scalar_parameter_value(mi, "OpacityScale", op_s)
            mel.set_material_instance_vector_parameter_value(mi, "BaseColorFactor", unreal.LinearColor(*bc_f))
            mel.set_material_instance_vector_parameter_value(mi, "EmissiveFactor", unreal.LinearColor(*em_f))
            mel.update_material_instance(mi)
            eal.save_loaded_asset(mi)
            rep["material_updates"].append({"mat": mpath, "mode": "M_F09_CardAlpha", "CutMin": cmin})

    # Idempotent light calibration: subtle turquoise cleft fill (Caustic_light_003), suppress upper-right & wall white-clipping
    # Tuple: (intensity_cd, radius_cm, color_or_none, specular_scale, inner_cone_or_none, outer_cone_or_none)
    caustic_targets = {
        "Caustic_light": (0.9, 260.0, None, 0.0, 22.0, 46.0),
        "Caustic_light_001": (0.8, 240.0, None, 0.0, None, None),
        "Caustic_light_002": (0.8, 240.0, None, 0.0, None, None),
        "Caustic_light_003": (0.50, 320.0, (0.04, 0.72, 0.88, 1.0), 0.0, 22.0, 48.0),
        "Caustic_light_004": (0.8, 250.0, (0.04, 0.68, 0.85, 1.0), 0.0, 22.0, 45.0),
        "Caustic_light_005": (0.9, 260.0, None, 0.0, 22.0, 46.0),
    }
    for a in actor_sub.get_all_level_actors():
        lbl = a.get_actor_label()
        if isinstance(a, unreal.DirectionalLight):
            # Align sun along front-left channel with higher key intensity so sunlit fluted cliffs & snow tops render crisp white
            a.set_actor_rotation(unreal.Rotator(roll=0.0, pitch=-28.0, yaw=-132.0), False)
            lc = a.light_component
            lc.set_intensity(9.0)
            lc.set_light_color(unreal.LinearColor(1.0, 0.94, 0.82, 1.0))
            lc.set_cast_shadows(True)
            r_now = a.get_actor_rotation()
            rep["lights_updated"].append({"label": lbl, "intensity": 9.0, "rot": [round(r_now.roll, 2), round(r_now.pitch, 2), round(r_now.yaw, 2)]})
        elif isinstance(a, unreal.Light):
            lc = a.light_component
            tgt_i, tgt_r, tgt_c, tgt_spec, tgt_in, tgt_out = caustic_targets.get(lbl, (1.5, 260.0, None, 0.0, None, None))
            lc.set_intensity(tgt_i)
            configure_light_optics(lc, tgt_r, specular_scale=tgt_spec, inner_cone=tgt_in, outer_cone=tgt_out)
            if tgt_c is not None:
                lc.set_light_color(unreal.LinearColor(*tgt_c))
            rep["lights_updated"].append({"label": lbl, "new": tgt_i, "radius": tgt_r, "outer_cone": tgt_out})
        elif isinstance(a, unreal.StaticMeshActor) and lbl == "water":
            a.static_mesh_component.set_material(0, m_water)
            a.static_mesh_component.set_editor_property("disallow_nanite", True)
            a.static_mesh_component.set_cast_shadow(False)
        elif isinstance(a, unreal.StaticMeshActor) and any(k in lbl for k in ("Cloud", "Bird", "birds", "ship_wake", "white_water")):
            a.static_mesh_component.set_editor_property("disallow_nanite", True)
            a.static_mesh_component.set_cast_shadow(False)

    # SkyDome + SkyLight + ExponentialHeightFog + PostProcessVolume
    m_f09_sky = build_sky_dome_material(
        "/Game/ThirdParty/F09/Custom",
        "M_F09_SkyDome",
        low_rgb=(0.08, 0.32, 0.36),
        high_rgb=(0.68, 0.76, 0.72),
        z_low=-1200.0,
        z_high=10000.0,
    )
    sphere_mesh = eal.load_asset("/Engine/BasicShapes/Sphere")
    sky_actor = spawn_labeled(unreal.StaticMeshActor, "Parity_F09_SkyDome", (0.0, 0.0, 0.0))
    sky_smc = sky_actor.static_mesh_component
    sky_smc.set_static_mesh(sphere_mesh)
    sky_smc.set_material(0, m_f09_sky)
    sky_smc.set_cast_shadow(False)
    sky_smc.set_editor_property("disallow_nanite", True)
    sky_smc.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    sky_actor.set_actor_scale3d(unreal.Vector(900.0, 900.0, 900.0))

    sl = spawn_labeled(unreal.SkyLight, "Parity_F09_SkyLight", (0.0, 0.0, 500.0))
    slc = sl.light_component
    slc.set_editor_property("source_type", unreal.SkyLightSourceType.SLS_CAPTURED_SCENE)
    slc.set_editor_property("real_time_capture", False)
    slc.set_editor_property("sky_distance_threshold", 500.0)
    slc.set_editor_property("lower_hemisphere_is_black", False)
    slc.set_editor_property("lower_hemisphere_color", unreal.LinearColor(0.02, 0.10, 0.12, 1.0))
    slc.set_intensity(0.56)
    slc.set_light_color(unreal.LinearColor(0.42, 0.76, 0.86, 1.0))
    slc.recapture_sky()

    fog = spawn_labeled(unreal.ExponentialHeightFog, "Parity_F09_Fog", (0.0, 0.0, -300.0))
    fc = fog.component
    fc.set_fog_density(0.0018)
    fc.set_fog_height_falloff(0.18)
    fc.set_fog_inscattering_color(unreal.LinearColor(0.06, 0.25, 0.28, 1.0))
    fc.set_fog_max_opacity(0.18)
    fc.set_start_distance(1800.0)
    fc.set_fog_cutoff_distance(25000.0)

    setup_post_process("Parity_F09_PostProcess", exposure_bias=-0.80, bloom_intensity=0.18, vignette_intensity=0.18)
    tune_post_process_grading("Parity_F09_PostProcess", contrast=1.08, slope=0.88, toe=0.54, shoulder=0.52)

    level_sub.save_current_level()
    rep["saved"] = True
    return rep


# ============================================================
# APPLY F06 PARITY
# ============================================================

def apply_f06():
    log("Applying F06 visual parity...")
    level_sub.load_level("/Game/Maps/F06_SakuraDream")
    rep = {"removed_parity_actors": cleanup_parity_actors(), "nanite_updates": [], "lights_updated": [], "material_updates": []}

    for mpath in [
        "/Game/ThirdParty/F06/02-foliage/01-foliage/StaticMeshes/Plane_004",
        "/Game/ThirdParty/F06/04-main/04-main/StaticMeshes/Circle_003",
        "/Game/ThirdParty/F06/04-main/04-main/StaticMeshes/Plane_018",
        "/Game/ThirdParty/F06/04-main/04-main/StaticMeshes/Circle",
        "/Game/ThirdParty/F06/04-main/04-main/StaticMeshes/Plane",
        "/Game/ThirdParty/F06/04-main/04-main/StaticMeshes/Plane_003",
        "/Game/ThirdParty/F06/04-main/04-main/StaticMeshes/Cylinder",
    ]:
        disable_nanite_on_mesh(mpath, rep["nanite_updates"])

    # Convert alpha-card foliage & petals & daisies to MI_Default_Mask_DS with ZERO self-emission (matches Cycles shadows & shading)
    mi_mask_ds = eal.load_asset("/InterchangeAssets/gltf/MaterialInstances/MI_Default_Mask_DS")
    mi_opaque_ds = eal.load_asset("/InterchangeAssets/gltf/MaterialInstances/MI_Default_Opaque_DS")
    assert mi_mask_ds is not None and mi_opaque_ds is not None

    mi_sakura = eal.load_asset("/Game/ThirdParty/F06/02-foliage/01-foliage/Materials/Material_001")
    if mi_sakura:
        mel.set_material_instance_parent(mi_sakura, mi_mask_ds)
        mel.set_material_instance_scalar_parameter_value(mi_sakura, "AlphaCutoff", 0.28)
        mel.set_material_instance_scalar_parameter_value(mi_sakura, "RoughnessFactor", 0.70)
        mel.set_material_instance_vector_parameter_value(mi_sakura, "BaseColorFactor", unreal.LinearColor(1.18, 0.78, 1.04, 1.0))
        # Subtle cooler lavender scatter keeps petal self-shadowing and atmospheric distance depth intact
        mel.set_material_instance_vector_parameter_value(mi_sakura, "EmissiveFactor", unreal.LinearColor(0.34, 0.28, 0.65, 1.0))
        mel.set_material_instance_scalar_parameter_value(mi_sakura, "EmissiveStrength", 0.05)
        mel.update_material_instance(mi_sakura)
        eal.save_loaded_asset(mi_sakura)
        rep["material_updates"].append({"mat": "Material_001", "mode": "MI_Default_Mask_DS", "EmissiveStrength": 0.05})

    for mpath, bcol, ecol, estr in [
        ("/Game/ThirdParty/F06/04-main/04-main/Materials/Grass", (0.48, 0.56, 0.34, 1.0), (0.14, 0.16, 0.24, 1.0), 0.01),
        ("/Game/ThirdParty/F06/04-main/04-main/Materials/Daisy", (0.76, 0.76, 0.78, 1.0), (0.30, 0.28, 0.42, 1.0), 0.01),
    ]:
        mi = eal.load_asset(mpath)
        if mi:
            mel.set_material_instance_parent(mi, mi_mask_ds)
            mel.set_material_instance_scalar_parameter_value(mi, "AlphaCutoff", 0.30)
            mel.set_material_instance_vector_parameter_value(mi, "BaseColorFactor", unreal.LinearColor(*bcol))
            mel.set_material_instance_vector_parameter_value(mi, "EmissiveFactor", unreal.LinearColor(*ecol))
            mel.set_material_instance_scalar_parameter_value(mi, "EmissiveStrength", estr)
            mel.update_material_instance(mi)
            eal.save_loaded_asset(mi)
            rep["material_updates"].append({"mat": mpath, "mode": "MI_Default_Mask_DS", "EmissiveStrength": estr})

    # Restore Blender ShaderNodeMix / HSV / ColorRamp albedos dropped during glTF export
    opaque_albedo_parity = [
        ("/Game/ThirdParty/F06/03-pagoda/02-pagoda/Materials/Pagoda_wood_red", (0.36, 0.085, 0.095, 1.0), 0.62),
        ("/Game/ThirdParty/F06/03-pagoda/02-pagoda/Materials/Pagoda_wood_yellow", (0.64, 0.36, 0.08, 1.0), 0.58),
        ("/Game/ThirdParty/F06/03-pagoda/02-pagoda/Materials/Pagoda_wood_green", (0.045, 0.165, 0.125, 1.0), 0.56),
        ("/Game/ThirdParty/F06/03-pagoda/02-pagoda/Materials/Pagoda_wood_white", (0.68, 0.64, 0.64, 1.0), 0.68),
        ("/Game/ThirdParty/F06/03-pagoda/02-pagoda/Materials/Pagoda_roof_green", (0.055, 0.160, 0.140, 1.0), 0.52),
        ("/Game/ThirdParty/F06/03-pagoda/02-pagoda/Materials/Pagoda_fence_green", (0.055, 0.21, 0.175, 1.0), 0.48),
        ("/Game/ThirdParty/F06/03-pagoda/02-pagoda/Materials/Pagoda_gold", (0.48, 0.34, 0.15, 1.0), 0.34),
        ("/Game/ThirdParty/F06/02-foliage/01-foliage/Materials/Cinnamomum_camphora_Bark_001", (0.32, 0.30, 0.34, 1.0), 0.85),
        ("/Game/ThirdParty/F06/01-stairs/03-stairs/Materials/yellow_stone_wall", (0.48, 0.46, 0.48, 1.0), 0.86),
        ("/Game/ThirdParty/F06/04-main/04-main/Materials/yellow_stone_wall", (0.48, 0.46, 0.48, 1.0), 0.86),
        ("/Game/ThirdParty/F06/04-main/04-main/Materials/Ground_mossy", (0.46, 0.48, 0.44, 1.0), 0.88),
        ("/Game/ThirdParty/F06/04-main/04-main/Materials/Concrete", (0.46, 0.46, 0.48, 1.0), 0.84),
        ("/Game/ThirdParty/F06/04-main/04-main/Materials/Oak", (0.45, 0.40, 0.38, 1.0), 0.84),
        ("/Game/ThirdParty/F06/04-main/04-main/Materials/Lantern_wood", (0.44, 0.40, 0.38, 1.0), 0.82),
    ]
    for mpath, bcol, rough in opaque_albedo_parity:
        mi = eal.load_asset(mpath)
        if mi:
            mel.set_material_instance_vector_parameter_value(mi, "BaseColorFactor", unreal.LinearColor(*bcol))
            mel.set_material_instance_scalar_parameter_value(mi, "RoughnessFactor", rough)
            mel.update_material_instance(mi)
            eal.save_loaded_asset(mi)
            rep["material_updates"].append({"mat": mpath, "BaseColorFactor": list(bcol), "RoughnessFactor": rough})

    # Switch Lantern_paper to MI_Default_Opaque_DS so soft warm cream-peach glow stays balanced
    mi_lantern = eal.load_asset("/Game/ThirdParty/F06/04-main/04-main/Materials/Lantern_paper")
    if mi_lantern:
        tex_b = mel.get_material_instance_texture_parameter_value(mi_lantern, "BaseColorTexture")
        tex_r = mel.get_material_instance_texture_parameter_value(mi_lantern, "MetallicRoughnessTexture")
        tex_n = mel.get_material_instance_texture_parameter_value(mi_lantern, "NormalTexture")
        mel.set_material_instance_parent(mi_lantern, mi_opaque_ds)
        if tex_b:
            mel.set_material_instance_texture_parameter_value(mi_lantern, "BaseColorTexture", tex_b)
        if tex_r:
            mel.set_material_instance_texture_parameter_value(mi_lantern, "MetallicRoughnessTexture", tex_r)
        if tex_n:
            mel.set_material_instance_texture_parameter_value(mi_lantern, "NormalTexture", tex_n)
        mel.set_material_instance_vector_parameter_value(mi_lantern, "BaseColorFactor", unreal.LinearColor(0.95, 0.58, 0.24, 1.0))
        mel.set_material_instance_vector_parameter_value(mi_lantern, "EmissiveFactor", unreal.LinearColor(1.0, 0.62, 0.28, 1.0))
        mel.set_material_instance_scalar_parameter_value(mi_lantern, "EmissiveStrength", 0.42)
        mel.set_material_instance_scalar_parameter_value(mi_lantern, "RoughnessFactor", 0.88)
        mel.update_material_instance(mi_lantern)
        eal.save_loaded_asset(mi_lantern)
        rep["material_updates"].append({"mat": "Lantern_paper", "EmissiveStrength": 0.42})

    # Custom Moon & Background Gradient materials
    m_moon = build_f06_moon_material()
    sm_moon = eal.load_asset("/Game/ThirdParty/F06/04-main/04-main/StaticMeshes/Plane")
    if sm_moon:
        sm_moon.set_material(0, m_moon)
        eal.save_loaded_asset(sm_moon)

    m_grad = build_f06_gradient_material()
    sm_grad = eal.load_asset("/Game/ThirdParty/F06/04-main/04-main/StaticMeshes/Plane_003")
    if sm_grad:
        sm_grad.set_material(0, m_grad)
        eal.save_loaded_asset(sm_grad)

    # Calibrate 23 PointLights cleanly to Cycles scale (gentle peach-gold pagoda windows, finite radii, low specular glare)
    for a in actor_sub.get_all_level_actors():
        lbl = a.get_actor_label()
        if isinstance(a, unreal.PointLight):
            lc = a.light_component
            if lbl in ("Point_10", "Point_11"):
                lc.set_use_temperature(False)
                lc.set_light_color(unreal.LinearColor(0.30, 0.52, 1.0, 1.0))
                lc.set_intensity(250.0)
                configure_light_optics(lc, 3000.0, specular_scale=0.20)
                rep["lights_updated"].append({"label": lbl, "role": "moon_blue_fill", "intensity": 250.0, "radius": 3000.0})
            elif lbl in ("Point_1", "Point_2", "Point_3"):
                lc.set_use_temperature(True)
                lc.set_temperature(2500.0)
                lc.set_intensity(14.0)
                configure_light_optics(lc, 620.0, specular_scale=0.15)
                rep["lights_updated"].append({"label": lbl, "role": "pagoda_core", "intensity": 14.0, "radius": 620.0})
            elif lbl.startswith("Lantern_point"):
                lc.set_use_temperature(True)
                lc.set_temperature(2450.0)
                lc.set_intensity(9.0)
                configure_light_optics(lc, 280.0, specular_scale=0.15)
            elif lbl.startswith("Stone_lantern"):
                lc.set_use_temperature(True)
                lc.set_temperature(2400.0)
                lc.set_intensity(4.5)
                configure_light_optics(lc, 280.0, specular_scale=0.15)
            else:
                # Point_4..Point_9
                lc.set_use_temperature(True)
                lc.set_temperature(2450.0)
                lc.set_intensity(9.5)
                configure_light_optics(lc, 480.0, specular_scale=0.15)
        elif isinstance(a, unreal.StaticMeshActor):
            smc = a.static_mesh_component
            if lbl == "Moon_decal":
                smc.set_material(0, m_moon)
                smc.set_editor_property("disallow_nanite", True)
                smc.set_cast_shadow(False)
            elif lbl == "Background_gradient":
                smc.set_material(0, m_grad)
                smc.set_editor_property("disallow_nanite", True)
                smc.set_cast_shadow(False)
            elif lbl.startswith("Lantern"):
                smc.set_editor_property("disallow_nanite", True)

    # Twilight periwinkle SkyDome + SkyLight + distant misty lavender Fog (starts behind stairs) + soft dreamy PostProcess
    m_f06_sky = build_sky_dome_material(
        "/Game/ThirdParty/F06/Custom",
        "M_F06_SkyDome",
        low_rgb=(0.26, 0.34, 0.76),
        high_rgb=(0.50, 0.60, 0.94),
        z_low=-1000.0,
        z_high=18000.0,
    )
    sphere_mesh = eal.load_asset("/Engine/BasicShapes/Sphere")
    sky_actor = spawn_labeled(unreal.StaticMeshActor, "Parity_F06_SkyDome", (0.0, 0.0, 0.0))
    sky_smc = sky_actor.static_mesh_component
    sky_smc.set_static_mesh(sphere_mesh)
    sky_smc.set_material(0, m_f06_sky)
    sky_smc.set_cast_shadow(False)
    sky_smc.set_editor_property("disallow_nanite", True)
    sky_smc.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    sky_actor.set_actor_scale3d(unreal.Vector(900.0, 900.0, 900.0))

    sl = spawn_labeled(unreal.SkyLight, "Parity_F06_SkyLight", (0.0, 0.0, 500.0))
    slc = sl.light_component
    slc.set_editor_property("source_type", unreal.SkyLightSourceType.SLS_CAPTURED_SCENE)
    slc.set_editor_property("real_time_capture", False)
    slc.set_editor_property("sky_distance_threshold", 500.0)
    slc.set_editor_property("lower_hemisphere_is_black", False)
    slc.set_editor_property("lower_hemisphere_color", unreal.LinearColor(0.22, 0.24, 0.52, 1.0))
    slc.set_intensity(1.30)
    slc.set_light_color(unreal.LinearColor(0.58, 0.70, 1.0, 1.0))
    slc.recapture_sky()

    fog = spawn_labeled(unreal.ExponentialHeightFog, "Parity_F06_Fog", (0.0, 0.0, -400.0))
    fc = fog.component
    fc.set_fog_density(0.0140)
    fc.set_fog_height_falloff(0.12)
    fc.set_fog_inscattering_color(unreal.LinearColor(0.46, 0.56, 1.0, 1.0))
    fc.set_fog_max_opacity(0.66)
    fc.set_start_distance(2250.0)
    fc.set_fog_cutoff_distance(25000.0)

    setup_post_process("Parity_F06_PostProcess", exposure_bias=0.06, bloom_intensity=0.28, vignette_intensity=0.26)
    tune_post_process_grading(
        "Parity_F06_PostProcess",
        contrast=1.06,
        shadow_gamma=(1.02, 1.01, 1.04, 1.0),
        slope=0.84,
        toe=0.46,
        shoulder=0.45,
    )

    level_sub.save_current_level()
    rep["saved"] = True
    return rep


def import_butterfly_v2():
    log("Importing Butterfly.v2.glb into /Game/DreamCore/Butterfly...")
    import hashlib
    src = Path("E:/紫萱2版/Assets/Original/Butterfly/Butterfly.v2.glb")
    dest = "/Game/DreamCore/Butterfly"
    assets = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
    existing = list(assets.list_assets(dest, recursive=True)) if assets.does_directory_exist(dest) else []
    if not existing:
        manager = unreal.InterchangeManager.get_interchange_manager_scripted()
        source_data = manager.create_source_data(str(src))
        params = unreal.ImportAssetParameters()
        params.set_editor_property("is_automated", True)
        imported_objs = manager.import_asset(dest, source_data, params)
        assets.save_directory(dest)
    final_assets = list(assets.list_assets(dest, recursive=True))
    nanite_off = []
    for ap in final_assets:
        if "/StaticMeshes/" in ap:
            disable_nanite_on_mesh(ap.split(".")[0], nanite_off)
    rep = {
        "source": str(src),
        "source_bytes": src.stat().st_size,
        "source_sha256": hashlib.sha256(src.read_bytes()).hexdigest(),
        "destination": dest,
        "assets": final_assets,
        "asset_count": len(final_assets),
        "nanite_updates": nanite_off,
        "status": "IMPORTED_AND_SAVED_AWAITING_CPP_PAWN_BINDING",
    }
    ev_dir = Path("E:/紫萱2版/Evidence/Unreal/Butterfly")
    ev_dir.mkdir(parents=True, exist_ok=True)
    (ev_dir / "import-result.json").write_text(json.dumps(rep, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return rep


result = {}
for name, fn in [("F09", apply_f09), ("F06", apply_f06), ("Butterfly", import_butterfly_v2)]:
    try:
        result[name] = fn()
    except Exception:
        result[name] = {"error": traceback.format_exc()}

REPORT_PATH.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
Path("E:/紫萱2版/Evidence/Unreal/parity-apply-report.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
log(f"DONE report={REPORT_PATH}")
