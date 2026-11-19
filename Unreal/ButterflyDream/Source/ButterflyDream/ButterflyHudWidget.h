#pragma once

#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "DreamGateResonance.h"
#include "ButterflyHudWidget.generated.h"

class UBorder;
class UProgressBar;
class USizeBox;
class UTextBlock;

UCLASS()
class BUTTERFLYDREAM_API UButterflyHudWidget : public UUserWidget
{
	GENERATED_BODY()

public:
	void SetHintText(const FText& NewText);
	void UpdateRealmPlaque(const FText& RealmTitle, const FText& FlightModeText, int32 FlightStyleIndex);
	void UpdateGateStatus(
		bool bShowGate,
		EDreamGateState State,
		float Charge,
		float OpenAlpha,
		const FString& GateTitle,
		const FString& Failure);
	void ShowSceneError(const FString& Failure);

	UFUNCTION(BlueprintCallable, Category = "HUD")
	void ShowStoryVerseEcho(
		const FText& VerseText,
		const FText& NoteText,
		const FLinearColor& TintColor,
		float Duration = 6.5f);

protected:
	virtual TSharedRef<SWidget> RebuildWidget() override;
	virtual void NativeTick(const FGeometry& MyGeometry, float InDeltaTime) override;

private:
	void EnsureWidgetTreeBuilt();
	UPROPERTY(Transient)
	TObjectPtr<UBorder> TopPlaqueBorder;

	UPROPERTY(Transient)
	TObjectPtr<UTextBlock> RealmTitleLabel;

	UPROPERTY(Transient)
	TObjectPtr<UTextBlock> FlightModeLabel;

	UPROPERTY(Transient)
	TObjectPtr<UBorder> VerseEchoBorder;

	UPROPERTY(Transient)
	TObjectPtr<UTextBlock> VerseEchoMainLabel;

	UPROPERTY(Transient)
	TObjectPtr<UTextBlock> VerseEchoNoteLabel;

	UPROPERTY(Transient)
	TObjectPtr<UBorder> BottomBarBorder;

	UPROPERTY(Transient)
	TObjectPtr<UTextBlock> HintLabel;

	UPROPERTY(Transient)
	TObjectPtr<USizeBox> ResonanceBarBox;

	UPROPERTY(Transient)
	TObjectPtr<UProgressBar> ResonanceProgressBar;

	float EchoElapsed = 0.0f;
	float EchoTotalDuration = 0.0f;
	bool bEchoActive = false;
};
