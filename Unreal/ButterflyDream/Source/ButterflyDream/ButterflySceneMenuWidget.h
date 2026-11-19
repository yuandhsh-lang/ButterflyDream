#pragma once

#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "ButterflySceneMenuWidget.generated.h"

class UButton;
class UScrollBox;
class UTextBlock;
class UVerticalBox;

UCLASS()
class BUTTERFLYDREAM_API UButterflySceneMenuWidget : public UUserWidget
{
	GENERATED_BODY()

protected:
	virtual TSharedRef<SWidget> RebuildWidget() override;

private:
	void EnsureWidgetTreeBuilt();
	UPROPERTY(Transient)
	TObjectPtr<UTextBlock> StatusText;

	UTextBlock* AddStyledText(
		UVerticalBox* Parent,
		FName WidgetName,
		const FText& Content,
		bool bUseBrushFont,
		float FontSize,
		int32 LetterSpacing,
		const FLinearColor& Color,
		const FMargin& InSlotPadding);

	UButton* AddRealmCardButton(
		UScrollBox* ScrollParent,
		FName WidgetName,
		const FText& RealmHeader,
		const FText& PoeticDesc,
		const FLinearColor& AccentTrim);

	UButton* AddActionPillButton(
		UVerticalBox* Parent,
		FName WidgetName,
		const FText& Label);

	void RequestScene(const FString& MapPackageName);

	UFUNCTION()
	void HandleRealm1StarSeaClicked();

	UFUNCTION()
	void HandleRealm2InkCloudClicked();

	UFUNCTION()
	void HandleRealm3CrystalMirageClicked();

	UFUNCTION()
	void HandleRealm4TaijiAwakeningClicked();

	UFUNCTION()
	void HandleResumeClicked();

	UFUNCTION()
	void HandleRestartClicked();

	UFUNCTION()
	void HandleQuitClicked();
};
