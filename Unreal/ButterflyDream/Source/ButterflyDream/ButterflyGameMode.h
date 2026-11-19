#pragma once

#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "ButterflyGameMode.generated.h"

UCLASS()
class BUTTERFLYDREAM_API AButterflyGameMode : public AGameModeBase
{
	GENERATED_BODY()

public:
	AButterflyGameMode();

	virtual APawn* SpawnDefaultPawnAtTransform_Implementation(AController* NewPlayer, const FTransform& SpawnTransform) override;
	virtual void FinishRestartPlayer(AController* NewPlayer, const FRotator& StartRotation) override;
};
