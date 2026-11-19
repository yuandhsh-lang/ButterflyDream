#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "DreamGateResonance.h"
#include "ButterflyDreamGateActor.generated.h"

class UBoxComponent;
class UNiagaraComponent;
class UPointLightComponent;
class USceneComponent;
class UStaticMeshComponent;

UCLASS()
class BUTTERFLYDREAM_API AButterflyDreamGateActor : public AActor
{
	GENERATED_BODY()

public:
	AButterflyDreamGateActor();

	virtual void OnConstruction(const FTransform& Transform) override;
	virtual void BeginPlay() override;
	virtual void Tick(float DeltaSeconds) override;

	UFUNCTION(BlueprintPure, Category = "DreamGate")
	float GetCurrentOpenAlpha() const { return Resonance.OpenAlpha; }

	UFUNCTION(BlueprintPure, Category = "DreamGate")
	bool IsPlayerNearGate() const { return bPlayerNear; }

	UFUNCTION(BlueprintPure, Category = "DreamGate")
	float GetResonancePercent() const { return Resonance.Charge * 100.0f; }

	UFUNCTION(BlueprintPure, Category = "DreamGate")
	float GetCharge() const { return Resonance.Charge; }

	UFUNCTION(BlueprintPure, Category = "DreamGate")
	EDreamGateState GetGateState() const { return Resonance.State; }

	UFUNCTION(BlueprintPure, Category = "DreamGate")
	FString GetGateStateName() const;

	UFUNCTION(BlueprintPure, Category = "DreamGate")
	bool IsResonanceReady() const { return Resonance.State == EDreamGateState::Ready; }

	UFUNCTION(BlueprintPure, Category = "DreamGate")
	bool IsTraversing() const { return Resonance.State == EDreamGateState::Traversing; }

	UFUNCTION(BlueprintPure, Category = "DreamGate")
	bool HasTransitionFailure() const { return Resonance.State == EDreamGateState::Error; }

	UFUNCTION(BlueprintPure, Category = "DreamGate")
	FString GetLastFailure() const { return Resonance.LastFailure; }

	UFUNCTION(BlueprintPure, Category = "DreamGate")
	FString GetTargetMapPackageName() const { return TargetMapPackageName; }

	UFUNCTION(BlueprintPure, Category = "DreamGate")
	float GetTunnelExitDistance() const;

	UFUNCTION(BlueprintPure, Category = "DreamGate")
	FVector GetTunnelExitWorldLocation() const;

	UFUNCTION(BlueprintPure, Category = "DreamGate")
	FVector GetPortalCenterWorldLocation() const { return GetActorTransform().TransformPosition(PortalCenterLocalOffset); }

	UFUNCTION(BlueprintPure, Category = "DreamGate")
	float GetTunnelRingSpacing() const;

	UFUNCTION(BlueprintCallable, Category = "DreamGate")
	void ConfigureHingeOffsets(
		FVector InLeftHinge,
		FVector InRightHinge,
		FVector InInnerRing,
		FVector InPortalCenter);

	UFUNCTION(BlueprintCallable, Category = "DreamGate")
	void ApplyGatePreset(bool bRotaryStarGate);

	UFUNCTION(BlueprintCallable, Category = "DreamGate")
	void ResetGateState();

	void HandleSceneSwitchFailure(const FString& Failure);

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "DreamGate")
	FString GateTitle = TEXT("星海梦境 ｜ 共鸣仙门");

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "DreamGate")
	FString TargetMapPackageName = TEXT("/Game/Maps/Lux_StarSeaDream");

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "DreamGate", meta = (ClampMin = "1.0"))
	float ResonanceDistance = 1600.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "DreamGate", meta = (ClampMin = "0.1"))
	float ChargeSeconds = FDreamGateResonance::DefaultChargeSeconds;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "DreamGate", meta = (ClampMin = "0.1"))
	float OpeningSeconds = FDreamGateResonance::DefaultOpeningSeconds;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "DreamGate")
	float MaxDoorOpenDegrees = 72.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "DreamGate")
	bool bUseRotaryInnerRingMode = false;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "DreamGate", meta = (ClampMin = "0.0"))
	float TunnelRingSpacingOverride = 0.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "DreamGate", meta = (ClampMin = "1.0"))
	float PortalApertureHalfWidth = 90.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "DreamGate", meta = (ClampMin = "1.0"))
	float PortalApertureHalfHeight = 105.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "DreamGate", meta = (ClampMin = "0.0"))
	float TraversalCapsuleRadius = 10.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "DreamGate", meta = (ClampMin = "1.0"))
	float TraversalCapsuleHalfHeight = 10.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "DreamGate")
	FVector PortalCenterLocalOffset = FVector(0.0f, 0.0f, 130.0f);

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "DreamGate")
	FVector LeftHingeLocalOffset = FVector(-88.4f, 12.4f, 136.6f);

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "DreamGate")
	FVector RightHingeLocalOffset = FVector(85.2f, 11.3f, 118.8f);

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "DreamGate")
	FVector InnerRingLocalOffset = FVector(0.0f, 0.0f, 24.9f);

protected:
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components")
	TObjectPtr<USceneComponent> SceneRoot;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components")
	TObjectPtr<UStaticMeshComponent> GateFrameMesh;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components")
	TObjectPtr<USceneComponent> LeftDoorPivot;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components")
	TObjectPtr<UStaticMeshComponent> LeftDoorMesh;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components")
	TObjectPtr<USceneComponent> RightDoorPivot;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components")
	TObjectPtr<UStaticMeshComponent> RightDoorMesh;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Collision")
	TObjectPtr<UBoxComponent> LeftDoorCollision;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Collision")
	TObjectPtr<UBoxComponent> RightDoorCollision;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Collision")
	TObjectPtr<UBoxComponent> LeftFrameCollision;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Collision")
	TObjectPtr<UBoxComponent> RightFrameCollision;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Collision")
	TObjectPtr<UBoxComponent> TopFrameCollision;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Collision")
	TObjectPtr<UBoxComponent> BottomFrameCollision;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components")
	TArray<TObjectPtr<UStaticMeshComponent>> TunnelRingMeshes;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Collision")
	TArray<TObjectPtr<UBoxComponent>> TunnelRingCollisionBoxes;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components")
	TObjectPtr<UPointLightComponent> GateCoreLight;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components")
	TObjectPtr<UPointLightComponent> TunnelGuideLight;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components")
	TObjectPtr<UNiagaraComponent> GateReformNiagara;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components")
	TObjectPtr<UNiagaraComponent> TunnelRibbonNiagara;

private:
	static constexpr int32 NumTunnelRings = FDreamGateResonance::TunnelRingCount;

	float AnimTime = 0.0f;
	float InnerRingAngleDeg = 0.0f;
	bool bPlayerNear = false;
	bool bTargetMapValid = false;
	FDreamGateResonance Resonance;

	void RefreshComponentTransforms();
	void UpdateCollisionState();
	bool IsCenterSweepClear(const APawn* PlayerPawn) const;
	void ConfigureProxy(UBoxComponent* Proxy) const;
};
