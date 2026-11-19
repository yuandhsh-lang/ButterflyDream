#include "ButterflyHudWidget.h"

#include "Blueprint/WidgetTree.h"
#include "ButterflyTypography.h"
#include "Components/Border.h"
#include "Components/Overlay.h"
#include "Components/OverlaySlot.h"
#include "Components/ProgressBar.h"
#include "Components/SizeBox.h"
#include "Components/TextBlock.h"
#include "Components/VerticalBox.h"
#include "Components/VerticalBoxSlot.h"
#include "Styling/SlateBrush.h"
#include "Styling/SlateColor.h"
#include "Styling/SlateTypes.h"

namespace ButterflyHudStyle
{
	static FSlateBrush MakePlaqueBrush(const FLinearColor& Fill, const FLinearColor& GoldTrim, float Radius, float OutlineWidth)
	{
		FSlateBrush Brush;
		Brush.DrawAs = ESlateBrushDrawType::RoundedBox;
		Brush.TintColor = FSlateColor(Fill);
		Brush.OutlineSettings = FSlateBrushOutlineSettings(Radius, FSlateColor(GoldTrim), OutlineWidth);
		return Brush;
	}

	static void ConfigureLabelFont(
		UTextBlock* Label,
		bool bUseBrushCalligraphy,
		float Size,
		int32 LetterSpacing,
		const FLinearColor& Color)
	{
		if (!Label)
		{
			return;
		}
		Label->SetFont(bUseBrushCalligraphy
			? FButterflyTypography::MakeBrushFont(Size, LetterSpacing, 2)
			: FButterflyTypography::MakeClassicalFont(Size, LetterSpacing, 1));
		Label->SetColorAndOpacity(FSlateColor(Color));
		Label->SetShadowOffset(FVector2D(0.0f, 1.5f));
		Label->SetShadowColorAndOpacity(FLinearColor(0.0f, 0.0f, 0.0f, 0.78f));
	}
}

TSharedRef<SWidget> UButterflyHudWidget::RebuildWidget()
{
	EnsureWidgetTreeBuilt();
	return Super::RebuildWidget();
}

void UButterflyHudWidget::EnsureWidgetTreeBuilt()
{
	if (!WidgetTree || WidgetTree->RootWidget)
	{
		return;
	}

	UOverlay* Root = WidgetTree->ConstructWidget<UOverlay>(UOverlay::StaticClass(), TEXT("HudRoot"));
	WidgetTree->RootWidget = Root;

	// 1. Top-Center Poetic Realm Plaque (Imperial Gold-on-Obsidian Pill with MaShanZheng Calligraphy)
	TopPlaqueBorder = WidgetTree->ConstructWidget<UBorder>(UBorder::StaticClass(), TEXT("TopPlaqueBorder"));
	UVerticalBox* TopBox = WidgetTree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass(), TEXT("TopPlaqueBox"));
	RealmTitleLabel = WidgetTree->ConstructWidget<UTextBlock>(UTextBlock::StaticClass(), TEXT("RealmTitleLabel"));
	FlightModeLabel = WidgetTree->ConstructWidget<UTextBlock>(UTextBlock::StaticClass(), TEXT("FlightModeLabel"));

	if (UOverlaySlot* TopSlot = Root->AddChildToOverlay(TopPlaqueBorder))
	{
		TopSlot->SetHorizontalAlignment(HAlign_Center);
		TopSlot->SetVerticalAlignment(VAlign_Top);
		TopSlot->SetPadding(FMargin(16.0f, 12.0f, 16.0f, 0.0f));
	}

	TopPlaqueBorder->SetBrushColor(FLinearColor::White);
	TopPlaqueBorder->SetBrush(ButterflyHudStyle::MakePlaqueBrush(
		FLinearColor(0.010f, 0.016f, 0.030f, 0.74f),
		FLinearColor(0.90f, 0.73f, 0.38f, 0.68f),
		16.0f,
		1.35f));
	TopPlaqueBorder->SetPadding(FMargin(26.0f, 7.0f));
	TopPlaqueBorder->SetContent(TopBox);

	ButterflyHudStyle::ConfigureLabelFont(
		RealmTitleLabel, true, 15.0f, 80, FLinearColor(0.99f, 0.88f, 0.56f, 0.99f));
	RealmTitleLabel->SetJustification(ETextJustify::Center);
	RealmTitleLabel->SetText(FText::FromString(TEXT("「庄周梦蝶 — 星海幻境」")));

	ButterflyHudStyle::ConfigureLabelFont(
		FlightModeLabel, false, 10.5f, 65, FLinearColor(0.76f, 0.88f, 0.95f, 0.92f));
	FlightModeLabel->SetJustification(ETextJustify::Center);
	FlightModeLabel->SetText(NSLOCTEXT("ButterflyDream", "ModeCruise", "巡游模式"));

	if (UVerticalBoxSlot* TitleSlot = TopBox->AddChildToVerticalBox(RealmTitleLabel))
	{
		TitleSlot->SetHorizontalAlignment(HAlign_Center);
		TitleSlot->SetPadding(FMargin(0.0f, 0.0f, 0.0f, 2.0f));
	}
	if (UVerticalBoxSlot* ModeSlot = TopBox->AddChildToVerticalBox(FlightModeLabel))
	{
		ModeSlot->SetHorizontalAlignment(HAlign_Center);
	}

	// 2. Small transient HUD caption; no world-space scroll is spawned.
	VerseEchoBorder = WidgetTree->ConstructWidget<UBorder>(UBorder::StaticClass(), TEXT("VerseEchoBorder"));
	UVerticalBox* EchoBox = WidgetTree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass(), TEXT("VerseEchoBox"));
	VerseEchoMainLabel = WidgetTree->ConstructWidget<UTextBlock>(UTextBlock::StaticClass(), TEXT("VerseEchoMainLabel"));
	VerseEchoNoteLabel = WidgetTree->ConstructWidget<UTextBlock>(UTextBlock::StaticClass(), TEXT("VerseEchoNoteLabel"));

	if (UOverlaySlot* EchoSlot = Root->AddChildToOverlay(VerseEchoBorder))
	{
		EchoSlot->SetHorizontalAlignment(HAlign_Center);
		EchoSlot->SetVerticalAlignment(VAlign_Bottom);
		EchoSlot->SetPadding(FMargin(24.0f, 0.0f, 24.0f, 68.0f));
	}

	VerseEchoBorder->SetBrushColor(FLinearColor::White);
	VerseEchoBorder->SetBrush(ButterflyHudStyle::MakePlaqueBrush(
		FLinearColor(0.008f, 0.014f, 0.028f, 0.50f),
		FLinearColor(0.95f, 0.80f, 0.44f, 0.54f),
		14.0f,
		1.15f));
	VerseEchoBorder->SetPadding(FMargin(24.0f, 6.0f));
	VerseEchoBorder->SetContent(EchoBox);
	VerseEchoBorder->SetRenderOpacity(0.0f);
	VerseEchoBorder->SetVisibility(ESlateVisibility::Collapsed);

	ButterflyHudStyle::ConfigureLabelFont(
		VerseEchoMainLabel, true, 16.5f, 80, FLinearColor(1.0f, 0.89f, 0.54f, 1.0f));
	VerseEchoMainLabel->SetJustification(ETextJustify::Center);

	ButterflyHudStyle::ConfigureLabelFont(
		VerseEchoNoteLabel, false, 10.0f, 45, FLinearColor(0.84f, 0.91f, 0.97f, 0.90f));
	VerseEchoNoteLabel->SetJustification(ETextJustify::Center);

	if (UVerticalBoxSlot* EchoMainSlot = EchoBox->AddChildToVerticalBox(VerseEchoMainLabel))
	{
		EchoMainSlot->SetHorizontalAlignment(HAlign_Center);
		EchoMainSlot->SetPadding(FMargin(0.0f, 0.0f, 0.0f, 2.0f));
	}
	if (UVerticalBoxSlot* EchoNoteSlot = EchoBox->AddChildToVerticalBox(VerseEchoNoteLabel))
	{
		EchoNoteSlot->SetHorizontalAlignment(HAlign_Center);
	}

	// 3. Bottom Translucent Control & Dream Gate Resonance Bar
	BottomBarBorder = WidgetTree->ConstructWidget<UBorder>(UBorder::StaticClass(), TEXT("BottomBarBorder"));
	UVerticalBox* BottomBox = WidgetTree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass(), TEXT("BottomBarBox"));
	HintLabel = WidgetTree->ConstructWidget<UTextBlock>(UTextBlock::StaticClass(), TEXT("HudHintLabel"));
	ResonanceBarBox = WidgetTree->ConstructWidget<USizeBox>(USizeBox::StaticClass(), TEXT("ResonanceBarBox"));
	ResonanceProgressBar = WidgetTree->ConstructWidget<UProgressBar>(UProgressBar::StaticClass(), TEXT("ResonanceProgressBar"));

	if (UOverlaySlot* BottomSlot = Root->AddChildToOverlay(BottomBarBorder))
	{
		BottomSlot->SetHorizontalAlignment(HAlign_Center);
		BottomSlot->SetVerticalAlignment(VAlign_Bottom);
		BottomSlot->SetPadding(FMargin(16.0f, 0.0f, 16.0f, 16.0f));
	}

	BottomBarBorder->SetBrushColor(FLinearColor::White);
	BottomBarBorder->SetBrush(ButterflyHudStyle::MakePlaqueBrush(
		FLinearColor(0.010f, 0.016f, 0.030f, 0.68f),
		FLinearColor(0.84f, 0.67f, 0.36f, 0.50f),
		14.0f,
		1.15f));
	BottomBarBorder->SetPadding(FMargin(24.0f, 7.5f));
	BottomBarBorder->SetContent(BottomBox);

	ButterflyHudStyle::ConfigureLabelFont(
		HintLabel, false, 11.0f, 45, FLinearColor(0.94f, 0.91f, 0.84f, 0.94f));
	HintLabel->SetJustification(ETextJustify::Center);
	HintLabel->SetText(NSLOCTEXT(
		"ButterflyDream",
		"HudDefaultControls",
		"WASD 御风 ｜ Space/C 升降 ｜ Shift 加速/近门蓄能 ｜ P 环绕 ｜ R 安全恢复 ｜ Tab 四境罗盘"));

	if (UVerticalBoxSlot* HintSlot = BottomBox->AddChildToVerticalBox(HintLabel))
	{
		HintSlot->SetHorizontalAlignment(HAlign_Center);
	}

	ResonanceBarBox->SetWidthOverride(380.0f);
	ResonanceBarBox->SetHeightOverride(5.0f);
	ResonanceBarBox->SetVisibility(ESlateVisibility::Collapsed);
	ResonanceBarBox->SetContent(ResonanceProgressBar);

	FProgressBarStyle BarStyle;
	BarStyle.BackgroundImage = ButterflyHudStyle::MakePlaqueBrush(
		FLinearColor(0.02f, 0.04f, 0.08f, 0.85f),
		FLinearColor(0.85f, 0.70f, 0.38f, 0.40f),
		2.5f,
		0.75f);
	BarStyle.FillImage = ButterflyHudStyle::MakePlaqueBrush(
		FLinearColor::White,
		FLinearColor::Transparent,
		2.5f,
		0.0f);
	ResonanceProgressBar->SetWidgetStyle(BarStyle);
	ResonanceProgressBar->SetFillColorAndOpacity(FLinearColor(0.48f, 0.92f, 1.0f, 0.96f));
	ResonanceProgressBar->SetPercent(0.0f);

	if (UVerticalBoxSlot* BarSlot = BottomBox->AddChildToVerticalBox(ResonanceBarBox))
	{
		BarSlot->SetHorizontalAlignment(HAlign_Center);
		BarSlot->SetPadding(FMargin(0.0f, 5.0f, 0.0f, 1.0f));
	}
}

void UButterflyHudWidget::NativeTick(const FGeometry& MyGeometry, float InDeltaTime)
{
	Super::NativeTick(MyGeometry, InDeltaTime);

	if (!bEchoActive || !VerseEchoBorder)
	{
		return;
	}

	EchoElapsed += InDeltaTime;
	if (EchoElapsed >= EchoTotalDuration)
	{
		bEchoActive = false;
		VerseEchoBorder->SetRenderOpacity(0.0f);
		VerseEchoBorder->SetVisibility(ESlateVisibility::Collapsed);
		return;
	}

	const float FadeInSec = 0.65f;
	const float FadeOutSec = 0.95f;
	float Alpha = 1.0f;
	if (EchoElapsed < FadeInSec)
	{
		Alpha = FMath::SmoothStep(0.0f, 1.0f, EchoElapsed / FadeInSec);
	}
	else if (EchoElapsed > EchoTotalDuration - FadeOutSec)
	{
		const float Remaining = FMath::Max(0.0f, EchoTotalDuration - EchoElapsed);
		Alpha = FMath::SmoothStep(0.0f, 1.0f, Remaining / FadeOutSec);
	}

	VerseEchoBorder->SetRenderOpacity(Alpha);
}

void UButterflyHudWidget::ShowStoryVerseEcho(
	const FText& VerseText,
	const FText& NoteText,
	const FLinearColor& TintColor,
	float Duration)
{
	EnsureWidgetTreeBuilt();
	if (!VerseEchoBorder || !VerseEchoMainLabel || VerseText.IsEmpty())
	{
		return;
	}

	VerseEchoMainLabel->SetText(FText::FromString(FString::Printf(TEXT("「 %s 」"), *VerseText.ToString())));
	VerseEchoMainLabel->SetColorAndOpacity(FSlateColor(FLinearColor(
		FMath::Clamp(TintColor.R, 0.55f, 1.0f),
		FMath::Clamp(TintColor.G, 0.55f, 1.0f),
		FMath::Clamp(TintColor.B, 0.45f, 1.0f),
		1.0f)));

	if (VerseEchoNoteLabel)
	{
		if (NoteText.IsEmpty())
		{
			VerseEchoNoteLabel->SetVisibility(ESlateVisibility::Collapsed);
		}
		else
		{
			VerseEchoNoteLabel->SetVisibility(ESlateVisibility::HitTestInvisible);
			VerseEchoNoteLabel->SetText(FText::FromString(FString::Printf(TEXT("— %s —"), *NoteText.ToString())));
		}
	}

	VerseEchoBorder->SetBrush(ButterflyHudStyle::MakePlaqueBrush(
		FLinearColor(0.008f, 0.014f, 0.028f, 0.56f),
		FLinearColor(TintColor.R, TintColor.G, TintColor.B, 0.62f),
		14.0f,
		1.2f));
	VerseEchoBorder->SetVisibility(ESlateVisibility::HitTestInvisible);
	VerseEchoBorder->SetRenderOpacity(0.0f);

	EchoElapsed = 0.0f;
	EchoTotalDuration = FMath::Clamp(Duration, 2.2f, 4.0f);
	bEchoActive = true;
}

void UButterflyHudWidget::SetHintText(const FText& NewText)
{
	if (HintLabel)
	{
		HintLabel->SetText(NewText);
	}
}

void UButterflyHudWidget::UpdateRealmPlaque(const FText& RealmTitle, const FText& FlightModeText, int32 FlightStyleIndex)
{
	if (RealmTitleLabel)
	{
		RealmTitleLabel->SetText(RealmTitle);
	}
	if (FlightModeLabel)
	{
		FlightModeLabel->SetText(FlightModeText);
		if (FlightStyleIndex == 2)
		{
			FlightModeLabel->SetColorAndOpacity(FSlateColor(FLinearColor(0.54f, 0.95f, 1.0f, 1.0f)));
		}
		else if (FlightStyleIndex == 1)
		{
			FlightModeLabel->SetColorAndOpacity(FSlateColor(FLinearColor(1.0f, 0.86f, 0.44f, 1.0f)));
		}
		else
		{
			FlightModeLabel->SetColorAndOpacity(FSlateColor(FLinearColor(0.76f, 0.88f, 0.95f, 0.92f)));
		}
	}
}

void UButterflyHudWidget::UpdateGateStatus(
	bool bShowGate,
	EDreamGateState State,
	float Charge,
	float OpenAlpha,
	const FString& GateTitle,
	const FString& Failure)
{
	if (!BottomBarBorder || !HintLabel || !ResonanceBarBox || !ResonanceProgressBar)
	{
		return;
	}

	if (!bShowGate)
	{
		BottomBarBorder->SetBrush(ButterflyHudStyle::MakePlaqueBrush(
			FLinearColor(0.010f, 0.016f, 0.030f, 0.68f),
			FLinearColor(0.84f, 0.67f, 0.36f, 0.50f),
			14.0f,
			1.15f));
		ButterflyHudStyle::ConfigureLabelFont(
			HintLabel, true, 11.5f, 40, FLinearColor(0.94f, 0.91f, 0.84f, 0.94f));
		HintLabel->SetText(NSLOCTEXT(
			"ButterflyDream",
			"HudDefaultControls",
			"WASD 御风 ｜ Space/C 升降 ｜ Shift 加速/近门蓄能 ｜ P 环绕 ｜ R 安全恢复 ｜ Tab 四境罗盘"));
		ResonanceBarBox->SetVisibility(ESlateVisibility::Collapsed);
		return;
	}

	const int32 ChargePct = FMath::Clamp(FMath::RoundToInt(Charge * 100.0f), 0, 100);
	const int32 OpenPct = FMath::Clamp(FMath::RoundToInt(OpenAlpha * 100.0f), 0, 100);
	const FString TitlePrefix = GateTitle.IsEmpty() ? FString() : FString::Printf(TEXT("【%s】 "), *GateTitle);
	FString StatusLine;
	FLinearColor Accent(0.48f, 0.90f, 1.0f, 0.96f);
	switch (State)
	{
	case EDreamGateState::Resonating:
	case EDreamGateState::Idle:
		StatusLine = FString::Printf(TEXT("『 %s按住 Shift 持续共鸣 %d%% — 松开或离开会衰减 』"), *TitlePrefix, ChargePct);
		break;
	case EDreamGateState::Opening:
		StatusLine = FString::Printf(TEXT("『 %s共鸣已满 — 仙门开启 %d%%，等待中心净空 』"), *TitlePrefix, OpenPct);
		Accent = FLinearColor(0.64f, 0.76f, 1.0f, 0.96f);
		break;
	case EDreamGateState::Ready:
		StatusLine = FString::Printf(TEXT("『 %s仙门已开 — 对准孔洞向前飞入，并飞越十环隧道 』"), *TitlePrefix);
		Accent = FLinearColor(1.0f, 0.84f, 0.40f, 1.0f);
		break;
	case EDreamGateState::Traversing:
		StatusLine = FString::Printf(TEXT("『 %s隧道穿越中 — 保持前向，实际越过出口才会转场 』"), *TitlePrefix);
		Accent = FLinearColor(0.56f, 0.95f, 0.88f, 1.0f);
		break;
	case EDreamGateState::Loading:
		StatusLine = FString::Printf(TEXT("『 %s已越过隧道出口 — 正在预载并前往目标幻境 』"), *TitlePrefix);
		Accent = FLinearColor(0.78f, 0.68f, 1.0f, 1.0f);
		break;
	case EDreamGateState::Error:
		StatusLine = FString::Printf(TEXT("『 门链暂不可用：%s — 退回门后或按 R 安全恢复后重试 』"), *Failure);
		Accent = FLinearColor(1.0f, 0.38f, 0.30f, 1.0f);
		break;
	default:
		StatusLine = TEXT("『 门链状态未知 — 请按 R 安全恢复 』");
		Accent = FLinearColor(1.0f, 0.38f, 0.30f, 1.0f);
		break;
	}

	BottomBarBorder->SetBrush(ButterflyHudStyle::MakePlaqueBrush(
		FLinearColor(0.012f, 0.024f, 0.045f, 0.84f), Accent, 14.0f, 1.5f));
	ButterflyHudStyle::ConfigureLabelFont(HintLabel, true, 11.5f, 35, Accent);
	HintLabel->SetText(FText::FromString(StatusLine));
	ResonanceBarBox->SetVisibility(ESlateVisibility::HitTestInvisible);
	const float BarAlpha = State == EDreamGateState::Opening
		? FMath::Clamp(OpenAlpha, 0.0f, 1.0f)
		: (State == EDreamGateState::Traversing || State == EDreamGateState::Loading
			? 1.0f
			: FMath::Clamp(Charge, 0.0f, 1.0f));
	ResonanceProgressBar->SetPercent(BarAlpha);
	ResonanceProgressBar->SetFillColorAndOpacity(Accent);
}

void UButterflyHudWidget::ShowSceneError(const FString& Failure)
{
	UpdateGateStatus(true, EDreamGateState::Error, 0.0f, 0.0f, FString(), Failure);
}
