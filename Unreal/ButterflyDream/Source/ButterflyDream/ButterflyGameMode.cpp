#include "ButterflyGameMode.h"

#include "ButterflyPawn.h"
#include "ButterflyPlayerController.h"
#include "Engine/World.h"
#include "GameFramework/Controller.h"
#include "GameFramework/Pawn.h"

AButterflyGameMode::AButterflyGameMode()
{
	DefaultPawnClass = AButterflyPawn::StaticClass();
	PlayerControllerClass = AButterflyPlayerController::StaticClass();
}

APawn* AButterflyGameMode::SpawnDefaultPawnAtTransform_Implementation(AController* NewPlayer, const FTransform& SpawnTransform)
{
	UWorld* World = GetWorld();
	UClass* PawnClass = GetDefaultPawnClassForController(NewPlayer);
	if (!World || !PawnClass)
	{
		return nullptr;
	}

	FActorSpawnParameters SpawnInfo;
	SpawnInfo.Instigator = GetInstigator();
	SpawnInfo.ObjectFlags |= RF_Transient;
	SpawnInfo.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AdjustIfPossibleButAlwaysSpawn;

	APawn* ResultPawn = World->SpawnActor<APawn>(PawnClass, SpawnTransform, SpawnInfo);
	if (!ResultPawn)
	{
		UE_LOG(LogTemp, Warning, TEXT("LUX_SPAWN Failed to spawn %s at %s"), *GetNameSafe(PawnClass), *SpawnTransform.ToHumanReadableString());
	}
	return ResultPawn;
}

void AButterflyGameMode::FinishRestartPlayer(AController* NewPlayer, const FRotator& StartRotation)
{
	Super::FinishRestartPlayer(NewPlayer, StartRotation);

	if (NewPlayer)
	{
		const APawn* SpawnedPawn = NewPlayer->GetPawn();
		const FVector PawnLoc = SpawnedPawn ? SpawnedPawn->GetActorLocation() : FVector::ZeroVector;
		const FRotator CtrlRot = NewPlayer->GetControlRotation();
		const UWorld* World = GetWorld();
		UE_LOG(
			LogTemp,
			Display,
			TEXT("LUX_SPAWN Map=%s PawnLoc=(%.1f,%.1f,%.1f) CtrlRot=(%.1f,%.1f,%.1f)"),
			World ? *World->GetMapName() : TEXT("Unknown"),
			PawnLoc.X, PawnLoc.Y, PawnLoc.Z,
			CtrlRot.Pitch, CtrlRot.Yaw, CtrlRot.Roll);
	}
}
