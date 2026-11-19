#include "ButterflySceneMenuWidget.h"

#include "Blueprint/WidgetTree.h"
#include "ButterflyPlayerController.h"
#include "ButterflySceneSubsystem.h"
#include "ButterflyTypography.h"
#include "Components/Border.h"
#include "Components/Button.h"
#include "Components/Overlay.h"
#include "Components/OverlaySlot.h"
#include "Components/ScrollBox.h"
#include "Components/ScrollBoxSlot.h"
#include "Components/SizeBox.h"
#include "Components/TextBlock.h"
#include "Components/VerticalBox.h"
#include "Components/VerticalBoxSlot.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "Styling/SlateBrush.h"
#include "Styling/SlateColor.h"
#include "Styling/SlateTypes.h"

namespace ButterflyMenuStyle
{
	static FSlateBrush MakeRoundedBrush(const FLinearColor& Fill, const FLinearColor& Trim, float Radius, float OutlineWidth)
	{
		FSlateBrush Brush;
		Brush.DrawAs = ESlateBrushDrawType::RoundedBox;
		Brush.TintColor = FSlateColor(Fill);
		Brush.OutlineSettings = FSlateBrushOutlineSettings(Radius, FSlateColor(Trim), OutlineWidth);
		return Brush;
	}

	static FButtonStyle MakeXianxiaButtonStyle(const FLinearColor& AccentTrim, float Radius)
	{
		FButtonStyle Style;
		Style.Normal = MakeRoundedBrush(
			FLinearColor(0.018f, 0.028f, 0.052f, 0.90f),
			FLinearColor(AccentTrim.R, AccentTrim.G, AccentTrim.B, 0.58f),
			Radius,
			1.25f);
		Style.Hovered = MakeRoundedBrush(
			FLinearColor(0.045f, 0.068f, 0.115f, 0.96f),
			FLinearColor(1.0f, 0.88f, 0.52f, 0.98f),
			Radius,
			1.75f);
		Style.Pressed = MakeRoundedBrush(
			FLinearColor(0.085f, 0.068f, 0.032f, 0.98f),
			FLinearColor(1.0f, 0.92f, 0.65f, 1.0f),
			Radius,
			2.0f);
		Style.NormalPadding = FMargin(18.0f, 10.0f);
		Style.PressedPadding = FMargin(18.0f, 11.0f, 18.0f, 9.0f);
		return Style;
	}
}

TSharedRef<SWidget> UButterflySceneMenuWidget::RebuildWidget()
{
	EnsureWidgetTreeBuilt();
	return Super::RebuildWidget();
}

void UButterflySceneMenuWidget::EnsureWidgetTreeBuilt()
{
	if (!WidgetTree || WidgetTree->RootWidget)
	{
		return;
	}

	UOverlay* Root = WidgetTree->ConstructWidget<UOverlay>(UOverlay::StaticClass(), TEXT("SceneMenuRoot"));
	UBorder* BackdropDim = WidgetTree->ConstructWidget<UBorder>(UBorder::StaticClass(), TEXT("SceneMenuBackdrop"));
	USizeBox* CardWidthBox = WidgetTree->ConstructWidget<USizeBox>(USizeBox::StaticClass(), TEXT("SceneMenuWidthBox"));
	UBorder* ObsidianCard = WidgetTree->ConstructWidget<UBorder>(UBorder::StaticClass(), TEXT("SceneMenuCard"));
	UVerticalBox* Content = WidgetTree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass(), TEXT("SceneMenuContent"));
	UBorder* GoldDivider = WidgetTree->ConstructWidget<UBorder>(UBorder::StaticClass(), TEXT("SceneMenuDivider"));
	USizeBox* DividerSize = WidgetTree->ConstructWidget<USizeBox>(USizeBox::StaticClass(), TEXT("SceneMenuDividerSize"));
	USizeBox* ScrollHeightBox = WidgetTree->ConstructWidget<USizeBox>(USizeBox::StaticClass(), TEXT("RealmScrollHeightBox"));
	UScrollBox* RealmScrollBox = WidgetTree->ConstructWidget<UScrollBox>(UScrollBox::StaticClass(), TEXT("RealmScrollBox"));

	WidgetTree->RootWidget = Root;

	BackdropDim->SetBrushColor(FLinearColor(0.004f, 0.008f, 0.018f, 0.66f));
	if (UOverlaySlot* DimSlot = Root->AddChildToOverlay(BackdropDim))
	{
		DimSlot->SetHorizontalAlignment(HAlign_Fill);
		DimSlot->SetVerticalAlignment(VAlign_Fill);
	}

	CardWidthBox->SetWidthOverride(630.0f);
	CardWidthBox->SetContent(ObsidianCard);
	if (UOverlaySlot* CardSlot = Root->AddChildToOverlay(CardWidthBox))
	{
		CardSlot->SetHorizontalAlignment(HAlign_Center);
		CardSlot->SetVerticalAlignment(VAlign_Center);
	}

	ObsidianCard->SetBrushColor(FLinearColor::White);
	ObsidianCard->SetBrush(ButterflyMenuStyle::MakeRoundedBrush(
		FLinearColor(0.010f, 0.016f, 0.030f, 0.95f),
		FLinearColor(0.90f, 0.73f, 0.38f, 0.88f),
		18.0f,
		1.65f));
	ObsidianCard->SetPadding(FMargin(30.0f, 22.0f));
	ObsidianCard->SetContent(Content);

	AddStyledText(
		Content,
		TEXT("MenuOverline"),
		NSLOCTEXT("ButterflyDream", "MenuOverline", "『 ZHUANGZI FOUR-REALM COMPASS 』"),
		false,
		9.0f,
		115,
		FLinearColor(0.82f, 0.68f, 0.40f, 0.86f),
		FMargin(0.0f, 0.0f, 0.0f, 3.0f));

	AddStyledText(
		Content,
		TEXT("SceneMenuTitle"),
		NSLOCTEXT("ButterflyDream", "SceneMenuTitle", "「 庄周梦蝶 — 四境罗盘 」"),
		true,
		24.0f,
		95,
		FLinearColor(0.99f, 0.88f, 0.56f, 1.0f),
		FMargin(0.0f, 0.0f, 0.0f, 3.0f));

	AddStyledText(
		Content,
		TEXT("PoeticSubtitle"),
		NSLOCTEXT("ButterflyDream", "PoeticSubtitle", "历星海、水墨、琉璃、太极四重幻境；振翅共鸣，飞越真实隧道"),
		false,
		10.5f,
		45,
		FLinearColor(0.75f, 0.86f, 0.94f, 0.92f),
		FMargin(0.0f, 0.0f, 0.0f, 10.0f));

	DividerSize->SetHeightOverride(1.2f);
	GoldDivider->SetBrushColor(FLinearColor(0.88f, 0.71f, 0.38f, 0.42f));
	DividerSize->SetContent(GoldDivider);
	if (UVerticalBoxSlot* DivSlot = Content->AddChildToVerticalBox(DividerSize))
	{
		DivSlot->SetHorizontalAlignment(HAlign_Fill);
		DivSlot->SetPadding(FMargin(12.0f, 0.0f, 12.0f, 10.0f));
	}

	ScrollHeightBox->SetMaxDesiredHeight(280.0f);
	ScrollHeightBox->SetContent(RealmScrollBox);
	if (UVerticalBoxSlot* ScrollSlot = Content->AddChildToVerticalBox(ScrollHeightBox))
	{
		ScrollSlot->SetHorizontalAlignment(HAlign_Fill);
		ScrollSlot->SetPadding(FMargin(0.0f, 0.0f, 0.0f, 8.0f));
	}

	const TArray<FButterflyRealmDescriptor>& Realms = FButterflyTypography::GetAllRealms();
	TArray<UButton*> RealmButtons;
	for (int32 Idx = 0; Idx < Realms.Num(); ++Idx)
	{
		const FButterflyRealmDescriptor& Realm = Realms[Idx];
		UButton* RealmBtn = AddRealmCardButton(
			RealmScrollBox,
			FName(*FString::Printf(TEXT("RealmCardBtn_%d"), Idx + 1)),
			FText::FromString(Realm.CompassHeader),
			FText::FromString(Realm.CompassDesc),
			Realm.AccentColor);
		RealmButtons.Add(RealmBtn);
	}

	if (RealmButtons.IsValidIndex(0))
	{
		RealmButtons[0]->OnClicked.AddDynamic(this, &UButterflySceneMenuWidget::HandleRealm1StarSeaClicked);
	}
	if (RealmButtons.IsValidIndex(1))
	{
		RealmButtons[1]->OnClicked.AddDynamic(this, &UButterflySceneMenuWidget::HandleRealm2InkCloudClicked);
	}
	if (RealmButtons.IsValidIndex(2))
	{
		RealmButtons[2]->OnClicked.AddDynamic(this, &UButterflySceneMenuWidget::HandleRealm3CrystalMirageClicked);
	}
	if (RealmButtons.IsValidIndex(3))
	{
		RealmButtons[3]->OnClicked.AddDynamic(this, &UButterflySceneMenuWidget::HandleRealm4TaijiAwakeningClicked);
	}

	AddStyledText(
		Content,
		TEXT("FlightControls"),
		NSLOCTEXT(
			"ButterflyDream",
			"FlightControls",
			"WASD 御风 ｜ Space/C 升降 ｜ Shift 加速/共鸣 ｜ P 环绕 ｜ R 安全恢复"),
		false,
		10.0f,
		35,
		FLinearColor(0.86f, 0.84f, 0.78f, 0.88f),
		FMargin(0.0f, 6.0f, 0.0f, 8.0f));

	UButton* ResumeButton = AddActionPillButton(
		Content,
		TEXT("ResumeButton"),
		NSLOCTEXT("ButterflyDream", "Resume", "『 收起罗盘 — 继续御风飞行 (Tab / Esc) 』"));
	ResumeButton->OnClicked.AddDynamic(this, &UButterflySceneMenuWidget::HandleResumeClicked);

	UButton* RestartButton = AddActionPillButton(
		Content,
		TEXT("RestartButton"),
		NSLOCTEXT("ButterflyDream", "Restart", "『 重新开始当前幻境 』"));
	RestartButton->OnClicked.AddDynamic(this, &UButterflySceneMenuWidget::HandleRestartClicked);

	UButton* QuitButton = AddActionPillButton(
		Content,
		TEXT("QuitButton"),
		NSLOCTEXT("ButterflyDream", "Quit", "『 退出蝶梦 』"));
	QuitButton->OnClicked.AddDynamic(this, &UButterflySceneMenuWidget::HandleQuitClicked);

	StatusText = AddStyledText(
		Content,
		TEXT("SceneStatus"),
		NSLOCTEXT("ButterflyDream", "SceneStatusInitial", "罗盘可直接选境；仙门路线需蓄满共鸣并飞越整条隧道。"),
		false,
		10.0f,
		35,
		FLinearColor(0.68f, 0.88f, 0.96f, 0.88f),
		FMargin(0.0f, 8.0f, 0.0f, 0.0f));
}

UTextBlock* UButterflySceneMenuWidget::AddStyledText(
	UVerticalBox* Parent,
	FName WidgetName,
	const FText& Content,
	bool bUseBrushFont,
	float FontSize,
	int32 LetterSpacing,
	const FLinearColor& Color,
	const FMargin& InSlotPadding)
{
	UTextBlock* Text = WidgetTree->ConstructWidget<UTextBlock>(UTextBlock::StaticClass(), WidgetName);
	Text->SetFont(bUseBrushFont
		? FButterflyTypography::MakeBrushFont(FontSize, LetterSpacing, 2)
		: FButterflyTypography::MakeClassicalFont(FontSize, LetterSpacing, 1));
	Text->SetColorAndOpacity(FSlateColor(Color));
	Text->SetJustification(ETextJustify::Center);
	Text->SetShadowOffset(FVector2D(0.0f, 1.5f));
	Text->SetShadowColorAndOpacity(FLinearColor(0.0f, 0.0f, 0.0f, 0.80f));
	Text->SetText(Content);

	if (UVerticalBoxSlot* TextSlot = Parent->AddChildToVerticalBox(Text))
	{
		TextSlot->SetPadding(InSlotPadding);
		TextSlot->SetHorizontalAlignment(HAlign_Center);
	}
	return Text;
}

UButton* UButterflySceneMenuWidget::AddRealmCardButton(
	UScrollBox* ScrollParent,
	FName WidgetName,
	const FText& RealmHeader,
	const FText& PoeticDesc,
	const FLinearColor& AccentTrim)
{
	UButton* Button = WidgetTree->ConstructWidget<UButton>(UButton::StaticClass(), WidgetName);
	Button->SetStyle(ButterflyMenuStyle::MakeXianxiaButtonStyle(AccentTrim, 12.0f));

	UVerticalBox* CardBox = WidgetTree->ConstructWidget<UVerticalBox>(
		UVerticalBox::StaticClass(), FName(*(WidgetName.ToString() + TEXT("_Box"))));
	UTextBlock* HeaderText = WidgetTree->ConstructWidget<UTextBlock>(
		UTextBlock::StaticClass(), FName(*(WidgetName.ToString() + TEXT("_Header"))));
	UTextBlock* DescText = WidgetTree->ConstructWidget<UTextBlock>(
		UTextBlock::StaticClass(), FName(*(WidgetName.ToString() + TEXT("_Desc"))));

	HeaderText->SetFont(FButterflyTypography::MakeBrushFont(15.5f, 58, 2));
	HeaderText->SetColorAndOpacity(FSlateColor(FLinearColor(0.99f, 0.88f, 0.56f, 1.0f)));
	HeaderText->SetText(RealmHeader);

	DescText->SetFont(FButterflyTypography::MakeClassicalFont(10.0f, 26, 1));
	DescText->SetColorAndOpacity(FSlateColor(FLinearColor(0.84f, 0.89f, 0.96f, 0.92f)));
	DescText->SetAutoWrapText(true);
	DescText->SetText(PoeticDesc);

	if (UVerticalBoxSlot* HSlot = CardBox->AddChildToVerticalBox(HeaderText))
	{
		HSlot->SetPadding(FMargin(0.0f, 0.0f, 0.0f, 3.0f));
		HSlot->SetHorizontalAlignment(HAlign_Left);
	}
	if (UVerticalBoxSlot* DSlot = CardBox->AddChildToVerticalBox(DescText))
	{
		DSlot->SetHorizontalAlignment(HAlign_Left);
	}

	Button->SetContent(CardBox);
	if (UScrollBoxSlot* ScrollSlot = Cast<UScrollBoxSlot>(ScrollParent->AddChild(Button)))
	{
		ScrollSlot->SetPadding(FMargin(0.0f, 4.0f, 6.0f, 4.0f));
		ScrollSlot->SetHorizontalAlignment(HAlign_Fill);
	}
	return Button;
}

UButton* UButterflySceneMenuWidget::AddActionPillButton(
	UVerticalBox* Parent,
	FName WidgetName,
	const FText& Label)
{
	UButton* Button = WidgetTree->ConstructWidget<UButton>(UButton::StaticClass(), WidgetName);
	Button->SetStyle(ButterflyMenuStyle::MakeXianxiaButtonStyle(FLinearColor(0.90f, 0.74f, 0.38f, 1.0f), 14.0f));

	UTextBlock* ButtonText = WidgetTree->ConstructWidget<UTextBlock>(
		UTextBlock::StaticClass(), FName(*(WidgetName.ToString() + TEXT("Text"))));
	ButtonText->SetFont(FButterflyTypography::MakeClassicalFont(11.5f, 60, 1));
	ButtonText->SetColorAndOpacity(FSlateColor(FLinearColor(0.98f, 0.89f, 0.62f, 1.0f)));
	ButtonText->SetJustification(ETextJustify::Center);
	ButtonText->SetText(Label);

	Button->SetContent(ButtonText);
	if (UVerticalBoxSlot* ButtonSlot = Parent->AddChildToVerticalBox(Button))
	{
		ButtonSlot->SetPadding(FMargin(28.0f, 4.0f, 28.0f, 0.0f));
		ButtonSlot->SetHorizontalAlignment(HAlign_Fill);
	}
	return Button;
}

void UButterflySceneMenuWidget::RequestScene(const FString& MapPackageName)
{
	FString Status = TEXT("当前无法切换幻境。");
	APlayerController* OwningPlayer = GetOwningPlayer();
	UWorld* World = OwningPlayer ? OwningPlayer->GetWorld() : nullptr;
	UGameInstance* GameInstance = World ? World->GetGameInstance() : nullptr;
	if (UButterflySceneSubsystem* SceneSubsystem = GameInstance
		? GameInstance->GetSubsystem<UButterflySceneSubsystem>()
		: nullptr)
	{
		SceneSubsystem->RequestSceneSwitch(MapPackageName, Status);
	}

	if (StatusText)
	{
		StatusText->SetText(FText::FromString(Status));
	}
}

void UButterflySceneMenuWidget::HandleRealm1StarSeaClicked()
{
	RequestScene(TEXT("/Game/Maps/Lux_StarSeaDream"));
}

void UButterflySceneMenuWidget::HandleRealm2InkCloudClicked()
{
	RequestScene(TEXT("/Game/Maps/Lux_InkCloudDream"));
}

void UButterflySceneMenuWidget::HandleRealm3CrystalMirageClicked()
{
	RequestScene(TEXT("/Game/Maps/Lux_CrystalMirageDream"));
}

void UButterflySceneMenuWidget::HandleRealm4TaijiAwakeningClicked()
{
	RequestScene(TEXT("/Game/Maps/Lux_TaijiAwakeningDream"));
}

void UButterflySceneMenuWidget::HandleResumeClicked()
{
	if (AButterflyPlayerController* ButterflyController = GetOwningPlayer<AButterflyPlayerController>())
	{
		ButterflyController->CloseSceneMenu();
	}
}

void UButterflySceneMenuWidget::HandleRestartClicked()
{
	if (APlayerController* OwningPlayer = GetOwningPlayer())
	{
		if (const UWorld* World = OwningPlayer->GetWorld())
		{
			RequestScene(TEXT("/Game/Maps/") + World->GetMapName());
		}
	}
}

void UButterflySceneMenuWidget::HandleQuitClicked()
{
	if (APlayerController* OwningPlayer = GetOwningPlayer())
	{
		OwningPlayer->ConsoleCommand(TEXT("quit"));
	}
}
