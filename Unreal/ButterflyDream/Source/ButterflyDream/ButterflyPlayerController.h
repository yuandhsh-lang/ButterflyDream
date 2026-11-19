#pragma once

#include "CoreMinimal.h"
#include "GameFramework/PlayerController.h"
#include "ButterflyPlayerController.generated.h"

class AButterflyDreamGateActor;
class UButterflyHudWidget;
class UButterflySceneMenuWidget;

UCLASS()
class BUTTERFLYDREAM_API AButterflyPlayerController : public APlayerController
{
	GENERATED_BODY()

public:
	virtual void BeginPlay() override;
	virtual void Tick(float DeltaSeconds) override;
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;

	void ToggleSceneMenu();
	void CloseSceneMenu();
	void SetFlightInputEnabled(bool bEnabled);
	void HandleSceneLoaded();
	void HandleSceneSwitchFailed(const FString& Failure);

	UButterflyHudWidget* GetButterflyHud() const { return HudWidget; }
	bool IsSceneMenuOpen() const { return bSceneMenuOpen; }

	void NotifyStoryVerseTriggered(
		const FText& VerseText,
		const FText& NoteText,
		const FLinearColor& TintColor,
		float DurationSeconds);

private:
	UPROPERTY(Transient)
	TObjectPtr<UButterflySceneMenuWidget> SceneMenu;

	UPROPERTY(Transient)
	TObjectPtr<UButterflyHudWidget> HudWidget;

	TArray<TWeakObjectPtr<AButterflyDreamGateActor>> CachedGates;
	float GateCacheRefreshTimer = 0.0f;
	float SceneErrorDisplaySeconds = 0.0f;

	bool bSceneMenuOpen = false;
	bool bHudInitialized = false;
	int32 LastRealmIndex = -1;
	int32 LastFlightModeIndex = -1;
	bool bLastNearGate = false;
	int32 LastResonancePct = -1;
	int32 LastOpenPct = -1;
	int32 LastGateStateIndex = -1;
	FString LastGateTitle;
	FString LastGateFailure;
	FString SceneErrorMessage;

	void OpenSceneMenu();
	void RefreshGateCache();
	bool IsSceneSwitchInProgress() const;
	void UpdateHudHint(float DeltaSeconds);
};
