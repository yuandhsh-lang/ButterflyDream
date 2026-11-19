#include "ButterflyDreamGateActor.h"

#include "ButterflyPawn.h"
#include "ButterflyPlayerController.h"
#include "ButterflySceneSubsystem.h"
#include "CollisionQueryParams.h"
#include "CollisionShape.h"
#include "Components/BoxComponent.h"
#include "Components/PointLightComponent.h"
#include "Components/SceneComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"
#include "GenericPlatform/GenericPlatformApplicationMisc.h"
#include "HAL/PlatformApplicationMisc.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/PackageName.h"
#include "NiagaraComponent.h"
#include "NiagaraSystem.h"
#include "UObject/ConstructorHelpers.h"

AButterflyDreamGateActor::AButterflyDreamGateActor()
{
	PrimaryActorTick.bCanEverTick = true;

	SceneRoot = CreateDefaultSubobject<USceneComponent>(TEXT("SceneRoot"));
	RootComponent = SceneRoot;

	GateFrameMesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("GateFrameMesh"));
	GateFrameMesh->SetupAttachment(SceneRoot);
	GateFrameMesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);

	LeftDoorPivot = CreateDefaultSubobject<USceneComponent>(TEXT("LeftDoorPivot"));
	LeftDoorPivot->SetupAttachment(SceneRoot);
	LeftDoorMesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("LeftDoorMesh"));
	LeftDoorMesh->SetupAttachment(LeftDoorPivot);
	LeftDoorMesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);

	RightDoorPivot = CreateDefaultSubobject<USceneComponent>(TEXT("RightDoorPivot"));
	RightDoorPivot->SetupAttachment(SceneRoot);
	RightDoorMesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("RightDoorMesh"));
	RightDoorMesh->SetupAttachment(RightDoorPivot);
	RightDoorMesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);

	LeftDoorCollision = CreateDefaultSubobject<UBoxComponent>(TEXT("LeftDoorCollision"));
	LeftDoorCollision->SetupAttachment(LeftDoorPivot);
	ConfigureProxy(LeftDoorCollision);
	RightDoorCollision = CreateDefaultSubobject<UBoxComponent>(TEXT("RightDoorCollision"));
	RightDoorCollision->SetupAttachment(RightDoorPivot);
	ConfigureProxy(RightDoorCollision);

	LeftFrameCollision = CreateDefaultSubobject<UBoxComponent>(TEXT("LeftFrameCollision"));
	LeftFrameCollision->SetupAttachment(SceneRoot);
	ConfigureProxy(LeftFrameCollision);
	RightFrameCollision = CreateDefaultSubobject<UBoxComponent>(TEXT("RightFrameCollision"));
	RightFrameCollision->SetupAttachment(SceneRoot);
	ConfigureProxy(RightFrameCollision);
	TopFrameCollision = CreateDefaultSubobject<UBoxComponent>(TEXT("TopFrameCollision"));
	TopFrameCollision->SetupAttachment(SceneRoot);
	ConfigureProxy(TopFrameCollision);
	BottomFrameCollision = CreateDefaultSubobject<UBoxComponent>(TEXT("BottomFrameCollision"));
	BottomFrameCollision->SetupAttachment(SceneRoot);
	ConfigureProxy(BottomFrameCollision);

	static ConstructorHelpers::FObjectFinder<UStaticMesh> FrameAsset(
		TEXT("/Game/LuxGenerated/Gate_G01/Gate_Frame"));
	if (FrameAsset.Succeeded())
	{
		GateFrameMesh->SetStaticMesh(FrameAsset.Object);
	}
	static ConstructorHelpers::FObjectFinder<UStaticMesh> LeftLeafAsset(
		TEXT("/Game/LuxGenerated/Gate_G01/Gate_Leaf_L"));
	if (LeftLeafAsset.Succeeded())
	{
		LeftDoorMesh->SetStaticMesh(LeftLeafAsset.Object);
	}
	static ConstructorHelpers::FObjectFinder<UStaticMesh> RightLeafAsset(
		TEXT("/Game/LuxGenerated/Gate_G01/Gate_Leaf_R"));
	if (RightLeafAsset.Succeeded())
	{
		RightDoorMesh->SetStaticMesh(RightLeafAsset.Object);
	}

	static ConstructorHelpers::FObjectFinder<UStaticMesh> TunnelRingAsset(
		TEXT("/Game/Optimized/Tunnel_Ring_FX"));
	for (int32 Index = 0; Index < NumTunnelRings; ++Index)
	{
		const FName RingName(*FString::Printf(TEXT("TunnelRing_%d"), Index));
		UStaticMeshComponent* RingComp = CreateDefaultSubobject<UStaticMeshComponent>(RingName);
		RingComp->SetupAttachment(SceneRoot);
		RingComp->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		RingComp->SetCastShadow(false);
		RingComp->SetRelativeLocation(FVector(0.0f, FDreamGateResonance::GetTunnelRingSpacing(true) * (Index + 1), 25.0f));
		RingComp->SetRelativeScale3D(FVector(2.4f));
		if (TunnelRingAsset.Succeeded())
		{
			RingComp->SetStaticMesh(TunnelRingAsset.Object);
		}
		TunnelRingMeshes.Add(RingComp);
		for (int32 Segment = 0; Segment < 8; ++Segment)
		{
			const float Angle = static_cast<float>(Segment) * PI * 0.25f;
			UBoxComponent* Proxy = CreateDefaultSubobject<UBoxComponent>(
				*FString::Printf(TEXT("TunnelCollision_%d_%d"), Index, Segment));
			Proxy->SetupAttachment(RingComp);
			ConfigureProxy(Proxy);
			Proxy->SetRelativeLocation(FVector(6.408f * FMath::Cos(Angle), 0.0f, 6.408f * FMath::Sin(Angle)));
			Proxy->SetRelativeRotation(FRotator(-FMath::RadiansToDegrees(Angle + PI * 0.5f), 0.0f, 0.0f));
			Proxy->SetBoxExtent(FVector(3.15f, 2.0f, 2.592f));
			TunnelRingCollisionBoxes.Add(Proxy);
		}
	}

	GateCoreLight = CreateDefaultSubobject<UPointLightComponent>(TEXT("GateCoreLight"));
	GateCoreLight->SetupAttachment(SceneRoot);
	GateCoreLight->SetRelativeLocation(FVector(0.0f, 0.0f, 130.0f));
	GateCoreLight->SetIntensityUnits(ELightUnits::Candelas);
	GateCoreLight->SetIntensity(95.0f);
	GateCoreLight->SetAttenuationRadius(1500.0f);
	GateCoreLight->SetLightColor(FLinearColor(1.0f, 0.74f, 0.88f));
	GateCoreLight->SetCastShadows(false);

	TunnelGuideLight = CreateDefaultSubobject<UPointLightComponent>(TEXT("TunnelGuideLight"));
	TunnelGuideLight->SetupAttachment(SceneRoot);
	TunnelGuideLight->SetRelativeLocation(FVector(0.0f, 200.0f, 130.0f));
	TunnelGuideLight->SetIntensityUnits(ELightUnits::Candelas);
	TunnelGuideLight->SetIntensity(120.0f);
	TunnelGuideLight->SetAttenuationRadius(1600.0f);
	TunnelGuideLight->SetLightColor(FLinearColor(0.48f, 0.84f, 1.0f));
	TunnelGuideLight->SetCastShadows(false);

	GateReformNiagara = CreateDefaultSubobject<UNiagaraComponent>(TEXT("GateReformNiagara"));
	GateReformNiagara->SetupAttachment(SceneRoot);
	GateReformNiagara->SetAutoActivate(false);
	static ConstructorHelpers::FObjectFinder<UNiagaraSystem> GateReformSystem(
		TEXT("/Game/FX/NS_Gate_MeshSwarm"));
	if (GateReformSystem.Succeeded())
	{
		GateReformNiagara->SetAsset(GateReformSystem.Object);
	}

	TunnelRibbonNiagara = CreateDefaultSubobject<UNiagaraComponent>(TEXT("TunnelRibbonNiagara"));
	TunnelRibbonNiagara->SetupAttachment(SceneRoot);
	TunnelRibbonNiagara->SetAutoActivate(true);
	static ConstructorHelpers::FObjectFinder<UNiagaraSystem> TunnelRibbonSystem(
		TEXT("/Game/FX/NS_Butterfly_WingRibbon"));
	if (TunnelRibbonSystem.Succeeded())
	{
		TunnelRibbonNiagara->SetAsset(TunnelRibbonSystem.Object);
	}

	RefreshComponentTransforms();
	UpdateCollisionState();
}

void AButterflyDreamGateActor::ConfigureProxy(UBoxComponent* Proxy) const
{
	Proxy->InitBoxExtent(FVector(1.0f));
	Proxy->SetCollisionObjectType(ECC_WorldDynamic);
	Proxy->SetCollisionResponseToAllChannels(ECR_Ignore);
	Proxy->SetCollisionResponseToChannel(ECC_Pawn, ECR_Block);
	Proxy->SetCollisionResponseToChannel(ECC_Camera, ECR_Block);
	Proxy->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
	Proxy->SetGenerateOverlapEvents(false);
	Proxy->CanCharacterStepUpOn = ECB_No;
}

void AButterflyDreamGateActor::OnConstruction(const FTransform& Transform)
{
	Super::OnConstruction(Transform);
	bTargetMapValid = FPackageName::DoesPackageExist(TargetMapPackageName);
	RefreshComponentTransforms();
	UpdateCollisionState();
}

void AButterflyDreamGateActor::BeginPlay()
{
	Super::BeginPlay();
	Resonance.Reset();
	Resonance.ChargeSeconds = ChargeSeconds;
	Resonance.OpeningSeconds = OpeningSeconds;
	bTargetMapValid = FPackageName::DoesPackageExist(TargetMapPackageName);
	AnimTime = 0.0f;
	InnerRingAngleDeg = 0.0f;
	bPlayerNear = false;
	RefreshComponentTransforms();
	UpdateCollisionState();
}

void AButterflyDreamGateActor::ConfigureHingeOffsets(
	FVector InLeftHinge,
	FVector InRightHinge,
	FVector InInnerRing,
	FVector InPortalCenter)
{
	LeftHingeLocalOffset = InLeftHinge;
	RightHingeLocalOffset = InRightHinge;
	InnerRingLocalOffset = InInnerRing;
	PortalCenterLocalOffset = InPortalCenter;
	RefreshComponentTransforms();
}

void AButterflyDreamGateActor::ApplyGatePreset(bool bRotaryStarGate)
{
	bUseRotaryInnerRingMode = bRotaryStarGate;
	if (bRotaryStarGate)
	{
		GateTitle = TEXT("太极梦境 ｜ 浑天星轨法阵");
		PortalApertureHalfWidth = 17.0f;
		PortalApertureHalfHeight = 17.0f;
		PortalCenterLocalOffset = FVector(0.0f, 0.0f, 25.0f);
		InnerRingLocalOffset = FVector(0.0f, 0.0f, 24.9f);
		if (UStaticMesh* OuterMesh = LoadObject<UStaticMesh>(nullptr, TEXT("/Game/LuxGenerated/Gate_G03/StarGate_OuterRing")))
		{
			GateFrameMesh->SetStaticMesh(OuterMesh);
		}
		if (UStaticMesh* InnerMesh = LoadObject<UStaticMesh>(nullptr, TEXT("/Game/LuxGenerated/Gate_G03/StarGate_InnerRing")))
		{
			LeftDoorMesh->SetStaticMesh(InnerMesh);
		}
		RightDoorMesh->SetVisibility(false);
		GateCoreLight->SetLightColor(FLinearColor(0.55f, 0.88f, 1.0f));
	}
	else
	{
		GateTitle = TEXT("星海梦境 ｜ 共鸣仙门");
		PortalApertureHalfWidth = 90.0f;
		PortalApertureHalfHeight = 105.0f;
		PortalCenterLocalOffset = FVector(0.0f, 12.0f, 130.0f);
		if (UStaticMesh* FrameMesh = LoadObject<UStaticMesh>(nullptr, TEXT("/Game/LuxGenerated/Gate_G01/Gate_Frame")))
		{
			GateFrameMesh->SetStaticMesh(FrameMesh);
		}
		if (UStaticMesh* LeftMesh = LoadObject<UStaticMesh>(nullptr, TEXT("/Game/LuxGenerated/Gate_G01/Gate_Leaf_L")))
		{
			LeftDoorMesh->SetStaticMesh(LeftMesh);
		}
		if (UStaticMesh* RightMesh = LoadObject<UStaticMesh>(nullptr, TEXT("/Game/LuxGenerated/Gate_G01/Gate_Leaf_R")))
		{
			RightDoorMesh->SetStaticMesh(RightMesh);
			RightDoorMesh->SetVisibility(true);
		}
		GateCoreLight->SetLightColor(FLinearColor(1.0f, 0.74f, 0.88f));
	}
	RefreshComponentTransforms();
	UpdateCollisionState();
}

float AButterflyDreamGateActor::GetTunnelRingSpacing() const
{
	return TunnelRingSpacingOverride > 0.0f
		? TunnelRingSpacingOverride
		: FDreamGateResonance::GetTunnelRingSpacing(bUseRotaryInnerRingMode);
}

float AButterflyDreamGateActor::GetTunnelExitDistance() const
{
	return GetTunnelRingSpacing() * static_cast<float>(NumTunnelRings);
}

FVector AButterflyDreamGateActor::GetTunnelExitWorldLocation() const
{
	return GetActorTransform().TransformPosition(
		PortalCenterLocalOffset + FVector(0.0f, GetTunnelExitDistance(), 0.0f));
}

FString AButterflyDreamGateActor::GetGateStateName() const
{
	switch (Resonance.State)
	{
	case EDreamGateState::Idle: return TEXT("Idle");
	case EDreamGateState::Resonating: return TEXT("Resonating");
	case EDreamGateState::Opening: return TEXT("Opening");
	case EDreamGateState::Ready: return TEXT("Ready");
	case EDreamGateState::Traversing: return TEXT("Traversing");
	case EDreamGateState::Loading: return TEXT("Loading");
	case EDreamGateState::Error: return TEXT("Error");
	default: return TEXT("Error");
	}
}

void AButterflyDreamGateActor::RefreshComponentTransforms()
{
	const float HalfWidth = FMath::Max(1.0f, PortalApertureHalfWidth);
	const float HalfHeight = FMath::Max(1.0f, PortalApertureHalfHeight);
	if (bUseRotaryInnerRingMode)
	{
		LeftDoorPivot->SetRelativeLocation(InnerRingLocalOffset);
		RightDoorPivot->SetRelativeLocation(InnerRingLocalOffset);
		LeftDoorMesh->SetRelativeLocation(FVector::ZeroVector);
		RightDoorMesh->SetRelativeLocation(FVector::ZeroVector);
		LeftDoorCollision->SetRelativeLocation(FVector(-HalfWidth * 0.5f, 0.0f, 0.0f));
		RightDoorCollision->SetRelativeLocation(FVector(HalfWidth * 0.5f, 0.0f, 0.0f));
	}
	else
	{
		LeftDoorPivot->SetRelativeLocation(LeftHingeLocalOffset);
		LeftDoorMesh->SetRelativeLocation(FVector::ZeroVector);
		RightDoorPivot->SetRelativeLocation(RightHingeLocalOffset);
		RightDoorMesh->SetRelativeLocation(FVector::ZeroVector);
		LeftDoorCollision->SetRelativeLocation(FVector(
			HalfWidth * 0.5f,
			PortalCenterLocalOffset.Y - LeftHingeLocalOffset.Y,
			PortalCenterLocalOffset.Z - LeftHingeLocalOffset.Z));
		RightDoorCollision->SetRelativeLocation(FVector(
			-HalfWidth * 0.5f,
			PortalCenterLocalOffset.Y - RightHingeLocalOffset.Y,
			PortalCenterLocalOffset.Z - RightHingeLocalOffset.Z));
	}
	LeftDoorCollision->SetBoxExtent(FVector(HalfWidth * 0.5f, 8.0f, HalfHeight));
	RightDoorCollision->SetBoxExtent(FVector(HalfWidth * 0.5f, 8.0f, HalfHeight));

	const float FrameThickness = 12.0f;
	const FVector Center = PortalCenterLocalOffset;
	LeftFrameCollision->SetRelativeLocation(Center + FVector(-HalfWidth - FrameThickness * 0.5f, 0.0f, 0.0f));
	RightFrameCollision->SetRelativeLocation(Center + FVector(HalfWidth + FrameThickness * 0.5f, 0.0f, 0.0f));
	TopFrameCollision->SetRelativeLocation(Center + FVector(0.0f, 0.0f, HalfHeight + FrameThickness * 0.5f));
	BottomFrameCollision->SetRelativeLocation(Center + FVector(0.0f, 0.0f, -HalfHeight - FrameThickness * 0.5f));
	LeftFrameCollision->SetBoxExtent(FVector(FrameThickness * 0.5f, 12.0f, HalfHeight + FrameThickness));
	RightFrameCollision->SetBoxExtent(FVector(FrameThickness * 0.5f, 12.0f, HalfHeight + FrameThickness));
	TopFrameCollision->SetBoxExtent(FVector(HalfWidth + FrameThickness, 12.0f, FrameThickness * 0.5f));
	BottomFrameCollision->SetBoxExtent(FVector(HalfWidth + FrameThickness, 12.0f, FrameThickness * 0.5f));

	const float Spacing = GetTunnelRingSpacing();
	for (int32 Index = 0; Index < TunnelRingMeshes.Num(); ++Index)
	{
		if (UStaticMeshComponent* RingComp = TunnelRingMeshes[Index])
		{
			const float BaseRingScale = bUseRotaryInnerRingMode
				? 2.4f
				: FMath::Max(1.8f, 7.6f - Index * 0.42f);
			RingComp->SetRelativeLocation(Center + FVector(0.0f, Spacing * (Index + 1), 0.0f));
			RingComp->SetRelativeScale3D(FVector(BaseRingScale));
		}
	}
	GateCoreLight->SetRelativeLocation(Center);
	TunnelGuideLight->SetRelativeLocation(Center + FVector(0.0f, Spacing * 6.0f, 0.0f));
	if (GateReformNiagara)
	{
		GateReformNiagara->SetRelativeLocation(Center);
	}
	if (TunnelRibbonNiagara)
	{
		TunnelRibbonNiagara->SetRelativeLocation(Center + FVector(0.0f, Spacing * 3.0f, 0.0f));
	}
}

void AButterflyDreamGateActor::UpdateCollisionState()
{
	const ECollisionEnabled::Type DoorCollision = Resonance.OpenAlpha >= FDreamGateResonance::SafeOpenAlpha
		? ECollisionEnabled::NoCollision
		: ECollisionEnabled::QueryOnly;
	LeftDoorCollision->SetCollisionEnabled(DoorCollision);
	RightDoorCollision->SetCollisionEnabled(DoorCollision);
}

bool AButterflyDreamGateActor::IsCenterSweepClear(const APawn* PlayerPawn) const
{
	if (Resonance.OpenAlpha < FDreamGateResonance::SafeOpenAlpha)
	{
		return false;
	}
	const UWorld* World = GetWorld();
	if (!World)
	{
		return false;
	}
	const FVector Center = GetActorTransform().TransformPosition(PortalCenterLocalOffset);
	const FVector Forward = GetActorRightVector();
	const float Radius = FMath::Max(0.0f, TraversalCapsuleRadius);
	const float HalfHeight = FMath::Max(Radius, TraversalCapsuleHalfHeight);
	FCollisionQueryParams QueryParams(SCENE_QUERY_STAT(DreamGateCenterSweep), false);
	if (PlayerPawn)
	{
		QueryParams.AddIgnoredActor(PlayerPawn);
	}
	FHitResult Hit;
	return !World->SweepSingleByChannel(
		Hit,
		Center - Forward * 45.0f,
		Center + Forward * 45.0f,
		GetActorQuat(),
		ECC_Pawn,
		FCollisionShape::MakeCapsule(Radius, HalfHeight),
		QueryParams);
}

void AButterflyDreamGateActor::ResetGateState()
{
	Resonance.Reset();
	Resonance.ChargeSeconds = ChargeSeconds;
	Resonance.OpeningSeconds = OpeningSeconds;
	bPlayerNear = false;
	RefreshComponentTransforms();
	UpdateCollisionState();
}

void AButterflyDreamGateActor::HandleSceneSwitchFailure(const FString& Failure)
{
	Resonance.NotifyLoadFailed(Failure);
}

void AButterflyDreamGateActor::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	if (!FMath::IsFinite(DeltaSeconds) || DeltaSeconds < 0.0f)
	{
		Resonance.Fail(TEXT("Invalid gate tick delta."));
		return;
	}

	APawn* PlayerPawn = UGameplayStatics::GetPlayerPawn(this, 0);
	AButterflyPlayerController* ButterflyController = PlayerPawn
		? Cast<AButterflyPlayerController>(PlayerPawn->GetController())
		: nullptr;
	const UGameInstance* GameInstance = GetGameInstance();
	const UButterflySceneSubsystem* SceneSubsystem = GameInstance
		? GameInstance->GetSubsystem<UButterflySceneSubsystem>()
		: nullptr;
	const bool bSuspended = !PlayerPawn ||
		(ButterflyController && ButterflyController->IsSceneMenuOpen()) ||
		(SceneSubsystem && SceneSubsystem->IsSceneSwitchInProgress());
	if (bSuspended)
	{
		Resonance.ForgetPosition();
		return;
	}

	const float Delta = FMath::Min(DeltaSeconds, 0.1f);
	AnimTime += Delta;
	Resonance.ChargeSeconds = ChargeSeconds;
	Resonance.OpeningSeconds = OpeningSeconds;

	const FVector PortalCenter = GetActorTransform().TransformPosition(PortalCenterLocalOffset);
	const float DistanceToPlayer = FVector::Dist(PlayerPawn->GetActorLocation(), PortalCenter);
	const FVector LocalPosition = GetActorTransform().InverseTransformPosition(PlayerPawn->GetActorLocation()) - PortalCenterLocalOffset;
	bPlayerNear = FMath::IsFinite(DistanceToPlayer) && DistanceToPlayer <= ResonanceDistance;
	const AButterflyPawn* ButterflyPawn = Cast<AButterflyPawn>(PlayerPawn);
	const AController* PawnController = PlayerPawn->GetController();
	const bool bBoosting = ButterflyPawn && ButterflyPawn->IsAccelerating() &&
		(!PawnController || !PawnController->IsMoveInputIgnored());
	const bool bTraversing = Resonance.State == EDreamGateState::Traversing;
	const bool bBeyondResetDistance = bTraversing
		? (FMath::Abs(LocalPosition.X) > PortalApertureHalfWidth * 3.0f ||
			FMath::Abs(LocalPosition.Z) > PortalApertureHalfHeight * 3.0f ||
			LocalPosition.Y < -ResonanceDistance || LocalPosition.Y > GetTunnelExitDistance() + ResonanceDistance)
		: DistanceToPlayer > ResonanceDistance * 1.3f;
	const bool bCenterClear = IsCenterSweepClear(PlayerPawn);

	Resonance.Update(
		DeltaSeconds,
		bPlayerNear,
		bBeyondResetDistance,
		bBoosting,
		bCenterClear,
		bTargetMapValid,
		false,
		LocalPosition,
		PortalApertureHalfWidth,
		PortalApertureHalfHeight,
		TraversalCapsuleRadius,
		TraversalCapsuleHalfHeight,
		GetTunnelExitDistance());

	if (bUseRotaryInnerRingMode)
	{
		const float SpinRate = FMath::Lerp(22.0f, 102.0f, Resonance.OpenAlpha);
		InnerRingAngleDeg = FMath::Fmod(InnerRingAngleDeg + SpinRate * Delta, 360.0f);
		LeftDoorPivot->SetRelativeRotation(FQuat(FVector::RightVector, FMath::DegreesToRadians(InnerRingAngleDeg)));
		RightDoorPivot->SetRelativeRotation(LeftDoorPivot->GetRelativeRotation());
	}
	else
	{
		const float DoorAngle = Resonance.OpenAlpha * MaxDoorOpenDegrees;
		LeftDoorPivot->SetRelativeRotation(FRotator(0.0f, DoorAngle, 0.0f));
		RightDoorPivot->SetRelativeRotation(FRotator(0.0f, -DoorAngle, 0.0f));
	}
	UpdateCollisionState();

	if (GateReformNiagara)
	{
		if (UStaticMesh* CurrentGateMesh = GateFrameMesh->GetStaticMesh())
		{
			GateReformNiagara->SetVariableStaticMesh(TEXT("User.TargetMesh"), CurrentGateMesh);
		}
		GateReformNiagara->SetVariableFloat(TEXT("User.OpenAlpha"), Resonance.OpenAlpha);
		GateReformNiagara->SetVariableFloat(TEXT("User.Resonance"), Resonance.Charge);
		GateReformNiagara->SetVariableFloat(TEXT("User.DisperseRadius"), 120.0f);
		if ((bPlayerNear || Resonance.Charge > 0.0f) && !GateReformNiagara->IsActive())
		{
			GateReformNiagara->Activate(true);
		}
		else if (!bPlayerNear && Resonance.Charge <= 0.0f && GateReformNiagara->IsActive())
		{
			GateReformNiagara->Deactivate();
		}
	}
	if (TunnelRibbonNiagara)
	{
		TunnelRibbonNiagara->SetVariableFloat(TEXT("User.Boost"), Resonance.OpenAlpha);
		TunnelRibbonNiagara->SetVariableFloat(TEXT("User.WingBeat"), 2.0f + Resonance.Charge * 6.0f);
		TunnelRibbonNiagara->SetVariableFloat(TEXT("User.Width"), 4.0f);
		TunnelRibbonNiagara->SetVariableVec3(TEXT("User.Color"), FVector(0.42f, 0.76f, 1.0f));
	}

	if (Resonance.ConsumeExitEvent())
	{
		FString Status = TEXT("Scene switching is unavailable.");
		UButterflySceneSubsystem* MutableSceneSubsystem = GameInstance
			? GameInstance->GetSubsystem<UButterflySceneSubsystem>()
			: nullptr;
		const bool bAccepted = MutableSceneSubsystem && MutableSceneSubsystem->RequestSceneSwitch(TargetMapPackageName, Status);
		if (bAccepted)
		{
			Resonance.BeginLoading();
		}
		else
		{
			Resonance.Fail(Status);
		}
	}

	const float Spacing = GetTunnelRingSpacing();
	const float SpinBoost = FMath::Lerp(1.0f, 1.85f, Resonance.OpenAlpha);
	for (int32 Index = 0; Index < TunnelRingMeshes.Num(); ++Index)
	{
		if (UStaticMeshComponent* RingComp = TunnelRingMeshes[Index])
		{
			const float Direction = (Index % 2 == 0) ? 1.0f : -1.0f;
			const float RollAngle = AnimTime * (16.0f + Index * 4.2f) * SpinBoost * Direction;
			const float BaseRingScale = bUseRotaryInnerRingMode
				? 2.4f
				: FMath::Max(1.8f, 7.6f - Index * 0.42f);
			const float PulseScale = BaseRingScale *
				(1.0f + (0.035f + 0.03f * Resonance.OpenAlpha) * FMath::Sin(AnimTime * 2.5f + Index * 0.65f));
			RingComp->SetRelativeLocation(PortalCenterLocalOffset + FVector(0.0f, Spacing * (Index + 1), 0.0f));
			RingComp->SetRelativeRotation(FQuat(FVector::RightVector, FMath::DegreesToRadians(RollAngle)));
			RingComp->SetRelativeScale3D(FVector(PulseScale));
		}
	}

	const float Pulse = 0.88f + 0.12f * FMath::Sin(AnimTime * 3.5f);
	GateCoreLight->SetRelativeLocation(PortalCenterLocalOffset);
	GateCoreLight->SetIntensity(FMath::Lerp(25.0f, 85.0f, Resonance.OpenAlpha) * Pulse);
	const float GuidePulse = 0.90f + 0.10f * FMath::Cos(AnimTime * 2.8f);
	TunnelGuideLight->SetRelativeLocation(PortalCenterLocalOffset + FVector(0.0f, Spacing * 6.0f, 0.0f));
	TunnelGuideLight->SetIntensity(FMath::Lerp(30.0f, 95.0f, Resonance.OpenAlpha) * GuidePulse);
}
