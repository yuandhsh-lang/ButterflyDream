#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "ButterflyParticleSwarmActor.generated.h"

class UInstancedStaticMeshComponent;
class UMaterialInstanceDynamic;
class UPointLightComponent;
class USceneComponent;
class UStaticMesh;

/** Procedural 3D swarm choreography modes for spirit koi, sakura petals, stardust helices & taiji rings. */
UENUM(BlueprintType)
enum class EButterflySwarmPattern : uint8
{
	OrbitalVortex      = 0 UMETA(DisplayName = "0 - Orbital Vortex (环绕漩涡)"),
	RisingHelix        = 1 UMETA(DisplayName = "1 - Rising Double Helix (升腾双螺旋)"),
	PetalCascade       = 2 UMETA(DisplayName = "2 - Petal Cascade (漫天飘落花雨)"),
	FigureEightSchool  = 3 UMETA(DisplayName = "3 - Figure-Eight School (灵鱼/仙蝶 ∞ 巡游群)")
};

/**
 * High-performance GPU-instanced 3D procedural swarm actor.
 * Animates dozens or hundreds of Lux3D meshes (Celestial_Spirit_Koi, Sakura_Spirit_Swirl,
 * Dream_Scale_Blade, etc.) via UInstancedStaticMeshComponent + Candelas aura lighting.
 */
UCLASS()
class BUTTERFLYDREAM_API AButterflyParticleSwarmActor : public AActor
{
	GENERATED_BODY()

public:
	AButterflyParticleSwarmActor();

	virtual void OnConstruction(const FTransform& Transform) override;
	virtual void BeginPlay() override;
	virtual void Tick(float DeltaSeconds) override;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components")
	TObjectPtr<USceneComponent> SceneRoot;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components")
	TObjectPtr<UInstancedStaticMeshComponent> SwarmMesh;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components")
	TObjectPtr<UPointLightComponent> CoreGlowLight;

	// ---- Editable Swarm Properties ----

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "ParticleSwarm")
	TObjectPtr<UStaticMesh> SwarmAsset;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "ParticleSwarm", meta = (ClampMin = "1", ClampMax = "512"))
	int32 InstanceCount = 36;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "ParticleSwarm", meta = (ClampMin = "20.0"))
	float SwarmRadius = 680.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "ParticleSwarm", meta = (ClampMin = "20.0"))
	float SwarmHeightSpan = 420.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "ParticleSwarm")
	float OrbitSpeedDegrees = 24.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "ParticleSwarm", meta = (ClampMin = "0.005"))
	float BaseInstanceScale = 0.35f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "ParticleSwarm")
	FLinearColor SwarmGlowColor = FLinearColor(1.0f, 0.84f, 0.48f, 1.0f);

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "ParticleSwarm", meta = (ClampMin = "0.0"))
	float SwarmLightCandelas = 120.0f;

	/** 0=OrbitalVortex, 1=RisingHelix, 2=PetalCascade, 3=FigureEightSchool */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "ParticleSwarm", meta = (ClampMin = "0", ClampMax = "3"))
	int32 MotionPattern = 0;

	/** Local mesh forward alignment yaw offset (+90 deg aligns Lux3D -Y forward glTF meshes to +X tangent). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "ParticleSwarm")
	float MeshYawOffsetDegrees = 90.0f;

	/** One-call configuration helper for Python scene assembly & Blueprints. */
	UFUNCTION(BlueprintCallable, Category = "ParticleSwarm")
	void ConfigureSwarm(
		UStaticMesh* InMesh,
		int32 Count,
		float Radius,
		float HeightSpan,
		float OrbitSpeedDeg,
		float InstanceScale,
		FLinearColor GlowColor,
		float LightCandelas,
		int32 InMotionPattern);

	/** Force rebuild of GPU instances after property edits. */
	UFUNCTION(BlueprintCallable, Category = "ParticleSwarm")
	void RebuildSwarmInstances();

private:
	struct FSwarmSeed
	{
		float Phase01 = 0.0f;
		float RadialBand = 1.0f;
		float HeightOffset01 = 0.5f;
		float ScaleJitter = 1.0f;
		float SpeedMultiplier = 1.0f;
		float LateralOffset = 0.0f;
	};

	UPROPERTY(Transient)
	TArray<TObjectPtr<UMaterialInstanceDynamic>> SwarmDynamicMaterials;

	TArray<FSwarmSeed> Seeds;
	TArray<FTransform> CachedTransforms;
	float ElapsedTime = 0.0f;

	void ComputeTransformsForTime(float TimeSeconds);
	void RefreshDynamicMaterials();
};
