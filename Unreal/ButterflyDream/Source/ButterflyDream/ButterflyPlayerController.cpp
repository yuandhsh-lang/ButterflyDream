#include "ButterflyPlayerController.h"

#include "Blueprint/UserWidget.h"
#include "ButterflyDreamGateActor.h"
#include "ButterflyHudWidget.h"
#include "ButterflyPawn.h"
#include "ButterflySceneMenuWidget.h"
#include "ButterflySceneSubsystem.h"
#include "ButterflyTypography.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"

void AButterflyPlayerController::BeginPlay()
{
	Super::BeginPlay();
	PrimaryActorTick.bCanEverTick = true;

	if (IsLocalPlayerController())
	{
		HudWidget = CreateWidget<UButterflyHudWidget>(this, UButterflyHudWidget::StaticClass());
		if (HudWidget)
		{
			HudWidget->SetVisibility(ESlateVisibility::HitTestInvisible);
			HudWidget->AddToViewport(0);
		}

		SceneMenu = CreateWidget<UButterflySceneMenuWidget>(this, UButterflySceneMenuWidget::StaticClass());
		if (SceneMenu)
		{
			SceneMenu->SetVisibility(ESlateVisibility::Collapsed);
			SceneMenu->AddToViewport(10);
		}
	}

	HandleSceneLoaded();
}

void AButterflyPlayerController::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	UpdateHudHint(DeltaSeconds);
}

void AButterflyPlayerController::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	if (HudWidget)
	{
		HudWidget->RemoveFromParent();
		HudWidget = nullptr;
	}
	if (SceneMenu)
	{
		SceneMenu->RemoveFromParent();
		SceneMenu = nullptr;
	}
	CachedGates.Reset();
	bSceneMenuOpen = false;

	Super::EndPlay(EndPlayReason);
}

void AButterflyPlayerController::NotifyStoryVerseTriggered(
	const FText& VerseText,
	const FText& NoteText,
	const FLinearColor& TintColor,
	float DurationSeconds)
{
	if (HudWidget)
	{
		HudWidget->ShowStoryVerseEcho(VerseText, NoteText, TintColor, DurationSeconds);
	}
}

void AButterflyPlayerController::RefreshGateCache()
{
	CachedGates.Reset();
	TArray<AActor*> FoundActors;
	UGameplayStatics::GetAllActorsOfClass(this, AButterflyDreamGateActor::StaticClass(), FoundActors);
	for (AActor* Actor : FoundActors)
	{
		if (AButterflyDreamGateActor* Gate = Cast<AButterflyDreamGateActor>(Actor))
		{
			CachedGates.Add(Gate);
		}
	}
	GateCacheRefreshTimer = 1.5f;
}

void AButterflyPlayerController::UpdateHudHint(float DeltaSeconds)
{
	if (!HudWidget || bSceneMenuOpen)
	{
		return;
	}

	GateCacheRefreshTimer -= DeltaSeconds;
	if (CachedGates.Num() == 0 && GateCacheRefreshTimer <= 0.0f)
	{
		RefreshGateCache();
	}

	const UWorld* World = GetWorld();
	const FString MapName = World ? World->GetMapName() : FString();
	const FButterflyRealmDescriptor& ActiveRealm = FButterflyTypography::FindRealmByMapOrScene(MapName);

	int32 FlightModeIndex = 0;
	if (const AButterflyPawn* ButterflyPawn = GetPawn<AButterflyPawn>())
	{
		if (ButterflyPawn->IsShowcaseOrbitActive())
		{
			FlightModeIndex = 2;
		}
		else if (ButterflyPawn->IsAccelerating())
		{
			FlightModeIndex = 1;
		}
	}

	if (!bHudInitialized || ActiveRealm.RealmIndex != LastRealmIndex || FlightModeIndex != LastFlightModeIndex)
	{
		LastRealmIndex = ActiveRealm.RealmIndex;
		LastFlightModeIndex = FlightModeIndex;

		const FText RealmTitle = FText::FromString(ActiveRealm.PlaqueTitle);
		FText ModeText = NSLOCTEXT("ButterflyDream", "ModeCruise", "巡游模式");
		if (FlightModeIndex == 2)
		{
			ModeText = NSLOCTEXT("ButterflyDream", "ModeOrbit", "『 环绕鉴赏视角 (P) 』");
		}
		else if (FlightModeIndex == 1)
		{
			ModeText = NSLOCTEXT("ButterflyDream", "ModeBoost", "『 流光疾掠 』");
		}
		HudWidget->UpdateRealmPlaque(RealmTitle, ModeText, FlightModeIndex);
	}

	if (SceneErrorDisplaySeconds > 0.0f)
	{
		SceneErrorDisplaySeconds = FMath::Max(0.0f, SceneErrorDisplaySeconds - DeltaSeconds);
		HudWidget->ShowSceneError(SceneErrorMessage);
		bHudInitialized = false;
		return;
	}

	const AButterflyDreamGateActor* BestGate = nullptr;
	EDreamGateState BestState = EDreamGateState::Idle;
	float BestCharge = 0.0f;
	float BestOpen = 0.0f;
	int32 BestRank = INDEX_NONE;
	auto StatusRank = [](EDreamGateState State)
	{
		switch (State)
		{
		case EDreamGateState::Loading: return 5;
		case EDreamGateState::Traversing: return 4;
		case EDreamGateState::Error: return 3;
		case EDreamGateState::Ready: return 2;
		case EDreamGateState::Opening: return 1;
		default: return 0;
		}
	};

	for (int32 Idx = CachedGates.Num() - 1; Idx >= 0; --Idx)
	{
		const AButterflyDreamGateActor* Gate = CachedGates[Idx].Get();
		if (!IsValid(Gate))
		{
			CachedGates.RemoveAtSwap(Idx);
			continue;
		}
		const EDreamGateState State = Gate->GetGateState();
		const bool bPersistentStatus = State == EDreamGateState::Traversing ||
			State == EDreamGateState::Loading || State == EDreamGateState::Error;
		if (!Gate->IsPlayerNearGate() && !bPersistentStatus)
		{
			continue;
		}
		const int32 Rank = StatusRank(State);
		if (!BestGate || Rank > BestRank || (Rank == BestRank && Gate->GetCharge() > BestCharge))
		{
			BestGate = Gate;
			BestState = State;
			BestCharge = Gate->GetCharge();
			BestOpen = Gate->GetCurrentOpenAlpha();
			BestRank = Rank;
		}
	}

	const bool bShowGate = BestGate != nullptr;
	const int32 ResonancePct = FMath::Clamp(FMath::RoundToInt(BestCharge * 100.0f), 0, 100);
	const int32 OpenPct = FMath::Clamp(FMath::RoundToInt(BestOpen * 100.0f), 0, 100);
	const int32 StateIndex = static_cast<int32>(BestState);
	const FString GateTitle = BestGate ? BestGate->GateTitle : FString();
	const FString GateFailure = BestGate ? BestGate->GetLastFailure() : FString();
	if (!bHudInitialized || bShowGate != bLastNearGate || ResonancePct != LastResonancePct ||
		OpenPct != LastOpenPct || StateIndex != LastGateStateIndex || GateTitle != LastGateTitle ||
		GateFailure != LastGateFailure)
	{
		bLastNearGate = bShowGate;
		LastResonancePct = ResonancePct;
		LastOpenPct = OpenPct;
		LastGateStateIndex = StateIndex;
		LastGateTitle = GateTitle;
		LastGateFailure = GateFailure;
		HudWidget->UpdateGateStatus(bShowGate, BestState, BestCharge, BestOpen, GateTitle, GateFailure);
	}

	bHudInitialized = true;
}

void AButterflyPlayerController::ToggleSceneMenu()
{
	if (bSceneMenuOpen)
	{
		CloseSceneMenu();
	}
	else
	{
		OpenSceneMenu();
	}
}

void AButterflyPlayerController::OpenSceneMenu()
{
	if (bSceneMenuOpen || !SceneMenu || IsSceneSwitchInProgress())
	{
		return;
	}

	bSceneMenuOpen = true;
	SetFlightInputEnabled(false);
	if (HudWidget)
	{
		HudWidget->SetVisibility(ESlateVisibility::Collapsed);
	}
	SceneMenu->SetVisibility(ESlateVisibility::Visible);
	bShowMouseCursor = true;

	FInputModeGameAndUI InputMode;
	InputMode.SetWidgetToFocus(SceneMenu->TakeWidget());
	InputMode.SetLockMouseToViewportBehavior(EMouseLockMode::DoNotLock);
	InputMode.SetHideCursorDuringCapture(false);
	SetInputMode(InputMode);
}

void AButterflyPlayerController::CloseSceneMenu()
{
	if (!bSceneMenuOpen || IsSceneSwitchInProgress())
	{
		return;
	}

	bSceneMenuOpen = false;
	if (SceneMenu)
	{
		SceneMenu->SetVisibility(ESlateVisibility::Collapsed);
	}
	if (HudWidget)
	{
		HudWidget->SetVisibility(ESlateVisibility::HitTestInvisible);
	}
	SetFlightInputEnabled(true);
	bShowMouseCursor = false;
	SetInputMode(FInputModeGameOnly());
}

void AButterflyPlayerController::SetFlightInputEnabled(bool bEnabled)
{
	if (bEnabled)
	{
		ResetIgnoreInputFlags();
	}
	else
	{
		SetIgnoreMoveInput(true);
		SetIgnoreLookInput(true);
	}

	if (AButterflyPawn* ButterflyPawn = GetPawn<AButterflyPawn>())
	{
		ButterflyPawn->ClearFlightInput();
	}
}

void AButterflyPlayerController::HandleSceneLoaded()
{
	bSceneMenuOpen = false;
	bHudInitialized = false;
	bLastNearGate = false;
	LastRealmIndex = -1;
	LastFlightModeIndex = -1;
	LastResonancePct = -1;
	LastOpenPct = -1;
	LastGateStateIndex = -1;
	LastGateTitle.Reset();
	LastGateFailure.Reset();
	SceneErrorMessage.Reset();
	SceneErrorDisplaySeconds = 0.0f;
	RefreshGateCache();

	if (SceneMenu)
	{
		SceneMenu->SetVisibility(ESlateVisibility::Collapsed);
	}
	if (HudWidget)
	{
		HudWidget->SetVisibility(ESlateVisibility::HitTestInvisible);
	}
	if (AButterflyPawn* ButterflyPawn = GetPawn<AButterflyPawn>())
	{
		ButterflyPawn->SetShowcaseOrbitActive(false);
	}
	SetFlightInputEnabled(true);
	bShowMouseCursor = false;
	SetInputMode(FInputModeGameOnly());
}

void AButterflyPlayerController::HandleSceneSwitchFailed(const FString& Failure)
{
	bSceneMenuOpen = false;
	if (SceneMenu)
	{
		SceneMenu->SetVisibility(ESlateVisibility::Collapsed);
	}
	if (HudWidget)
	{
		HudWidget->SetVisibility(ESlateVisibility::HitTestInvisible);
	}
	SetFlightInputEnabled(true);
	bShowMouseCursor = false;
	SetInputMode(FInputModeGameOnly());
	SceneErrorMessage = Failure;
	SceneErrorDisplaySeconds = 8.0f;
	bHudInitialized = false;
}

bool AButterflyPlayerController::IsSceneSwitchInProgress() const
{
	const UWorld* World = GetWorld();
	const UGameInstance* GameInstance = World ? World->GetGameInstance() : nullptr;
	const UButterflySceneSubsystem* SceneSubsystem = GameInstance
		? GameInstance->GetSubsystem<UButterflySceneSubsystem>()
		: nullptr;
	return SceneSubsystem && SceneSubsystem->IsSceneSwitchInProgress();
}
