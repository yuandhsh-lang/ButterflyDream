#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "FourRealmNiagaraEditorBridge.generated.h"

class UStaticMesh;

UCLASS()
class BUTTERFLYDREAM_API UFourRealmNiagaraEditorBridge : public UBlueprintFunctionLibrary
{
	GENERATED_BODY()

public:
	UFUNCTION(BlueprintCallable, Category = "FourRealm|Niagara", meta = (CallInEditor))
	static bool CreateWingRibbonSystem(const FString& ReportPath);

	UFUNCTION(BlueprintCallable, Category = "FourRealm|Niagara", meta = (CallInEditor))
	static bool CreateGateMeshSwarmSystem(UStaticMesh* TargetMesh, UStaticMesh* RenderMesh, const FString& ReportPath);
};
