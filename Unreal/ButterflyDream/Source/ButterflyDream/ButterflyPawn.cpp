#include "ButterflyPawn.h"

#include "ButterflyDreamGateActor.h"
#include "ButterflyPlayerController.h"
#include "ButterflyStorySubsystem.h"
#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/PointLightComponent.h"
#include "Components/SceneComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/LocalPlayer.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/WorldSettings.h"
#include "EnhancedInputComponent.h"
#include "EnhancedInputSubsystems.h"
#include "GameFramework/Controller.h"
#include "GameFramework/FloatingPawnMovement.h"
#include "GameFramework/GameModeBase.h"
#include "GameFramework/SpringArmComponent.h"
#include "GenericPlatform/GenericPlatformApplicationMisc.h"
#include "HAL/PlatformApplicationMisc.h"
#include "Misc/CoreDelegates.h"
#include "InputAction.h"
#include "InputActionValue.h"
#include "InputCoreTypes.h"
#include "InputKeyEventArgs.h"
#include "InputMappingContext.h"
#include "InputModifiers.h"
#include "Kismet/GameplayStatics.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialInterface.h"
#include "NiagaraComponent.h"
#include "NiagaraSystem.h"
#include "UObject/ConstructorHelpers.h"

namespace ButterflyMaterialParams
{
	static const FName EmissiveStrength(TEXT("EmissiveStrength"));
	static const FName EmissiveScale(TEXT("EmissiveScale"));
}

AButterflyPawn::AButterflyPawn()
{
	PrimaryActorTick.bCanEverTick = true;

	Capsule = CreateDefaultSubobject<UCapsuleComponent>(TEXT("Capsule"));
	Capsule->InitCapsuleSize(10.0f, 10.0f);
	Capsule->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
	Capsule->SetCollisionObjectType(ECC_Pawn);
	Capsule->SetCollisionResponseToAllChannels(ECR_Block);
	RootComponent = Capsule;

	// UE imports the antennae along -Y. Rotate the entire mesh set to face pawn +X.
	const FRotator ButterflyMeshRotation(0.0f, 90.0f, 0.0f);
	const FVector ButterflyScale(1.35f, 1.35f, 1.35f);

	BodyMesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("BodyMesh"));
	BodyMesh->SetupAttachment(Capsule);
	BodyMesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	BodyMesh->SetCastShadow(false);
	BodyMesh->SetRelativeRotation(ButterflyMeshRotation);
	BodyMesh->SetRelativeScale3D(ButterflyScale);

	LeftWingPivot = CreateDefaultSubobject<USceneComponent>(TEXT("LeftWingPivot"));
	LeftWingPivot->SetupAttachment(Capsule);
	LeftWingPivot->SetRelativeLocation(FVector(0.0f, -1.5f, 0.0f));
	LeftWingMesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("LeftWingMesh"));
	LeftWingMesh->SetupAttachment(LeftWingPivot);
	LeftWingMesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	LeftWingMesh->SetCastShadow(false);
	LeftWingMesh->SetRelativeRotation(ButterflyMeshRotation);
	LeftWingMesh->SetRelativeScale3D(ButterflyScale);

	RightWingPivot = CreateDefaultSubobject<USceneComponent>(TEXT("RightWingPivot"));
	RightWingPivot->SetupAttachment(Capsule);
	RightWingPivot->SetRelativeLocation(FVector(0.0f, 1.5f, 0.0f));
	RightWingMesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("RightWingMesh"));
	RightWingMesh->SetupAttachment(RightWingPivot);
	RightWingMesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	RightWingMesh->SetCastShadow(false);
	RightWingMesh->SetRelativeRotation(ButterflyMeshRotation);
	RightWingMesh->SetRelativeScale3D(ButterflyScale);

	static ConstructorHelpers::FObjectFinder<UStaticMesh> BodyAsset(
		TEXT("/Game/LuxGenerated/Butterfly_B01/Butterfly_Body"));
	if (BodyAsset.Succeeded())
	{
		BodyMesh->SetStaticMesh(BodyAsset.Object);
	}

	static ConstructorHelpers::FObjectFinder<UStaticMesh> LeftWingAsset(
		TEXT("/Game/LuxGenerated/Butterfly_B01/Wing_L"));
	if (LeftWingAsset.Succeeded())
	{
		LeftWingMesh->SetStaticMesh(LeftWingAsset.Object);
	}

	static ConstructorHelpers::FObjectFinder<UStaticMesh> RightWingAsset(
		TEXT("/Game/LuxGenerated/Butterfly_B01/Wing_R"));
	if (RightWingAsset.Succeeded())
	{
		RightWingMesh->SetStaticMesh(RightWingAsset.Object);
	}

	// Cool-cyan iridescent aura light (1.8 cd)
	ButterflyAuraLight = CreateDefaultSubobject<UPointLightComponent>(TEXT("ButterflyAuraLight"));
	ButterflyAuraLight->SetupAttachment(Capsule);
	ButterflyAuraLight->SetRelativeLocation(FVector(8.0f, -5.0f, 11.0f));
	ButterflyAuraLight->SetIntensityUnits(ELightUnits::Candelas);
	ButterflyAuraLight->SetIntensity(1.8f);
	ButterflyAuraLight->SetAttenuationRadius(290.0f);
	ButterflyAuraLight->SetLightColor(FLinearColor(0.70f, 0.90f, 1.0f));
	ButterflyAuraLight->SetCastShadows(false);

	// Complementary warm-gold rim light (1.2 cd) to make royal gold filigree wing veins gleam in 3D
	ButterflyGoldRimLight = CreateDefaultSubobject<UPointLightComponent>(TEXT("ButterflyGoldRimLight"));
	ButterflyGoldRimLight->SetupAttachment(Capsule);
	ButterflyGoldRimLight->SetRelativeLocation(FVector(-12.0f, 8.0f, 14.0f));
	ButterflyGoldRimLight->SetIntensityUnits(ELightUnits::Candelas);
	ButterflyGoldRimLight->SetIntensity(1.2f);
	ButterflyGoldRimLight->SetAttenuationRadius(250.0f);
	ButterflyGoldRimLight->SetLightColor(FLinearColor(1.0f, 0.78f, 0.42f));
	ButterflyGoldRimLight->SetCastShadows(false);

	UpdateMeshVisibility();

	CameraSpringArm = CreateDefaultSubobject<USpringArmComponent>(TEXT("CameraSpringArm"));
	CameraSpringArm->SetupAttachment(Capsule);
	CameraSpringArm->TargetArmLength = 210.0f;
	CameraSpringArm->SocketOffset = FVector(0.0f, 0.0f, 38.0f);
	CameraSpringArm->ProbeSize = 6.0f;
	CameraSpringArm->ProbeChannel = ECC_Camera;
	CameraSpringArm->bDoCollisionTest = true;
	CameraSpringArm->bUsePawnControlRotation = true;
	CameraSpringArm->bEnableCameraLag = true;
	CameraSpringArm->CameraLagSpeed = 9.0f;
	CameraSpringArm->CameraLagMaxDistance = 180.0f;
	CameraSpringArm->bEnableCameraRotationLag = true;
	CameraSpringArm->CameraRotationLagSpeed = 12.0f;

	FlightCamera = CreateDefaultSubobject<UCameraComponent>(TEXT("FlightCamera"));
	FlightCamera->SetupAttachment(CameraSpringArm, USpringArmComponent::SocketName);
	FlightCamera->bUsePawnControlRotation = false;
	FlightCamera->SetFieldOfView(CruiseCameraFOV);

	WakeRibbon = CreateDefaultSubobject<UNiagaraComponent>(TEXT("WakeRibbon"));
	WakeRibbon->SetupAttachment(Capsule);
	WakeRibbon->SetAutoActivate(true);
	static ConstructorHelpers::FObjectFinder<UNiagaraSystem> WakeSystem(
		TEXT("/Game/FX/NS_Butterfly_WingRibbon"));
	if (WakeSystem.Succeeded())
	{
		WakeRibbon->SetAsset(WakeSystem.Object);
	}

	FloatingMovement = CreateDefaultSubobject<UFloatingPawnMovement>(TEXT("FloatingMovement"));
	FloatingMovement->MaxSpeed = BaseSpeed;
	FloatingMovement->Acceleration = 1850.0f;
	FloatingMovement->Deceleration = 2050.0f;
	FloatingMovement->TurningBoost = 8.5f;
}

void AButterflyPawn::BeginPlay()
{
	Super::BeginPlay();

	CurrentCameraFOV = CruiseCameraFOV;
	if (FlightCamera)
	{
		FlightCamera->SetFieldOfView(CurrentCameraFOV);
	}

	UpdateMeshVisibility();
	RefreshButterflyMaterials();
	CacheSafePoint();
	FCoreDelegates::ApplicationWillDeactivateDelegate.AddUObject(this, &AButterflyPawn::HandleApplicationWillDeactivate);

	if (UWorld* World = GetWorld())
	{
		if (UButterflyStorySubsystem* StorySubsystem = World->GetSubsystem<UButterflyStorySubsystem>())
		{
			StorySubsystem->RegisterPawn(this);
		}
	}
}

void AButterflyPawn::CacheSafePoint()
{
	SafePointLocation = GetActorLocation();
	SafePointRotation = GetController() ? GetController()->GetControlRotation() : GetActorRotation();
	PreviousPosition = SafePointLocation;
	StuckTimer = 0.0f;
	bHasSafePoint = FDreamGateResonance::IsFiniteVector(SafePointLocation);
	if (!bHasSafePoint)
	{
		SafePointLocation = FVector::ZeroVector;
		SafePointRotation = FRotator::ZeroRotator;
	}
}

bool AButterflyPawn::NeedsRecovery() const
{
	const FVector Location = GetActorLocation();
	if (!FDreamGateResonance::IsFiniteVector(Location) ||
		(FloatingMovement && !FDreamGateResonance::IsFiniteVector(FloatingMovement->Velocity)))
	{
		return true;
	}
	constexpr float MaxCoordinate = 2000000.0f;
	if (FMath::Abs(Location.X) > MaxCoordinate || FMath::Abs(Location.Y) > MaxCoordinate ||
		FMath::Abs(Location.Z) > MaxCoordinate)
	{
		return true;
	}
	if (bHasSafePoint && FVector::Dist2D(Location, SafePointLocation) > SafeFlightRadius)
	{
		return true;
	}
	const UWorld* World = GetWorld();
	const AWorldSettings* WorldSettings = World ? World->GetWorldSettings() : nullptr;
	return WorldSettings && Location.Z < WorldSettings->KillZ + 500.0f;
}

void AButterflyPawn::RecoverToSafePoint()
{
	if (RecoveryCooldown > 0.0f)
	{
		return;
	}
	ClearFlightInput();
	SetShowcaseOrbitActive(false);
	FVector Destination = bHasSafePoint ? SafePointLocation : FVector::ZeroVector;
	const FRotator DestinationRotation = bHasSafePoint ? SafePointRotation : FRotator::ZeroRotator;
	if (UWorld* World = GetWorld())
	{
		if (!World->FindTeleportSpot(this, Destination, DestinationRotation))
		{
			UE_LOG(LogTemp, Warning, TEXT("LUX_RECOVERY No collision-free point near the safe transform"));
			RecoveryCooldown = 0.35f;
			return;
		}
	}
	SetActorLocationAndRotation(Destination, DestinationRotation, false, nullptr, ETeleportType::TeleportPhysics);
	PreviousPosition = Destination;
	StuckTimer = 0.0f;
	if (AController* PawnController = GetController())
	{
		PawnController->SetControlRotation(DestinationRotation);
	}
	FloatingMovement->StopMovementImmediately();
	if (CameraSpringArm)
	{
		CameraSpringArm->bEnableCameraLag = false;
		CameraSpringArm->bEnableCameraRotationLag = false;
		CameraSpringArm->TargetArmLength = 210.0f;
		CameraSpringArm->SocketOffset = FVector(0.0f, 0.0f, 38.0f);
		CameraSpringArm->PreviousDesiredLoc = Destination;
		CameraSpringArm->PreviousArmOrigin = Destination;
		CameraSpringArm->PreviousDesiredRot = DestinationRotation;
		bRestoreCameraLag = true;
	}

	TArray<AActor*> Gates;
	UGameplayStatics::GetAllActorsOfClass(this, AButterflyDreamGateActor::StaticClass(), Gates);
	for (AActor* Actor : Gates)
	{
		if (AButterflyDreamGateActor* Gate = Cast<AButterflyDreamGateActor>(Actor))
		{
			Gate->ResetGateState();
		}
	}
	RecoveryCooldown = 0.35f;
}

void AButterflyPawn::FellOutOfWorld(const UDamageType& DmgType)
{
	RecoverToSafePoint();
}

void AButterflyPawn::OutsideWorldBounds()
{
	RecoverToSafePoint();
}

void AButterflyPawn::HandleApplicationWillDeactivate()
{
	ClearFlightInput();
}

void AButterflyPawn::CollectComponentDynamicMaterials(
	UStaticMeshComponent* MeshComp,
	float FallbackEmissive,
	TArray<TObjectPtr<UMaterialInstanceDynamic>>& OutMIDs,
	TArray<float>& OutBaseEmissives)
{
	if (!MeshComp || !IsValid(MeshComp->GetStaticMesh()))
	{
		return;
	}

	const int32 NumMats = MeshComp->GetNumMaterials();
	for (int32 SlotIdx = 0; SlotIdx < NumMats; ++SlotIdx)
	{
		UMaterialInterface* CurrentMat = MeshComp->GetMaterial(SlotIdx);
		if (!CurrentMat)
		{
			continue;
		}

		UMaterialInstanceDynamic* MID = Cast<UMaterialInstanceDynamic>(CurrentMat);
		if (!MID)
		{
			MID = MeshComp->CreateDynamicMaterialInstance(SlotIdx, CurrentMat);
		}
		if (MID)
		{
			float BaseEmissive = FallbackEmissive;
			float ReadEmissive = 0.0f;
			if (MID->GetScalarParameterValue(ButterflyMaterialParams::EmissiveStrength, ReadEmissive) && ReadEmissive > 0.02f)
			{
				BaseEmissive = ReadEmissive;
			}
			else if (MID->GetScalarParameterValue(ButterflyMaterialParams::EmissiveScale, ReadEmissive) && ReadEmissive > 0.02f)
			{
				BaseEmissive = ReadEmissive;
			}
			OutMIDs.Add(MID);
			OutBaseEmissives.Add(BaseEmissive);
		}
	}
}

void AButterflyPawn::RefreshButterflyMaterials()
{
	BodyDynamicMaterials.Reset();
	BodyBaseEmissives.Reset();
	WingDynamicMaterials.Reset();
	WingBaseEmissives.Reset();

	CollectComponentDynamicMaterials(BodyMesh, 0.0f, BodyDynamicMaterials, BodyBaseEmissives);
	CollectComponentDynamicMaterials(LeftWingMesh, 0.0f, WingDynamicMaterials, WingBaseEmissives);
	CollectComponentDynamicMaterials(RightWingMesh, 0.0f, WingDynamicMaterials, WingBaseEmissives);

	bMaterialsInitialized = (WingDynamicMaterials.Num() > 0 || BodyDynamicMaterials.Num() > 0);
}

void AButterflyPawn::UpdateMaterialPulse()
{
	if (!bMaterialsInitialized && IsValid(LeftWingMesh->GetStaticMesh()))
	{
		RefreshButterflyMaterials();
	}

	const float WingbeatWave = 0.5f + 0.5f * FMath::Sin(WingFlapPhase);

	auto ApplyEmissivePulse = [this, WingbeatWave](
		const TArray<TObjectPtr<UMaterialInstanceDynamic>>& Materials,
		const TArray<float>& BaseEmissives)
	{
		for (int32 Idx = 0; Idx < Materials.Num(); ++Idx)
		{
			UMaterialInstanceDynamic* MID = Materials[Idx];
			if (!MID || !BaseEmissives.IsValidIndex(Idx) || BaseEmissives[Idx] <= 0.0f)
			{
				continue;
			}
			const float Emissive = BaseEmissives[Idx] * FMath::Lerp(0.90f, 1.10f, WingbeatWave) * (1.0f + BoostBlend * 0.15f);
			float ExistingValue = 0.0f;
			if (MID->GetScalarParameterValue(ButterflyMaterialParams::EmissiveStrength, ExistingValue))
			{
				MID->SetScalarParameterValue(ButterflyMaterialParams::EmissiveStrength, Emissive);
			}
			if (MID->GetScalarParameterValue(ButterflyMaterialParams::EmissiveScale, ExistingValue))
			{
				MID->SetScalarParameterValue(ButterflyMaterialParams::EmissiveScale, Emissive);
			}
		}
	};
	ApplyEmissivePulse(BodyDynamicMaterials, BodyBaseEmissives);
	ApplyEmissivePulse(WingDynamicMaterials, WingBaseEmissives);

}

void AButterflyPawn::Tick(float DeltaSeconds)
{
	if (!FMath::IsFinite(DeltaSeconds) || DeltaSeconds < 0.0f)
	{
		ClearFlightInput();
		return;
	}
	RecoveryCooldown = FMath::Max(0.0f, RecoveryCooldown - DeltaSeconds);
	const FVector CurrentPosition = GetActorLocation();
	const AController* CurrentController = GetController();
	const bool bHasMovementIntent = CurrentController && !CurrentController->IsMoveInputIgnored() &&
		(MoveInput.Size() > 0.1f || FMath::Abs(VerticalInput) > 0.1f);
	const float MovedDistance = FVector::Dist(CurrentPosition, PreviousPosition);
	if (bHasMovementIntent && MovedDistance < 0.25f && DeltaSeconds <= 0.25f && RecoveryCooldown <= 0.0f)
	{
		StuckTimer += DeltaSeconds;
	}
	else
	{
		StuckTimer = 0.0f;
	}
	PreviousPosition = CurrentPosition;
	if (StuckTimer >= StuckTimeoutSeconds)
	{
		UE_LOG(LogTemp, Warning, TEXT("LUX_RECOVERY Movement remained blocked for %.2f seconds"), StuckTimer);
		RecoverToSafePoint();
		return;
	}
	if (NeedsRecovery())
	{
		RecoverToSafePoint();
		return;
	}
	if (bRestoreCameraLag && CameraSpringArm)
	{
		CameraSpringArm->bEnableCameraLag = true;
		CameraSpringArm->bEnableCameraRotationLag = true;
		bRestoreCameraLag = false;
	}

	Super::Tick(DeltaSeconds);

	FlightTime += DeltaSeconds;
	FloatingMovement->MaxSpeed = bAccelerating ? BoostSpeed : BaseSpeed;
	BoostBlend = FMath::FInterpTo(BoostBlend, bAccelerating ? 1.0f : 0.0f, DeltaSeconds, 5.2f);

	const float InputMagnitude = FMath::Clamp(static_cast<float>(MoveInput.Size()) + FMath::Abs(VerticalInput), 0.0f, 1.0f);
	const bool bIsClimbingOrBoosting = bAccelerating || VerticalInput > 0.1f || MoveInput.Y > 0.15f;
	const float TargetGlide = bIsClimbingOrBoosting ? 0.0f : (InputMagnitude > 0.05f ? 0.42f : 0.68f);
	GlideBlend = FMath::FInterpTo(GlideBlend, TargetGlide, DeltaSeconds, 3.2f);

	const AController* PawnController = GetController();
	if (PawnController && !PawnController->IsMoveInputIgnored())
	{
		const FRotator ControlRotation = PawnController->GetControlRotation();
		const FRotationMatrix ControlAxes(FRotator(ControlRotation.Pitch, ControlRotation.Yaw, 0.0f));
		const float EffectiveForward = MoveInput.Y;
		const FVector WorldInput =
			ControlAxes.GetUnitAxis(EAxis::X) * EffectiveForward +
			ControlAxes.GetUnitAxis(EAxis::Y) * MoveInput.X +
			FVector::UpVector * VerticalInput;
		FloatingMovement->AddInputVector(WorldInput.GetClampedToMaxSize(1.0f));

		const float BobPitch = FMath::Sin(WingFlapPhase) * (1.0f - GlideBlend) * 3.2f;
		const float TargetPitch = FMath::Clamp(
			static_cast<float>(FRotator::NormalizeAxis(ControlRotation.Pitch)) * 0.45f + VerticalInput * 18.0f + BobPitch,
			-38.0f,
			38.0f);
		const float TargetRoll = FMath::Clamp(static_cast<float>(MoveInput.X) * 22.0f, -26.0f, 26.0f);
		const FRotator TargetActorRotation(TargetPitch, ControlRotation.Yaw, TargetRoll);
		SetActorRotation(FMath::RInterpTo(GetActorRotation(), TargetActorRotation, DeltaSeconds, 8.5f));
	}
	else
	{
		FloatingMovement->ConsumeInputVector();
	}

	// Speed-reactive FOV & Showcase 360 Orbit Camera cinematography
	if (CameraSpringArm && FlightCamera)
	{
		if (bShowcaseOrbit)
		{
			ShowcaseOrbitTime += DeltaSeconds;
			ShowcaseOrbitYaw = FMath::Fmod(ShowcaseOrbitYaw + ShowcaseOrbitSpeedDegrees * DeltaSeconds, 360.0f);
			const float OrbitPitch = -12.5f - 5.5f * FMath::Sin(ShowcaseOrbitTime * 0.85f);
			CameraSpringArm->SetWorldRotation(FRotator(OrbitPitch, ShowcaseOrbitYaw, 0.0f));
			CameraSpringArm->TargetArmLength = FMath::FInterpTo(CameraSpringArm->TargetArmLength, ShowcaseArmLength, DeltaSeconds, 4.8f);
			CameraSpringArm->SocketOffset = FMath::VInterpTo(CameraSpringArm->SocketOffset, FVector(0.0f, 0.0f, 32.0f), DeltaSeconds, 4.8f);
			CurrentCameraFOV = FMath::FInterpTo(CurrentCameraFOV, 72.0f, DeltaSeconds, 5.0f);
		}
		else
		{
			const float DesiredArm = FMath::Lerp(210.0f, 250.0f, BoostBlend);
			const float DesiredFOV = FMath::Lerp(CruiseCameraFOV, BoostCameraFOV, BoostBlend);
			CameraSpringArm->TargetArmLength = FMath::FInterpTo(CameraSpringArm->TargetArmLength, DesiredArm, DeltaSeconds, 5.0f);
			CameraSpringArm->SocketOffset = FMath::VInterpTo(CameraSpringArm->SocketOffset, FVector(0.0f, 0.0f, 38.0f), DeltaSeconds, 5.0f);
			CurrentCameraFOV = FMath::FInterpTo(CurrentCameraFOV, DesiredFOV, DeltaSeconds, 5.5f);
		}
		FlightCamera->SetFieldOfView(CurrentCameraFOV);
	}

	UpdateMeshVisibility();
	if (IsValid(LeftWingMesh->GetStaticMesh()) && IsValid(RightWingMesh->GetStaticMesh()))
	{
		const float SpeedRatio = static_cast<float>(FloatingMovement->Velocity.Size()) / FMath::Max(1.0f, BaseSpeed);
		const float DynamicFreq = WingFlapFrequency * FMath::Lerp(0.75f, bAccelerating ? 1.68f : 1.16f, FMath::Clamp(SpeedRatio, 0.0f, 1.0f));
		WingFlapPhase = FMath::Fmod(WingFlapPhase + DeltaSeconds * DynamicFreq * 2.0f * PI, 2.0f * PI);

		const float AsymmetricWave = (FMath::Sin(WingFlapPhase) + 0.28f * FMath::Sin(2.0f * WingFlapPhase - 0.45f)) * 0.85f;
		const float ActiveFlapAngle = AsymmetricWave * WingFlapAmplitudeDegrees;
		const float GlideDihedralAngle = 14.0f + 4.5f * FMath::Sin(FlightTime * 2.4f);
		const float FinalWingRoll = FMath::Lerp(ActiveFlapAngle, GlideDihedralAngle, GlideBlend);
		const float WingFeatherPitch = FMath::Cos(WingFlapPhase) * 5.5f * (1.0f - GlideBlend);

		LeftWingPivot->SetRelativeRotation(FRotator(WingFeatherPitch, 0.0f, FinalWingRoll));
		RightWingPivot->SetRelativeRotation(FRotator(WingFeatherPitch, 0.0f, -FinalWingRoll));
	}

	UpdateMaterialPulse();

	if (WakeRibbon)
	{
		WakeRibbon->SetVariableFloat(TEXT("User.Boost"), BoostBlend);
		WakeRibbon->SetVariableFloat(TEXT("User.WingBeat"), WingFlapFrequency * FMath::Lerp(1.0f, 1.65f, BoostBlend));
		WakeRibbon->SetVariableFloat(TEXT("User.Width"), 7.0f);
		WakeRibbon->SetVariableVec3(TEXT("User.Color"), FVector(0.45f + 0.35f * BoostBlend, 0.78f - 0.08f * BoostBlend, 1.0f - 0.15f * BoostBlend));
	}

	if (ButterflyAuraLight)
	{
		const float AuraPulse = 1.0f + 0.22f * FMath::Sin(WingFlapPhase);
		ButterflyAuraLight->SetIntensity(FMath::Lerp(1.8f, 3.0f, BoostBlend) * AuraPulse);
	}

	if (ButterflyGoldRimLight)
	{
		const float GoldPulse = 1.0f + 0.18f * FMath::Cos(WingFlapPhase);
		ButterflyGoldRimLight->SetIntensity(FMath::Lerp(1.2f, 2.0f, BoostBlend) * GoldPulse);
	}
}

void AButterflyPawn::SetupPlayerInputComponent(UInputComponent* PlayerInputComponent)
{
	Super::SetupPlayerInputComponent(PlayerInputComponent);

	UEnhancedInputComponent* EnhancedInput = Cast<UEnhancedInputComponent>(PlayerInputComponent);
	APlayerController* PlayerController = Cast<APlayerController>(GetController());
	if (!EnhancedInput || !PlayerController)
	{
		return;
	}

	CreateInputObjects();
	ULocalPlayer* LocalPlayer = PlayerController->GetLocalPlayer();
	if (!LocalPlayer)
	{
		return;
	}

	if (UEnhancedInputLocalPlayerSubsystem* InputSubsystem = LocalPlayer->GetSubsystem<UEnhancedInputLocalPlayerSubsystem>())
	{
		InputSubsystem->AddMappingContext(FlightInputContext, 0);
		MappedLocalPlayer = LocalPlayer;
	}

	EnhancedInput->BindAction(MoveAction, ETriggerEvent::Triggered, this, &AButterflyPawn::HandleMove);
	EnhancedInput->BindAction(MoveAction, ETriggerEvent::Completed, this, &AButterflyPawn::StopMove);
	EnhancedInput->BindAction(MoveAction, ETriggerEvent::Canceled, this, &AButterflyPawn::StopMove);
	EnhancedInput->BindAction(LookAction, ETriggerEvent::Triggered, this, &AButterflyPawn::HandleLook);
	EnhancedInput->BindAction(VerticalAction, ETriggerEvent::Triggered, this, &AButterflyPawn::HandleVertical);
	EnhancedInput->BindAction(VerticalAction, ETriggerEvent::Completed, this, &AButterflyPawn::StopVertical);
	EnhancedInput->BindAction(VerticalAction, ETriggerEvent::Canceled, this, &AButterflyPawn::StopVertical);
	EnhancedInput->BindAction(AccelerateAction, ETriggerEvent::Started, this, &AButterflyPawn::StartAccelerate);
	EnhancedInput->BindAction(AccelerateAction, ETriggerEvent::Completed, this, &AButterflyPawn::StopAccelerate);
	EnhancedInput->BindAction(AccelerateAction, ETriggerEvent::Canceled, this, &AButterflyPawn::StopAccelerate);
	EnhancedInput->BindAction(OrbitAction, ETriggerEvent::Started, this, &AButterflyPawn::ToggleShowcaseOrbit);
	EnhancedInput->BindAction(RecoveryAction, ETriggerEvent::Started, this, &AButterflyPawn::HandleRecovery);
	EnhancedInput->BindAction(MenuAction, ETriggerEvent::Started, this, &AButterflyPawn::ToggleMenu);
}

void AButterflyPawn::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	ClearFlightInput();
	FCoreDelegates::ApplicationWillDeactivateDelegate.RemoveAll(this);
	if (MappedLocalPlayer.IsValid() && FlightInputContext)
	{
		if (UEnhancedInputLocalPlayerSubsystem* InputSubsystem = MappedLocalPlayer->GetSubsystem<UEnhancedInputLocalPlayerSubsystem>())
		{
			InputSubsystem->RemoveMappingContext(FlightInputContext);
		}
	}
	MappedLocalPlayer.Reset();

	Super::EndPlay(EndPlayReason);
}

void AButterflyPawn::ClearFlightInput()
{
	MoveInput = FVector2D::ZeroVector;
	VerticalInput = 0.0f;
	bAccelerating = false;
	if (FloatingMovement)
	{
		FloatingMovement->ConsumeInputVector();
		FloatingMovement->StopMovementImmediately();
		FloatingMovement->MaxSpeed = BaseSpeed;
	}
}

void AButterflyPawn::ToggleShowcaseOrbit()
{
	if (const AController* PawnController = GetController(); PawnController && PawnController->IsMoveInputIgnored())
	{
		return;
	}
	SetShowcaseOrbitActive(!bShowcaseOrbit);
}

void AButterflyPawn::SetShowcaseOrbitActive(bool bEnable)
{
	if (bShowcaseOrbit == bEnable)
	{
		return;
	}

	bShowcaseOrbit = bEnable;
	if (CameraSpringArm)
	{
		if (bShowcaseOrbit)
		{
			const AController* PawnController = GetController();
			ShowcaseOrbitYaw = static_cast<float>(PawnController ? PawnController->GetControlRotation().Yaw : GetActorRotation().Yaw);
			ShowcaseOrbitTime = 0.0f;
			CameraSpringArm->bUsePawnControlRotation = false;
			CameraSpringArm->SetUsingAbsoluteRotation(true);
			CameraSpringArm->SetWorldRotation(FRotator(-15.5f, ShowcaseOrbitYaw, 0.0f));
		}
		else
		{
			CameraSpringArm->SetUsingAbsoluteRotation(false);
			CameraSpringArm->bUsePawnControlRotation = true;
		}
	}
}

void AButterflyPawn::CreateInputObjects()
{
	if (FlightInputContext)
	{
		return;
	}

	MoveAction = NewObject<UInputAction>(this, TEXT("IA_Move"), RF_Transient);
	MoveAction->ValueType = EInputActionValueType::Axis2D;
	MoveAction->AccumulationBehavior = EInputActionAccumulationBehavior::Cumulative;

	LookAction = NewObject<UInputAction>(this, TEXT("IA_Look"), RF_Transient);
	LookAction->ValueType = EInputActionValueType::Axis2D;

	VerticalAction = NewObject<UInputAction>(this, TEXT("IA_Vertical"), RF_Transient);
	VerticalAction->ValueType = EInputActionValueType::Axis1D;
	VerticalAction->AccumulationBehavior = EInputActionAccumulationBehavior::Cumulative;

	AccelerateAction = NewObject<UInputAction>(this, TEXT("IA_Accelerate"), RF_Transient);
	AccelerateAction->ValueType = EInputActionValueType::Boolean;

	OrbitAction = NewObject<UInputAction>(this, TEXT("IA_ShowcaseOrbit"), RF_Transient);
	OrbitAction->ValueType = EInputActionValueType::Boolean;

	RecoveryAction = NewObject<UInputAction>(this, TEXT("IA_Recovery"), RF_Transient);
	RecoveryAction->ValueType = EInputActionValueType::Boolean;

	MenuAction = NewObject<UInputAction>(this, TEXT("IA_Menu"), RF_Transient);
	MenuAction->ValueType = EInputActionValueType::Boolean;

	FlightInputContext = NewObject<UInputMappingContext>(this, TEXT("IMC_ButterflyFlight"), RF_Transient);
	AddMoveKey(EKeys::W, true, false);
	AddMoveKey(EKeys::S, true, true);
	AddMoveKey(EKeys::D, false, false);
	AddMoveKey(EKeys::A, false, true);
	FlightInputContext->MapKey(LookAction, EKeys::Mouse2D);
	FlightInputContext->MapKey(VerticalAction, EKeys::SpaceBar);
	FEnhancedActionKeyMapping& DescendMapping = FlightInputContext->MapKey(VerticalAction, EKeys::C);
	DescendMapping.Modifiers.Add(NewObject<UInputModifierNegate>(FlightInputContext, NAME_None, RF_Transient));
	FlightInputContext->MapKey(AccelerateAction, EKeys::LeftShift);
	FlightInputContext->MapKey(AccelerateAction, EKeys::RightShift);
	FlightInputContext->MapKey(OrbitAction, EKeys::P);
	FlightInputContext->MapKey(RecoveryAction, EKeys::R);
	FlightInputContext->MapKey(MenuAction, EKeys::Escape);
	FlightInputContext->MapKey(MenuAction, EKeys::Tab);
}

void AButterflyPawn::AddMoveKey(FKey Key, bool bUseYAxis, bool bNegate)
{
	FEnhancedActionKeyMapping& Mapping = FlightInputContext->MapKey(MoveAction, Key);
	if (bUseYAxis)
	{
		UInputModifierSwizzleAxis* Swizzle = NewObject<UInputModifierSwizzleAxis>(FlightInputContext, NAME_None, RF_Transient);
		Swizzle->Order = EInputAxisSwizzle::YXZ;
		Mapping.Modifiers.Add(Swizzle);
	}
	if (bNegate)
	{
		Mapping.Modifiers.Add(NewObject<UInputModifierNegate>(FlightInputContext, NAME_None, RF_Transient));
	}
}

void AButterflyPawn::UpdateMeshVisibility()
{
	const bool bBodyValid = IsValid(BodyMesh->GetStaticMesh());
	BodyMesh->SetHiddenInGame(!bBodyValid);
	BodyMesh->SetVisibility(bBodyValid);

	const bool bLeftWingValid = IsValid(LeftWingMesh->GetStaticMesh());
	LeftWingMesh->SetHiddenInGame(!bLeftWingValid);
	LeftWingMesh->SetVisibility(bLeftWingValid);

	const bool bRightWingValid = IsValid(RightWingMesh->GetStaticMesh());
	RightWingMesh->SetHiddenInGame(!bRightWingValid);
	RightWingMesh->SetVisibility(bRightWingValid);
}

void AButterflyPawn::HandleMove(const FInputActionValue& Value)
{
	if (const AController* PawnController = GetController(); PawnController && !PawnController->IsMoveInputIgnored())
	{
		MoveInput = Value.Get<FVector2D>();
	}
}

void AButterflyPawn::HandleLook(const FInputActionValue& Value)
{
	AController* PawnController = GetController();
	if (!PawnController || PawnController->IsLookInputIgnored())
	{
		return;
	}

	const FVector2D LookInput = Value.Get<FVector2D>() * MouseSensitivity;
	if (bShowcaseOrbit)
	{
		ShowcaseOrbitYaw = FMath::Fmod(ShowcaseOrbitYaw + static_cast<float>(LookInput.X), 360.0f);
		return;
	}

	FRotator ControlRotation = PawnController->GetControlRotation();
	ControlRotation.Yaw += LookInput.X;
	ControlRotation.Pitch = FMath::Clamp(
		FRotator::NormalizeAxis(ControlRotation.Pitch - LookInput.Y), -70.0, 70.0);
	ControlRotation.Roll = 0.0f;
	PawnController->SetControlRotation(ControlRotation);
}

void AButterflyPawn::HandleVertical(const FInputActionValue& Value)
{
	if (const AController* PawnController = GetController(); PawnController && !PawnController->IsMoveInputIgnored())
	{
		VerticalInput = FMath::Clamp(Value.Get<float>(), -1.0f, 1.0f);
	}
}

void AButterflyPawn::StopMove()
{
	MoveInput = FVector2D::ZeroVector;
}

void AButterflyPawn::StopVertical()
{
	VerticalInput = 0.0f;
}

void AButterflyPawn::StartAccelerate()
{
	if (const AController* PawnController = GetController(); PawnController && !PawnController->IsMoveInputIgnored())
	{
		bAccelerating = true;
	}
}

void AButterflyPawn::StopAccelerate()
{
	bAccelerating = false;
}

#if WITH_DEV_AUTOMATION_TESTS
void AButterflyPawn::DreamTestInputKey(FName KeyName, bool bPressed)
{
	if (APlayerController* PlayerController = Cast<APlayerController>(GetController()))
	{
		const FKey Key(KeyName);
		if (Key.IsValid())
		{
			PlayerController->InputKey(FInputKeyEventArgs::CreateSimulated(
				Key,
				bPressed ? IE_Pressed : IE_Released,
				bPressed ? 1.0f : 0.0f));
		}
	}
}
#else
void AButterflyPawn::DreamTestInputKey(FName KeyName, bool bPressed)
{
}
#endif

void AButterflyPawn::HandleRecovery()
{
	if (const AController* PawnController = GetController(); PawnController && PawnController->IsMoveInputIgnored())
	{
		return;
	}
	RecoverToSafePoint();
}

void AButterflyPawn::ToggleMenu()
{
	if (AButterflyPlayerController* ButterflyController = Cast<AButterflyPlayerController>(GetController()))
	{
		ButterflyController->ToggleSceneMenu();
	}
}
