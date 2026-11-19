#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "ButterflyDreamPropActor.generated.h"

class UPointLightComponent;
class USceneComponent;
class UStaticMesh;
class UStaticMeshComponent;

UCLASS()
class BUTTERFLYDREAM_API AButterflyDreamPropActor : public AActor
{
	GENERATED_BODY()

public:
	AButterflyDreamPropActor();

	virtual void BeginPlay() override;
	virtual void Tick(float DeltaSeconds) override;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components")
	TObjectPtr<USceneComponent> SceneRoot;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components")
	TObjectPtr<UStaticMeshComponent> PropMesh;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components")
	TObjectPtr<UPointLightComponent> GlowLight;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Motion")
	float BobAmplitude = 22.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Motion")
	float BobSpeed = 1.1f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Motion")
	float SpinSpeedYaw = 10.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Motion")
	float SwayAmplitudeDegrees = 3.2f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Motion")
	float SwaySpeed = 1.35f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Motion")
	float BreatheScaleAmplitude = 0.025f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Motion")
	float PhaseOffset = 0.0f;

	UFUNCTION(BlueprintCallable, Category = "DreamProp")
	void ConfigureProp(
		UStaticMesh* MeshAsset,
		float Scale,
		bool bEnableLight,
		FLinearColor LightColor,
		float LightIntensity,
		float LightRadius);

private:
	FVector BaseLocation = FVector::ZeroVector;
	FVector BaseMeshScale = FVector::OneVector;
	float BaseLightIntensity = 0.0f;
	float ElapsedTime = 0.0f;
	bool bHasBaseLocation = false;
};
