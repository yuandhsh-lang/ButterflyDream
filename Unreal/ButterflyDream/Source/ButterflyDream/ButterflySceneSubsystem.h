#pragma once

#include "CoreMinimal.h"
#include "Engine/EngineBaseTypes.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "TimerManager.h"
#include "UObject/UObjectGlobals.h"
#include "ButterflySceneSubsystem.generated.h"

UCLASS()
class BUTTERFLYDREAM_API UButterflySceneSubsystem : public UGameInstanceSubsystem
{
	GENERATED_BODY()

public:
	virtual void Initialize(FSubsystemCollectionBase& Collection) override;
	virtual void Deinitialize() override;

	bool RequestSceneSwitch(const FString& MapPackageName, FString& OutStatus);
	bool IsSceneSwitchInProgress() const { return bSceneSwitchInProgress; }
	const FString& GetLastStatus() const { return LastStatus; }
	const FString& GetPendingMapPackageName() const { return PendingMapPackageName; }

private:
	bool bSceneSwitchInProgress = false;
	FString LastStatus;
	FString PendingMapPackageName;
	FTimerHandle SceneSwitchTimeoutHandle;
	float SceneSwitchTimeoutSeconds = 180.0f;

	void HandlePackageLoaded(const FName& PackageName, UPackage* LoadedPackage, EAsyncLoadingResult::Type Result);
	void HandlePostLoadMap(UWorld* LoadedWorld);
	void HandleTravelFailure(UWorld* FailedWorld, ETravelFailure::Type FailureType, const FString& ErrorString);
	void HandleSceneSwitchTimeout();
	void FailSceneSwitch(const FString& Reason);
};
