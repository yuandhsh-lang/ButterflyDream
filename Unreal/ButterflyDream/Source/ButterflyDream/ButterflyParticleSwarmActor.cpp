#include "ButterflyParticleSwarmActor.h"

#include "Components/InstancedStaticMeshComponent.h"
#include "Components/PointLightComponent.h"
#include "Components/SceneComponent.h"
#include "Engine/StaticMesh.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialInterface.h"
#include "UObject/ConstructorHelpers.h"

namespace ButterflySwarmParams
{
	static const FName EmissiveStrength(TEXT("EmissiveStrength"));
	static const FName EmissiveScale(TEXT("EmissiveScale"));
}

AButterflyParticleSwarmActor::AButterflyParticleSwarmActor()
{
	PrimaryActorTick.bCanEverTick = true;

	SceneRoot = CreateDefaultSubobject<USceneComponent>(TEXT("SceneRoot"));
	RootComponent = SceneRoot;

	SwarmMesh = CreateDefaultSubobject<UInstancedStaticMeshComponent>(TEXT("SwarmMesh"));
	SwarmMesh->SetupAttachment(SceneRoot);
	SwarmMesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	SwarmMesh->SetCastShadow(false);
	SwarmMesh->SetMobility(EComponentMobility::Movable);

	static ConstructorHelpers::FObjectFinder<UStaticMesh> DefaultScaleMesh(
		TEXT("/Game/LuxGenerated/Scale_T02/Dream_Scale_Blade"));
	if (DefaultScaleMesh.Succeeded())
	{
		SwarmAsset = DefaultScaleMesh.Object;
		SwarmMesh->SetStaticMesh(SwarmAsset);
	}

	CoreGlowLight = CreateDefaultSubobject<UPointLightComponent>(TEXT("CoreGlowLight"));
	CoreGlowLight->SetupAttachment(SceneRoot);
	CoreGlowLight->SetIntensityUnits(ELightUnits::Candelas);
	CoreGlowLight->SetIntensity(SwarmLightCandelas);
	CoreGlowLight->SetAttenuationRadius(1100.0f);
	CoreGlowLight->SetLightColor(SwarmGlowColor);
	CoreGlowLight->SetCastShadows(false);
}

void AButterflyParticleSwarmActor::OnConstruction(const FTransform& Transform)
{
	Super::OnConstruction(Transform);
	RebuildSwarmInstances();
}

void AButterflyParticleSwarmActor::BeginPlay()
{
	Super::BeginPlay();
	RebuildSwarmInstances();
}

void AButterflyParticleSwarmActor::ConfigureSwarm(
	UStaticMesh* InMesh,
	int32 Count,
	float Radius,
	float HeightSpan,
	float OrbitSpeedDeg,
	float InstanceScale,
	FLinearColor GlowColor,
	float LightCandelas,
	int32 InMotionPattern)
{
	if (InMesh)
	{
		SwarmAsset = InMesh;
	}
	InstanceCount = FMath::Clamp(Count, 1, 512);
	SwarmRadius = FMath::Max(20.0f, Radius);
	SwarmHeightSpan = FMath::Max(20.0f, HeightSpan);
	OrbitSpeedDegrees = OrbitSpeedDeg;
	BaseInstanceScale = FMath::Max(0.005f, InstanceScale);
	SwarmGlowColor = GlowColor;
	SwarmLightCandelas = FMath::Max(0.0f, LightCandelas);
	MotionPattern = FMath::Clamp(InMotionPattern, 0, 3);

	RebuildSwarmInstances();
}

void AButterflyParticleSwarmActor::RefreshDynamicMaterials()
{
	SwarmDynamicMaterials.Reset();
	if (!SwarmMesh || !IsValid(SwarmMesh->GetStaticMesh()))
	{
		return;
	}

	const int32 NumMats = SwarmMesh->GetNumMaterials();
	for (int32 SlotIdx = 0; SlotIdx < NumMats; ++SlotIdx)
	{
		UMaterialInterface* BaseMat = SwarmMesh->GetMaterial(SlotIdx);
		if (!BaseMat)
		{
			continue;
		}
		UMaterialInstanceDynamic* MID = Cast<UMaterialInstanceDynamic>(BaseMat);
		if (!MID)
		{
			MID = SwarmMesh->CreateDynamicMaterialInstance(SlotIdx, BaseMat);
		}
		if (MID)
		{
			MID->SetScalarParameterValue(ButterflySwarmParams::EmissiveStrength, 0.95f);
			MID->SetScalarParameterValue(ButterflySwarmParams::EmissiveScale, 0.95f);
			SwarmDynamicMaterials.Add(MID);
		}
	}
}

void AButterflyParticleSwarmActor::RebuildSwarmInstances()
{
	if (CoreGlowLight)
	{
		CoreGlowLight->SetLightColor(SwarmGlowColor);
		CoreGlowLight->SetIntensity(SwarmLightCandelas);
		CoreGlowLight->SetAttenuationRadius(FMath::Clamp(SwarmRadius * 1.65f, 450.0f, 3200.0f));
	}

	if (!SwarmMesh)
	{
		return;
	}

	if (SwarmAsset && SwarmMesh->GetStaticMesh() != SwarmAsset)
	{
		SwarmMesh->SetStaticMesh(SwarmAsset);
	}

	SwarmMesh->ClearInstances();
	Seeds.Reset();
	CachedTransforms.Reset();

	if (!IsValid(SwarmMesh->GetStaticMesh()) || InstanceCount <= 0)
	{
		return;
	}

	const int32 ClampedCount = FMath::Clamp(InstanceCount, 1, 512);
	Seeds.Reserve(ClampedCount);
	CachedTransforms.SetNum(ClampedCount);

	// Deterministic golden-ratio low-discrepancy sequence so saved maps look lush and well-spaced
	for (int32 Idx = 0; Idx < ClampedCount; ++Idx)
	{
		const float FracA = FMath::Fmod(static_cast<float>(Idx) * 0.6180339887f, 1.0f);
		const float FracB = FMath::Fmod(static_cast<float>(Idx) * 0.3819660113f + 0.17f, 1.0f);
		const float FracC = FMath::Fmod(static_cast<float>(Idx) * 0.7548776662f + 0.31f, 1.0f);

		FSwarmSeed Seed;
		Seed.Phase01 = static_cast<float>(Idx) / static_cast<float>(ClampedCount);
		Seed.RadialBand = FMath::Lerp(0.38f, 1.0f, FracA);
		Seed.HeightOffset01 = FracB;
		Seed.ScaleJitter = FMath::Lerp(0.72f, 1.28f, FracC);
		Seed.SpeedMultiplier = FMath::Lerp(0.84f, 1.18f, FracA);
		Seed.LateralOffset = FMath::Lerp(-1.0f, 1.0f, FracB);
		Seeds.Add(Seed);
	}

	ComputeTransformsForTime(ElapsedTime);
	SwarmMesh->AddInstances(CachedTransforms, false, false);
	RefreshDynamicMaterials();
}

void AButterflyParticleSwarmActor::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);

	ElapsedTime += DeltaSeconds;

	if (CoreGlowLight && SwarmLightCandelas > 0.0f)
	{
		const float Breath = 0.88f + 0.22f * (0.5f + 0.5f * FMath::Sin(ElapsedTime * 2.1f));
		CoreGlowLight->SetIntensity(SwarmLightCandelas * Breath);
	}

	if (!SwarmMesh || CachedTransforms.Num() == 0 || SwarmMesh->GetInstanceCount() != CachedTransforms.Num())
	{
		return;
	}

	ComputeTransformsForTime(ElapsedTime);
	SwarmMesh->BatchUpdateInstancesTransforms(0, CachedTransforms, false, true, true);
}

void AButterflyParticleSwarmActor::ComputeTransformsForTime(float TimeSeconds)
{
	const int32 Count = Seeds.Num();
	if (Count <= 0 || CachedTransforms.Num() != Count)
	{
		return;
	}

	const float AngularVelRad = FMath::DegreesToRadians(OrbitSpeedDegrees);
	const float HalfHeight = SwarmHeightSpan * 0.5f;

	for (int32 Idx = 0; Idx < Count; ++Idx)
	{
		const FSwarmSeed& Seed = Seeds[Idx];
		FVector Pos = FVector::ZeroVector;
		FRotator Rot = FRotator::ZeroRotator;
		float ScaleFactor = BaseInstanceScale * Seed.ScaleJitter;

		switch (MotionPattern)
		{
		case 1: // RisingHelix — twin intertwined ascending helices
		{
			const float StrandOffset = (Idx % 2 == 0) ? 0.0f : PI;
			const float RiseRate = FMath::Max(0.04f, FMath::Abs(OrbitSpeedDegrees) * 0.0045f) * Seed.SpeedMultiplier;
			const float Height01 = FMath::Fmod(Seed.HeightOffset01 + TimeSeconds * RiseRate, 1.0f);
			const float Envelope = FMath::Sin(Height01 * PI); // 0 -> 1 -> 0 seamless wrap taper
			const float Angle = TimeSeconds * AngularVelRad * 1.4f + Height01 * 4.0f * PI + StrandOffset;
			const float DynamicRadius = SwarmRadius * FMath::Lerp(0.75f, 1.08f, Envelope) * FMath::Lerp(0.82f, 1.0f, Seed.RadialBand);

			Pos = FVector(
				FMath::Cos(Angle) * DynamicRadius,
				FMath::Sin(Angle) * DynamicRadius,
				FMath::Lerp(-HalfHeight, HalfHeight, Height01));

			const FVector Tangent(-FMath::Sin(Angle) * DynamicRadius, FMath::Cos(Angle) * DynamicRadius, SwarmHeightSpan * 0.22f);
			Rot = Tangent.Rotation();
			Rot.Yaw += MeshYawOffsetDegrees;
			Rot.Roll += 18.0f * FMath::Sin(Angle * 2.0f);
			ScaleFactor *= FMath::Lerp(0.18f, 1.0f, Envelope);
			break;
		}
		case 2: // PetalCascade — wind-swayed falling blossom shower looping top-to-bottom
		{
			const float FallRate = FMath::Max(0.035f, FMath::Abs(OrbitSpeedDegrees) * 0.0038f) * Seed.SpeedMultiplier;
			const float Progress01 = FMath::Fmod(Seed.HeightOffset01 + TimeSeconds * FallRate, 1.0f);
			const float Height01 = 1.0f - Progress01;
			const float EdgeFade = FMath::Sin(Progress01 * PI);
			const float DriftAngle = Seed.Phase01 * 2.0f * PI + TimeSeconds * AngularVelRad * 0.55f + FMath::Sin(TimeSeconds * 1.3f + Seed.Phase01 * 6.0f) * 0.35f;
			const float RadialPos = SwarmRadius * Seed.RadialBand;
			const float BreezeX = 36.0f * FMath::Sin(TimeSeconds * 1.8f + Seed.HeightOffset01 * 9.0f);

			Pos = FVector(
				FMath::Cos(DriftAngle) * RadialPos + BreezeX,
				FMath::Sin(DriftAngle) * RadialPos,
				FMath::Lerp(-HalfHeight, HalfHeight, Height01));

			Rot = FRotator(
				35.0f * FMath::Sin(TimeSeconds * 2.4f + Seed.Phase01 * 12.0f),
				FMath::RadiansToDegrees(DriftAngle) + TimeSeconds * 48.0f * Seed.LateralOffset,
				42.0f * FMath::Cos(TimeSeconds * 2.1f + Seed.HeightOffset01 * 10.0f));
			ScaleFactor *= FMath::Lerp(0.20f, 1.0f, FMath::Sqrt(FMath::Max(0.0f, EdgeFade)));
			break;
		}
		case 3: // FigureEightSchool — 3D infinity-ribbon spirit koi / celestial butterfly school
		{
			const float SchoolParam = TimeSeconds * AngularVelRad * 0.85f * Seed.SpeedMultiplier + Seed.Phase01 * 2.0f * PI;
			const float SpreadR = SwarmRadius * 0.16f * Seed.LateralOffset;
			const float SpreadZ = HalfHeight * 0.35f * (Seed.HeightOffset01 - 0.5f);

			const float SinU = FMath::Sin(SchoolParam);
			const float CosU = FMath::Cos(SchoolParam);
			const float Sin2U = FMath::Sin(2.0f * SchoolParam);
			const float Cos2U = FMath::Cos(2.0f * SchoolParam);

			// Lemniscate 3D ribbon position + analytical tangent derivative
			Pos = FVector(
				SwarmRadius * CosU + SpreadR * Cos2U,
				SwarmRadius * 0.56f * Sin2U + SpreadR * SinU,
				HalfHeight * 0.55f * SinU + SpreadZ);

			const float DirSign = (OrbitSpeedDegrees >= 0.0f) ? 1.0f : -1.0f;
			const FVector VelocityTangent(
				-SwarmRadius * SinU * DirSign,
				SwarmRadius * 1.12f * Cos2U * DirSign,
				HalfHeight * 0.55f * CosU * DirSign);

			Rot = VelocityTangent.GetSafeNormal(UE_SMALL_NUMBER, FVector::ForwardVector).Rotation();
			const float SwimTailSway = 7.5f * FMath::Sin(TimeSeconds * 6.4f + Seed.Phase01 * 18.0f);
			Rot.Yaw += MeshYawOffsetDegrees + SwimTailSway;
			Rot.Roll += -16.0f * Sin2U;
			break;
		}
		default: // 0: OrbitalVortex — multi-band celestial vortex
		{
			const float Angle = Seed.Phase01 * 2.0f * PI + TimeSeconds * AngularVelRad * Seed.SpeedMultiplier;
			const float Radius = SwarmRadius * Seed.RadialBand;
			const float VerticalWave = FMath::Lerp(-HalfHeight, HalfHeight, Seed.HeightOffset01) * 0.72f +
				HalfHeight * 0.28f * FMath::Sin(Angle * 2.0f + Seed.Phase01 * PI);

			Pos = FVector(
				FMath::Cos(Angle) * Radius,
				FMath::Sin(Angle) * Radius,
				VerticalWave);

			const float DirSign = (OrbitSpeedDegrees >= 0.0f) ? 1.0f : -1.0f;
			const FVector Tangent(-FMath::Sin(Angle) * DirSign, FMath::Cos(Angle) * DirSign, 0.12f * FMath::Cos(Angle * 2.0f));
			Rot = Tangent.Rotation();
			Rot.Yaw += MeshYawOffsetDegrees;
			Rot.Roll += 18.0f * DirSign;
			ScaleFactor *= (0.90f + 0.14f * FMath::Sin(TimeSeconds * 4.2f + Seed.Phase01 * 10.0f));
			break;
		}
		}

		CachedTransforms[Idx] = FTransform(Rot, Pos, FVector(FMath::Max(0.002f, ScaleFactor)));
	}
}
