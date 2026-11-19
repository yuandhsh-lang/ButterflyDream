#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Pawn.h"
#include "ButterflyPawn.generated.h"

class UCameraComponent;
class UCapsuleComponent;
class UFloatingPawnMovement;
class UInputAction;
class UInputMappingContext;
class ULocalPlayer;
class UMaterialInstanceDynamic;
class UPointLightComponent;
class USceneComponent;
class USpringArmComponent;
class UStaticMeshComponent;
class UNiagaraComponent;
class UButterflyStorySubsystem;
struct FInputActionValue;

UCLASS()
class BUTTERFLYDREAM_API AButterflyPawn : public APawn
{
	GENERATED_BODY()

public:
	AButterflyPawn();

	virtual void BeginPlay() override;
	virtual void Tick(float DeltaSeconds) override;
	virtual void SetupPlayerInputComponent(UInputComponent* PlayerInputComponent) override;
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;
	virtual void FellOutOfWorld(const UDamageType& DmgType) override;
	virtual void OutsideWorldBounds() override;

	void ClearFlightInput();

	UFUNCTION(BlueprintCallable, Category = "Flight")
	void RecoverToSafePoint();

	UFUNCTION(BlueprintCallable, Category = "Materials")
	void RefreshButterflyMaterials();

	UFUNCTION(BlueprintCallable, Category = "Flight")
	void ToggleShowcaseOrbit();

	UFUNCTION(BlueprintCallable, Category = "Flight")
	void SetShowcaseOrbitActive(bool bEnable);

	UFUNCTION(BlueprintPure, Category = "Flight")
	bool IsAccelerating() const { return bAccelerating; }

	UFUNCTION(BlueprintPure, Category = "Flight")
	bool IsShowcaseOrbitActive() const { return bShowcaseOrbit; }

	UFUNCTION(BlueprintCallable, Category = "Development|Input")
	void DreamTestInputKey(FName KeyName, bool bPressed);

protected:
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components")
	TObjectPtr<UCapsuleComponent> Capsule;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components")
	TObjectPtr<UStaticMeshComponent> BodyMesh;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components")
	TObjectPtr<USceneComponent> LeftWingPivot;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components")
	TObjectPtr<USceneComponent> RightWingPivot;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components")
	TObjectPtr<UStaticMeshComponent> LeftWingMesh;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components")
	TObjectPtr<UStaticMeshComponent> RightWingMesh;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components")
	TObjectPtr<UPointLightComponent> ButterflyAuraLight;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components")
	TObjectPtr<UPointLightComponent> ButterflyGoldRimLight;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components")
	TObjectPtr<USpringArmComponent> CameraSpringArm;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components")
	TObjectPtr<UCameraComponent> FlightCamera;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components")
	TObjectPtr<UNiagaraComponent> WakeRibbon;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components")
	TObjectPtr<UFloatingPawnMovement> FloatingMovement;

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Flight", meta = (ClampMin = "0.0"))
	float BaseSpeed = 620.0f;

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Flight", meta = (ClampMin = "0.0"))
	float BoostSpeed = 1280.0f;

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Flight", meta = (ClampMin = "0.0"))
	float MouseSensitivity = 1.0f;

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Flight", meta = (ClampMin = "1000.0"))
	float SafeFlightRadius = 30000.0f;

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Flight", meta = (ClampMin = "0.5"))
	float StuckTimeoutSeconds = 3.0f;

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Camera", meta = (ClampMin = "40.0", ClampMax = "130.0"))
	float CruiseCameraFOV = 72.0f;

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Camera", meta = (ClampMin = "40.0", ClampMax = "130.0"))
	float BoostCameraFOV = 82.0f;

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Camera", meta = (ClampMin = "20.0"))
	float ShowcaseArmLength = 230.0f;

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Camera")
	float ShowcaseOrbitSpeedDegrees = 28.0f;

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Wings", meta = (ClampMin = "0.0"))
	float WingFlapFrequency = 5.4f;

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Wings", meta = (ClampMin = "0.0", ClampMax = "89.0"))
	float WingFlapAmplitudeDegrees = 40.0f;

private:
	UPROPERTY(Transient)
	TObjectPtr<UInputMappingContext> FlightInputContext;

	UPROPERTY(Transient)
	TObjectPtr<UInputAction> MoveAction;

	UPROPERTY(Transient)
	TObjectPtr<UInputAction> LookAction;

	UPROPERTY(Transient)
	TObjectPtr<UInputAction> VerticalAction;

	UPROPERTY(Transient)
	TObjectPtr<UInputAction> AccelerateAction;

	UPROPERTY(Transient)
	TObjectPtr<UInputAction> OrbitAction;

	UPROPERTY(Transient)
	TObjectPtr<UInputAction> RecoveryAction;

	UPROPERTY(Transient)
	TObjectPtr<UInputAction> MenuAction;

	UPROPERTY(Transient)
	TArray<TObjectPtr<UMaterialInstanceDynamic>> BodyDynamicMaterials;

	UPROPERTY(Transient)
	TArray<TObjectPtr<UMaterialInstanceDynamic>> WingDynamicMaterials;

	TArray<float> BodyBaseEmissives;
	TArray<float> WingBaseEmissives;

	TWeakObjectPtr<ULocalPlayer> MappedLocalPlayer;
	FVector2D MoveInput = FVector2D::ZeroVector;
	FVector SafePointLocation = FVector::ZeroVector;
	FRotator SafePointRotation = FRotator::ZeroRotator;
	float VerticalInput = 0.0f;
	float WingFlapPhase = 0.0f;
	float GlideBlend = 0.0f;
	float BoostBlend = 0.0f;
	float FlightTime = 0.0f;
	float CurrentCameraFOV = 72.0f;
	float ShowcaseOrbitYaw = 0.0f;
	float ShowcaseOrbitTime = 0.0f;
	float RecoveryCooldown = 0.0f;
	FVector PreviousPosition = FVector::ZeroVector;
	float StuckTimer = 0.0f;
	bool bAccelerating = false;
	bool bShowcaseOrbit = false;
	bool bMaterialsInitialized = false;
	bool bHasSafePoint = false;
	bool bRestoreCameraLag = false;

	void CreateInputObjects();
	void AddMoveKey(FKey Key, bool bUseYAxis, bool bNegate);
	void UpdateMeshVisibility();
	void UpdateMaterialPulse();
	void CacheSafePoint();
	bool NeedsRecovery() const;
	void HandleApplicationWillDeactivate();
	void CollectComponentDynamicMaterials(
		UStaticMeshComponent* MeshComp,
		float FallbackEmissive,
		TArray<TObjectPtr<UMaterialInstanceDynamic>>& OutMIDs,
		TArray<float>& OutBaseEmissives);
	void HandleMove(const FInputActionValue& Value);
	void HandleLook(const FInputActionValue& Value);
	void HandleVertical(const FInputActionValue& Value);
	void StopMove();
	void StopVertical();
	void StartAccelerate();
	void StopAccelerate();
	void HandleRecovery();
	void ToggleMenu();
};
