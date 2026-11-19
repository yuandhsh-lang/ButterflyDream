import math
from pathlib import Path

import unreal


ROOT = Path(r'E:\紫萱2版')
ASSETS = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
ACTORS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
MATERIALS = unreal.MaterialEditingLibrary
MESHES = {
    'pavilion': '/Game/LuxGenerated/Pavilion_S01/Floating_Pavilion',
    'bridge': '/Game/LuxGenerated/Sanctuary/Celestial_Bridge',
    'guardian': '/Game/LuxGenerated/Sanctuary/Celestial_Guardian',
    'pillar': '/Game/LuxGenerated/Sanctuary/Dragon_Pillar',
    'lantern': '/Game/LuxGenerated/Props/Floating_Lantern',
    'lotus': '/Game/LuxGenerated/Props/Crystal_Lotus',
    'mountain': '/Game/LuxGenerated/Extra/Ink_Cloud_Mountain_Complex',
    'guqin': '/Game/LuxGenerated/Extra/Luminous_Guqin_Bridge',
    'pagoda': '/Game/LuxGenerated/Extra/Seven_Tier_Crystal_Pagoda',
    'garden': '/Game/LuxGenerated/Extra/Floating_Crystal_Garden',
    'taiji': '/Game/LuxGenerated/Extra/Taiji_Star_Sphere',
    'ink_portal': '/Game/LuxGenerated/Extra/Ink_Ripple_Portal',
    'crystal_portal': '/Game/LuxGenerated/Extra/Crystal_Prism_Portal',
    'scroll_gate': '/Game/LuxGenerated/Extra/Celestial_Scroll_Gate',
}


def vec(x, y, z):
    return unreal.Vector(float(x), float(y), float(z))


def rot(pitch=0.0, yaw=0.0, roll=0.0):
    return unreal.Rotator(roll=float(roll), pitch=float(pitch), yaw=float(yaw))


def color(r, g, b, a=1.0):
    return unreal.LinearColor(float(r), float(g), float(b), float(a))


def set_prop(obj, name, value):
    obj.set_editor_property(name, value)


def load(path, expected_class):
    asset = ASSETS.load_asset(path)
    if not asset or not isinstance(asset, expected_class):
        raise RuntimeError(f'Required asset is missing or has wrong type: {path}')
    return asset


def load_mesh(key_or_path):
    path = MESHES.get(key_or_path, key_or_path)
    return load(path, unreal.StaticMesh)


def save(asset):
    if not ASSETS.save_loaded_asset(asset, False):
        raise RuntimeError(f'Failed to save {asset.get_path_name()}')


def restore_scene_materials():
    # The sanctuary and extra-scene GLBs share an opaque, non-emissive material layout,
    # with UV0 base color, packed roughness G / metallic B, and metallicFactor 0.1.
    bindings = []
    for key in MESHES:
        mesh = load_mesh(key)
        for slot in mesh.get_editor_property('static_materials'):
            instance = slot.material_interface
            if not isinstance(instance, unreal.MaterialInstanceConstant):
                raise RuntimeError(f'Missing imported material instance on {mesh.get_path_name()}')
            base = MATERIALS.get_material_instance_texture_parameter_value(instance, 'BaseColorTexture')
            packed = MATERIALS.get_material_instance_texture_parameter_value(instance, 'MetallicRoughnessTexture')
            if not base or not packed:
                raise RuntimeError(f'Missing GLB textures on {instance.get_path_name()}')
            bindings.append((instance, base, packed))

    folder = '/Game/LuxGenerated/Materials/FourRealms'
    name = 'M_LuxScenePBR'
    if ASSETS.does_asset_exist(f'{folder}/{name}'):
        parent = load(f'{folder}/{name}', unreal.Material)
    else:
        parent = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            name, folder, unreal.Material, unreal.MaterialFactoryNew())
        if not parent:
            raise RuntimeError(f'Could not create {folder}/{name}')
        _, base, packed = bindings[0]
        base_sample = MATERIALS.create_material_expression(
            parent, unreal.MaterialExpressionTextureSampleParameter2D, -540, -120)
        base_sample.set_editor_property('parameter_name', 'BaseColorTexture')
        base_sample.set_editor_property('texture', base)
        packed_sample = MATERIALS.create_material_expression(
            parent, unreal.MaterialExpressionTextureSampleParameter2D, -540, 120)
        packed_sample.set_editor_property('parameter_name', 'MetallicRoughnessTexture')
        packed_sample.set_editor_property('texture', packed)
        sampler = unreal.MaterialSamplerType
        packed_sample.set_editor_property(
            'sampler_type', sampler.SAMPLERTYPE_MASKS
            if packed.get_editor_property('compression_settings') == unreal.TextureCompressionSettings.TC_MASKS
            else sampler.SAMPLERTYPE_LINEAR_COLOR)
        metallic = MATERIALS.create_material_expression(parent, unreal.MaterialExpressionMultiply, -230, 200)
        metallic.set_editor_property('const_b', 0.1)
        specular = MATERIALS.create_material_expression(parent, unreal.MaterialExpressionConstant, -230, 340)
        specular.set_editor_property('r', 0.35)
        if not MATERIALS.connect_material_expressions(packed_sample, 'B', metallic, 'A'):
            raise RuntimeError('Could not bind GLB metallic channel')
        for expression, output, prop in (
            (base_sample, 'RGB', unreal.MaterialProperty.MP_BASE_COLOR),
            (packed_sample, 'G', unreal.MaterialProperty.MP_ROUGHNESS),
            (metallic, '', unreal.MaterialProperty.MP_METALLIC),
            (specular, '', unreal.MaterialProperty.MP_SPECULAR),
        ):
            if not MATERIALS.connect_material_property(expression, output, prop):
                raise RuntimeError(f'Could not connect {prop} on {name}')
        parent.set_editor_property('two_sided', True)
        MATERIALS.set_material_usage(parent, unreal.MaterialUsage.MATUSAGE_NANITE)
        MATERIALS.recompile_material(parent)
        save(parent)

    for instance, base, packed in bindings:
        if instance.get_editor_property('parent') == parent:
            continue
        MATERIALS.set_material_instance_parent(instance, parent)
        for name, texture in (('BaseColorTexture', base), ('MetallicRoughnessTexture', packed)):
            MATERIALS.set_material_instance_texture_parameter_value(instance, name, texture)
            if MATERIALS.get_material_instance_texture_parameter_value(instance, name) != texture:
                raise RuntimeError(f'GLB texture readback failed: {instance.get_path_name()} {name}')
        MATERIALS.update_material_instance(instance)
        save(instance)


def spawn_base_collision(label, location, size):
    cube = load('/Engine/BasicShapes/Cube', unreal.StaticMesh)
    actor = ACTORS.spawn_actor_from_class(unreal.StaticMeshActor, location, rot())
    actor.set_actor_label(label)
    smc = actor.static_mesh_component
    smc.set_static_mesh(cube)
    actor.set_actor_scale3d(vec(size.x / 100.0, size.y / 100.0, size.z / 100.0))
    smc.set_collision_profile_name('BlockAll')
    smc.set_collision_enabled(unreal.CollisionEnabled.QUERY_AND_PHYSICS)
    smc.set_cast_shadow(False)
    actor.set_actor_hidden_in_game(True)
    return actor


def spawn_static(label, mesh_key, location, yaw=0.0, target_height=None, target_span=None, base_collision=False):
    mesh = load_mesh(mesh_key)
    nanite = mesh.get_editor_property('nanite_settings')
    if mesh.get_num_triangles(0) >= 80000 and not nanite.get_editor_property('enabled'):
        nanite.set_editor_property('enabled', True)
        mesh.set_editor_property('nanite_settings', nanite)
        save(mesh)
    actor = ACTORS.spawn_actor_from_class(unreal.StaticMeshActor, location, rot(yaw=yaw))
    actor.set_actor_label(label)
    actor.static_mesh_component.set_static_mesh(mesh)
    box = mesh.get_bounding_box()
    size = box.max - box.min
    height = max(float(size.z), 1.0)
    span = max(float(size.x), float(size.y), float(size.z), 1.0)
    scale = float(target_height) / height if target_height is not None else float(target_span) / span if target_span is not None else 1.0
    actor.set_actor_scale3d(vec(scale, scale, scale))
    actor.static_mesh_component.set_collision_profile_name('NoCollision')
    if base_collision:
        base_size = vec(
            max(60.0, float(size.x) * scale * 0.55),
            max(60.0, float(size.y) * scale * 0.55),
            60.0,
        )
        spawn_base_collision(f'{label}_BaseCollision', vec(location.x, location.y, location.z + 30.0), base_size)
    return {'actor': actor, 'scale': scale, 'bounds': size}


def spawn_point(label, location, intensity, radius, light_color, cast_shadow=False):
    actor = ACTORS.spawn_actor_from_class(unreal.PointLight, location, rot())
    actor.set_actor_label(label)
    component = actor.light_component
    component.set_mobility(unreal.ComponentMobility.MOVABLE)
    component.set_intensity_units(unreal.LightUnits.CANDELAS)
    component.set_intensity(float(intensity))
    component.set_attenuation_radius(float(radius))
    component.set_light_color(light_color)
    component.set_cast_shadows(bool(cast_shadow))
    return actor


def create_custom_sky(name, code):
    path = f'/Game/LuxGenerated/Materials/FourRealms/{name}'
    if ASSETS.does_asset_exist(path):
        material = load(path, unreal.Material)
    else:
        material = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            name,
            '/Game/LuxGenerated/Materials/FourRealms',
            unreal.Material,
            unreal.MaterialFactoryNew(),
        )
        if not material:
            raise RuntimeError(f'Could not create sky material {path}')
        world_position = MATERIALS.create_material_expression(material, unreal.MaterialExpressionWorldPosition, -700, 0)
        normalize = MATERIALS.create_material_expression(material, unreal.MaterialExpressionNormalize, -480, 0)
        custom = MATERIALS.create_material_expression(material, unreal.MaterialExpressionCustom, -180, 0)
        custom.set_editor_property('output_type', unreal.CustomMaterialOutputType.CMOT_FLOAT3)
        custom.set_editor_property('description', f'{name}_DirectionalSky')
        direction = unreal.CustomInput()
        direction.set_editor_property('input_name', 'Dir')
        custom.set_editor_property('inputs', [direction])
        custom.set_editor_property('code', code)
        if not MATERIALS.connect_material_expressions(world_position, '', normalize, ''):
            raise RuntimeError(f'Could not connect WorldPosition for {name}')
        if not MATERIALS.connect_material_expressions(normalize, '', custom, 'Dir'):
            raise RuntimeError(f'Could not connect direction for {name}')
        if not MATERIALS.connect_material_property(custom, '', unreal.MaterialProperty.MP_EMISSIVE_COLOR):
            raise RuntimeError(f'Could not connect emissive output for {name}')
    material.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_UNLIT)
    material.set_editor_property('two_sided', True)
    material.set_editor_property('is_sky', True)
    MATERIALS.recompile_material(material)
    save(material)
    return material


def prepare_sky_material(path):
    material = load(path, unreal.Material)
    material.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_UNLIT)
    material.set_editor_property('two_sided', True)
    material.set_editor_property('is_sky', True)
    MATERIALS.recompile_material(material)
    save(material)
    return material


def spawn_sky(prefix, material):
    actor = ACTORS.spawn_actor_from_class(unreal.StaticMeshActor, vec(0, 0, 0), rot())
    actor.set_actor_label(f'{prefix}_SkyDome')
    actor.static_mesh_component.set_static_mesh(load('/Engine/BasicShapes/Sphere', unreal.StaticMesh))
    actor.static_mesh_component.set_material(0, material)
    actor.static_mesh_component.set_cast_shadow(False)
    actor.set_actor_scale3d(vec(6000, 6000, 6000))
    actor.static_mesh_component.set_collision_profile_name('NoCollision')
    return actor


def spawn_water(label, material_path, location, scale):
    actor = ACTORS.spawn_actor_from_class(unreal.StaticMeshActor, location, rot())
    actor.set_actor_label(label)
    actor.static_mesh_component.set_static_mesh(load('/Engine/BasicShapes/Plane', unreal.StaticMesh))
    actor.static_mesh_component.set_material(0, load(material_path, unreal.Material))
    actor.static_mesh_component.set_cast_shadow(False)
    actor.set_actor_scale3d(scale)
    actor.static_mesh_component.set_collision_profile_name('NoCollision')
    return actor


def configure_atmosphere(
    prefix,
    sky_material,
    sun_rotation,
    sun_intensity,
    sun_color,
    sky_intensity,
    fog_color,
    fog_density,
    fog_start,
    exposure_bias=0.0,
    bloom=0.18,
    ssr_intensity=20.0,
):
    if not sky_material.get_editor_property('is_sky'):
        raise RuntimeError(f'{sky_material.get_path_name()} is not marked IsSky')
    sun = ACTORS.spawn_actor_from_class(unreal.DirectionalLight, vec(0, 0, 1800), sun_rotation)
    sun.set_actor_label(f'{prefix}_KeyLight')
    sun.light_component.set_mobility(unreal.ComponentMobility.MOVABLE)
    sun.light_component.set_intensity(float(sun_intensity))
    sun.light_component.set_light_color(sun_color)
    sun.light_component.set_cast_shadows(True)

    sky = ACTORS.spawn_actor_from_class(unreal.SkyLight, vec(0, 0, 1500), rot())
    sky.set_actor_label(f'{prefix}_SkyLight')
    sky.light_component.set_mobility(unreal.ComponentMobility.MOVABLE)
    sky.light_component.set_intensity(float(sky_intensity))
    sky.light_component.set_editor_property('real_time_capture', True)
    sky.light_component.set_editor_property('source_type', unreal.SkyLightSourceType.SLS_CAPTURED_SCENE)
    if callable(getattr(sky.light_component, 'recapture_sky', None)):
        sky.light_component.recapture_sky()

    fog = ACTORS.spawn_actor_from_class(unreal.ExponentialHeightFog, vec(0, 0, -500), rot())
    fog.set_actor_label(f'{prefix}_Fog')
    component = fog.get_component_by_class(unreal.ExponentialHeightFogComponent)
    component.set_editor_property('fog_density', float(fog_density))
    component.set_editor_property('fog_height_falloff', 0.25)
    component.set_editor_property('fog_inscattering_luminance', fog_color)
    component.set_editor_property('start_distance', float(fog_start))
    component.set_editor_property('fog_max_opacity', 0.35)

    volume = ACTORS.spawn_actor_from_class(unreal.PostProcessVolume, vec(0, 0, 0), rot())
    volume.set_actor_label(f'{prefix}_PostProcess')
    volume.set_editor_property('unbound', True)
    settings = volume.get_editor_property('settings')
    for name, value in (
        ('override_auto_exposure_min_brightness', True),
        ('auto_exposure_min_brightness', 1.0),
        ('override_auto_exposure_max_brightness', True),
        ('auto_exposure_max_brightness', 1.0),
        ('override_auto_exposure_bias', True),
        ('auto_exposure_bias', float(exposure_bias)),
        ('override_bloom_intensity', True),
        ('bloom_intensity', float(bloom)),
        ('override_bloom_threshold', True),
        ('bloom_threshold', 1.5),
        ('override_screen_space_reflection_intensity', True),
        ('screen_space_reflection_intensity', float(ssr_intensity)),
        ('override_screen_space_reflection_quality', True),
        ('screen_space_reflection_quality', 40.0),
    ):
        settings.set_editor_property(name, value)
    volume.set_editor_property('settings', settings)
    return {'sun': sun, 'sky': sky, 'fog': fog, 'post_process': volume}


def configure_gate(
    label,
    title,
    target_map,
    location,
    yaw,
    target_height,
    aperture,
    custom_mesh_key=None,
    resonance_distance=1400.0,
):
    gate = ACTORS.spawn_actor_from_class(unreal.ButterflyDreamGateActor, location, rot(yaw=yaw))
    gate.set_actor_label(label)
    gate.apply_gate_preset(True)
    gate.set_editor_property('gate_title', title)
    gate.set_editor_property('target_map_package_name', target_map)
    gate.set_editor_property('resonance_distance', float(resonance_distance))
    gate.set_editor_property('portal_aperture_half_width', float(aperture))
    gate.set_editor_property('portal_aperture_half_height', float(aperture))
    gate.set_editor_property('traversal_capsule_radius', 10.0)
    gate.set_editor_property('traversal_capsule_half_height', 10.0)
    gate.set_editor_property('tunnel_ring_spacing_override', 0.0)

    center = vec(0, 0, 25)
    if custom_mesh_key:
        mesh = load_mesh(custom_mesh_key)
        centers = {
            'ink_portal': vec(0, 0, 27.388),
            'crystal_portal': vec(0, 0, 15.016),
            'scroll_gate': vec(0, 0, 19.978),
        }
        center = centers.get(custom_mesh_key, center)
    gate.configure_hinge_offsets(center, center, center, center)

    frame = None
    for component in gate.get_components_by_class(unreal.StaticMeshComponent):
        name = component.get_name()
        if name.startswith('GateFrameMesh'):
            frame = component
            if custom_mesh_key:
                component.set_static_mesh(load_mesh(custom_mesh_key))
                component.set_editor_property('relative_rotation', rot(yaw=180.0))
        elif name.startswith('LeftDoorMesh') and custom_mesh_key:
            component.set_visibility(False)
            component.set_hidden_in_game(True)
        elif name.startswith('VortexMote_'):
            component.set_visibility(False)
            component.set_hidden_in_game(True)
        elif name.startswith('TunnelRing_'):
            optimized = '/Game/Optimized/Tunnel_Ring_FX'
            if ASSETS.does_asset_exist(optimized):
                component.set_static_mesh(load(optimized, unreal.StaticMesh))
    frame_mesh = frame.get_editor_property('static_mesh') if frame else None
    if not frame_mesh:
        raise RuntimeError(f'No valid gate frame on {label}')
    box = frame_mesh.get_bounding_box()
    relative_scale = frame.get_editor_property('relative_scale3d')
    relative_location = frame.get_editor_property('relative_location')
    unit_height = max(1.0, float(box.max.z - box.min.z) * abs(float(relative_scale.z)))
    scale = float(target_height) / unit_height
    gate.set_actor_scale3d(vec(scale, scale, scale))
    corrected = vec(location.x, location.y, location.z - float(box.min.z) * float(relative_scale.z) * scale)
    gate.set_actor_location(corrected, False, False)

    for property_name, expected in (
        ('target_map_package_name', target_map),
        ('portal_aperture_half_width', float(aperture)),
        ('portal_aperture_half_height', float(aperture)),
    ):
        actual = gate.get_editor_property(property_name)
        matches = math.isclose(actual, expected, abs_tol=1e-5) if isinstance(expected, float) else actual == expected
        if not matches:
            raise RuntimeError(f'Gate readback failed: {label} {property_name}: {actual} != {expected}')
    return {'actor': gate, 'scale': scale, 'center': center, 'height': target_height, 'target': target_map}


def finalize_map(map_path, spawn_location, spawn_rotation):
    spawn = ACTORS.spawn_actor_from_class(unreal.PlayerStart, spawn_location, spawn_rotation)
    spawn.set_actor_label(f'{Path(map_path).name}_PlayerStart')
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    settings = world.get_world_settings()
    settings.set_editor_property('default_game_mode', unreal.ButterflyGameMode)
    settings.set_editor_property('kill_z', -2500.0)
    settings.set_editor_property('enable_world_bounds_checks', True)
    return spawn
