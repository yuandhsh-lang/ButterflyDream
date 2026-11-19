#include "ButterflySceneSubsystem.h"

#include "ButterflyDreamGateActor.h"
#include "ButterflyPawn.h"
#include "ButterflyPlayerController.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/CoreDelegates.h"
#include "Misc/PackageName.h"

void UButterflySceneSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
	Super::Initialize(Collection);
	FCoreUObjectDelegates::PostLoadMapWithWorld.AddUObject(this, &UButterflySceneSubsystem::HandlePostLoadMap);
	if (GEngine)
	{
		GEngine->OnTravelFailure().AddUObject(this, &UButterflySceneSubsystem::HandleTravelFailure);
	}
}

void UButterflySceneSubsystem::Deinitialize()
{
	FCoreUObjectDelegates::PostLoadMapWithWorld.RemoveAll(this);
	if (GEngine)
	{
		GEngine->OnTravelFailure().RemoveAll(this);
	}
	if (UGameInstance* GameInstance = GetGameInstance())
	{
		GameInstance->GetTimerManager().ClearTimer(SceneSwitchTimeoutHandle);
	}
	Super::Deinitialize();
}

bool UButterflySceneSubsystem::RequestSceneSwitch(const FString& MapPackageName, FString& OutStatus)
{
	if (bSceneSwitchInProgress)
	{
		OutStatus = TEXT("已有幻境正在加载，请稍候。");
		return false;
	}
	if (MapPackageName.IsEmpty() || !FPackageName::DoesPackageExist(MapPackageName))
	{
		LastStatus = FString::Printf(TEXT("目标幻境不存在：%s"), *MapPackageName);
		OutStatus = LastStatus;
		return false;
	}

	UGameInstance* GameInstance = GetGameInstance();
	UWorld* World = GameInstance ? GameInstance->GetWorld() : nullptr;
	if (!GameInstance || !World)
	{
		LastStatus = TEXT("当前无法切换幻境：游戏世界尚未就绪。");
		OutStatus = LastStatus;
		return false;
	}
	if (World->IsPaused())
	{
		UGameplayStatics::SetGamePaused(World, false);
	}
	if (APlayerController* PlayerController = GameInstance->GetFirstLocalPlayerController())
	{
		if (AButterflyPlayerController* ButterflyController = Cast<AButterflyPlayerController>(PlayerController))
		{
			ButterflyController->SetFlightInputEnabled(false);
		}
		else
		{
			PlayerController->SetIgnoreMoveInput(true);
			PlayerController->SetIgnoreLookInput(true);
		}
	}

	bSceneSwitchInProgress = true;
	PendingMapPackageName = MapPackageName;
	LastStatus = FString::Printf(TEXT("正在加载幻境：%s"), *MapPackageName);
	OutStatus = LastStatus;
	GameInstance->GetTimerManager().SetTimer(
		SceneSwitchTimeoutHandle,
		this,
		&UButterflySceneSubsystem::HandleSceneSwitchTimeout,
		SceneSwitchTimeoutSeconds,
		false);
	LoadPackageAsync(
		MapPackageName,
		FLoadPackageAsyncDelegate::CreateUObject(this, &UButterflySceneSubsystem::HandlePackageLoaded));
	return true;
}

void UButterflySceneSubsystem::HandlePackageLoaded(
	const FName& PackageName,
	UPackage* LoadedPackage,
	EAsyncLoadingResult::Type Result)
{
	if (!bSceneSwitchInProgress || PackageName.ToString() != PendingMapPackageName)
	{
		return;
	}
	if (Result != EAsyncLoadingResult::Succeeded || !LoadedPackage)
	{
		FailSceneSwitch(FString::Printf(TEXT("幻境资源加载失败：%s"), *PackageName.ToString()));
		return;
	}

	UGameInstance* GameInstance = GetGameInstance();
	if (!GameInstance)
	{
		FailSceneSwitch(TEXT("加载完成时游戏实例已经不存在。"));
		return;
	}
	LastStatus = FString::Printf(TEXT("资源已就绪，正在进入：%s"), *PendingMapPackageName);
	UGameplayStatics::OpenLevel(GameInstance, FName(*PendingMapPackageName), true);
}

void UButterflySceneSubsystem::HandlePostLoadMap(UWorld* LoadedWorld)
{
	UGameInstance* GameInstance = GetGameInstance();
	if (!LoadedWorld || !GameInstance || LoadedWorld->GetGameInstance() != GameInstance)
	{
		return;
	}
	GameInstance->GetTimerManager().ClearTimer(SceneSwitchTimeoutHandle);
	bSceneSwitchInProgress = false;
	PendingMapPackageName.Reset();
	LastStatus = FString::Printf(TEXT("已进入 %s。"), *LoadedWorld->GetMapName());

	APlayerController* PlayerController = GameInstance->GetFirstLocalPlayerController(LoadedWorld);
	if (AButterflyPlayerController* ButterflyController = Cast<AButterflyPlayerController>(PlayerController))
	{
		ButterflyController->HandleSceneLoaded();
	}
	else if (PlayerController)
	{
		PlayerController->ResetIgnoreInputFlags();
		PlayerController->bShowMouseCursor = false;
		PlayerController->SetInputMode(FInputModeGameOnly());
	}
}

void UButterflySceneSubsystem::HandleTravelFailure(
	UWorld* FailedWorld,
	ETravelFailure::Type FailureType,
	const FString& ErrorString)
{
	if (!bSceneSwitchInProgress)
	{
		return;
	}
	FailSceneSwitch(FString::Printf(
		TEXT("进入幻境失败（%s）：%s"),
		ETravelFailure::ToString(FailureType),
		*ErrorString));
}

void UButterflySceneSubsystem::HandleSceneSwitchTimeout()
{
	if (bSceneSwitchInProgress)
	{
		FailSceneSwitch(TEXT("幻境加载超时。已恢复原场景和安全点，请重试。"));
	}
}

void UButterflySceneSubsystem::FailSceneSwitch(const FString& Reason)
{
	UGameInstance* GameInstance = GetGameInstance();
	if (GameInstance)
	{
		GameInstance->GetTimerManager().ClearTimer(SceneSwitchTimeoutHandle);
	}
	bSceneSwitchInProgress = false;
	PendingMapPackageName.Reset();
	LastStatus = Reason;

	UWorld* World = GameInstance ? GameInstance->GetWorld() : nullptr;
	if (World)
	{
		TArray<AActor*> Gates;
		UGameplayStatics::GetAllActorsOfClass(World, AButterflyDreamGateActor::StaticClass(), Gates);
		for (AActor* Actor : Gates)
		{
			if (AButterflyDreamGateActor* Gate = Cast<AButterflyDreamGateActor>(Actor))
			{
				Gate->HandleSceneSwitchFailure(Reason);
			}
		}
		if (AButterflyPawn* Pawn = Cast<AButterflyPawn>(UGameplayStatics::GetPlayerPawn(World, 0)))
		{
			Pawn->RecoverToSafePoint();
		}
	}
	if (GameInstance)
	{
		if (AButterflyPlayerController* ButterflyController = Cast<AButterflyPlayerController>(
			GameInstance->GetFirstLocalPlayerController()))
		{
			ButterflyController->HandleSceneSwitchFailed(Reason);
		}
		else if (APlayerController* PlayerController = GameInstance->GetFirstLocalPlayerController())
		{
			PlayerController->ResetIgnoreInputFlags();
		}
	}
	UE_LOG(LogTemp, Warning, TEXT("LUX_SCENE_FAILURE %s"), *Reason);
}
