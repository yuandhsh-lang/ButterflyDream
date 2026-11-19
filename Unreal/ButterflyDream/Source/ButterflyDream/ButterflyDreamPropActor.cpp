#include "ButterflyDreamPropActor.h"

#include "Components/PointLightComponent.h"
#include "Components/SceneComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"

AButterflyDreamPropActor::AButterflyDreamPropActor()
{
	PrimaryActorTick.bCanEverTick = true;

	SceneRoot = CreateDefaultSubobject<USceneComponent>(TEXT("SceneRoot"));
	RootComponent = SceneRoot;

	PropMesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("PropMesh"));
	PropMesh->SetupAttachment(SceneRoot);
	PropMesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);

	GlowLight = CreateDefaultSubobject<UPointLightComponent>(TEXT("GlowLight"));
	GlowLight->SetupAttachment(SceneRoot);
	GlowLight->SetCastShadows(false);
	GlowLight->SetIntensityUnits(ELightUnits::Candelas);
	GlowLight->SetIntensity(0.0f);
	GlowLight->SetVisibility(false);
}

void AButterflyDreamPropActor::BeginPlay()
{
	Super::BeginPlay();
	BaseLocation = GetActorLocation();
	bHasBaseLocation = true;
	if (PropMesh)
	{
		BaseMeshScale = PropMesh->GetRelativeScale3D();
	}
	if (GlowLight)
	{
		BaseLightIntensity = GlowLight->Intensity;
	}
}

void AButterflyDreamPropActor::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	ElapsedTime += DeltaSeconds;

	if (!bHasBaseLocation)
	{
		BaseLocation = GetActorLocation();
		bHasBaseLocation = true;
	}

	const float ZOffset = FMath::Sin(ElapsedTime * BobSpeed + PhaseOffset) * BobAmplitude;
	SetActorLocation(BaseLocation + FVector(0.0f, 0.0f, ZOffset));

	if (!FMath::IsNearlyZero(SpinSpeedYaw))
	{
		AddActorLocalRotation(FRotator(0.0f, SpinSpeedYaw * DeltaSeconds, 0.0f));
	}

	if (PropMesh)
	{
		if (!FMath::IsNearlyZero(SwayAmplitudeDegrees))
		{
			const float SwayPitch = FMath::Sin(ElapsedTime * SwaySpeed + PhaseOffset) * SwayAmplitudeDegrees;
			const float SwayRoll = FMath::Cos(ElapsedTime * (SwaySpeed * 0.82f) + PhaseOffset * 1.35f) * (SwayAmplitudeDegrees * 0.78f);
			PropMesh->SetRelativeRotation(FRotator(SwayPitch, 0.0f, SwayRoll));
		}

		if (!FMath::IsNearlyZero(BreatheScaleAmplitude))
		{
			const float BreatheFactor = 1.0f + BreatheScaleAmplitude * FMath::Sin(ElapsedTime * (BobSpeed * 1.2f) + PhaseOffset);
			PropMesh->SetRelativeScale3D(BaseMeshScale * BreatheFactor);
		}
	}

	if (GlowLight && GlowLight->IsVisible() && BaseLightIntensity > 0.0f)
	{
		const float WarmBreath = 1.0f + 0.12f * FMath::Sin(ElapsedTime * (BobSpeed * 1.5f) + PhaseOffset);
		GlowLight->SetIntensity(BaseLightIntensity * WarmBreath);
	}
}

void AButterflyDreamPropActor::ConfigureProp(
	UStaticMesh* MeshAsset,
	float Scale,
	bool bEnableLight,
	FLinearColor LightColor,
	float LightIntensity,
	float LightRadius)
{
	if (PropMesh && MeshAsset)
	{
		PropMesh->SetStaticMesh(MeshAsset);
		BaseMeshScale = FVector(Scale);
		PropMesh->SetRelativeScale3D(BaseMeshScale);
	}
	if (GlowLight)
	{
		BaseLightIntensity = bEnableLight ? LightIntensity : 0.0f;
		GlowLight->SetVisibility(bEnableLight);
		GlowLight->SetLightColor(LightColor);
		GlowLight->SetIntensityUnits(ELightUnits::Candelas);
		GlowLight->SetIntensity(BaseLightIntensity);
		GlowLight->SetAttenuationRadius(LightRadius);
	}
}
