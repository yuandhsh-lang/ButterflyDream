#include "FourRealmNiagaraEditorBridge.h"

#if WITH_EDITOR

#include "AssetToolsModule.h"
#include "IAssetTools.h"
#include "DataInterface/NiagaraDataInterfaceStaticMesh.h"
#include "NiagaraEmitter.h"
#include "NiagaraExternalSystemEditorUtilities.h"
#include "NiagaraMeshRendererMeshProperties.h"
#include "NiagaraMeshRendererProperties.h"
#include "NiagaraRibbonRendererProperties.h"
#include "NiagaraScript.h"
#include "NiagaraSystem.h"
#include "NiagaraTypes.h"
#include "NiagaraVariant.h"
#include "Engine/StaticMesh.h"
#include "Materials/MaterialInterface.h"
#include "Misc/FileHelper.h"
#include "Misc/PackageName.h"
#include "UObject/Package.h"
#include "UObject/SavePackage.h"
#include "JsonObjectConverter.h"
#include "Json.h"
#include "Serialization/JsonSerializer.h"

namespace FourRealmNiagara
{
	constexpr const TCHAR* FxPath = TEXT("/Game/FX");
	constexpr const TCHAR* RibbonTemplate = TEXT("/Niagara/DefaultAssets/Templates/Emitters/LocationBasedRibbon");
	constexpr const TCHAR* MeshTemplate = TEXT("/Niagara/DefaultAssets/Templates/Emitters/UpwardMeshBurst");
	constexpr const TCHAR* SampleStaticMesh = TEXT("/Niagara/Modules/Spawn/MeshInterface/SampleStaticMesh");
	constexpr const TCHAR* RibbonMaterial = TEXT("/Niagara/DefaultAssets/DefaultRIbbonMaterial");

	FString ContextErrors(const FNiagaraExternalEditContext& Context)
	{
		TArray<FString> Messages;
		for (const FText& Error : Context.Errors)
		{
			Messages.Add(Error.ToString());
		}
		return FString::Join(Messages, TEXT(" | "));
	}

	bool WriteReport(const FString& Path, const FString& AssetPath, bool bSuccess, const FNiagaraExt_SystemCompileState& State, const FString& Errors)
	{
		FString StateJson;
		FJsonObjectConverter::UStructToJsonObjectString(State, StateJson, 0, 0);
		FString Escaped = Errors.Replace(TEXT("\\"), TEXT("\\\\")).Replace(TEXT("\""), TEXT("\\\"")).Replace(TEXT("\r"), TEXT(" ")).Replace(TEXT("\n"), TEXT(" "));
		const FString Content = FString::Printf(
			TEXT("{\"status\":\"%s\",\"asset\":\"%s\",\"compile\":%s,\"errors\":\"%s\"}\n"),
			bSuccess ? TEXT("SUCCEEDED") : TEXT("FAILED"),
			*AssetPath,
			*StateJson,
			*Escaped);
		return FFileHelper::SaveStringToFile(Content, *Path);
	}

	bool SaveAsset(UObject* Asset)
	{
		if (!Asset)
		{
			return false;
		}
		const FString FileName = FPackageName::LongPackageNameToFilename(Asset->GetOutermost()->GetName(), FPackageName::GetAssetPackageExtension());
		return UPackage::SavePackage(Asset->GetOutermost(), Asset, *FileName, FSavePackageArgs());
	}

	UNiagaraSystem* CreateSystem(const FString& Name, FNiagaraExternalEditContext& Context)
	{
		UNiagaraSystem* System = UNiagaraExternalEditUtilities::CreateNiagaraSystem(Name, FxPath, nullptr, Context);
		if (System)
		{
			Context = FNiagaraExternalEditContext(System);
		}
		return System;
	}

	FNiagaraExt_EmitterTopology AddEmitter(UNiagaraSystem* System, const TCHAR* TemplatePath, FName EmitterName, FNiagaraExternalEditContext& Context)
	{
		UNiagaraEmitter* Template = LoadObject<UNiagaraEmitter>(nullptr, TemplatePath);
		FNiagaraExt_EmitterTopology Topology;
		if (!Template)
		{
			Context.Error(FText::FromString(FString::Printf(TEXT("Missing emitter template %s"), TemplatePath)));
			return Topology;
		}
		UNiagaraExternalEditUtilities::AddEmitter(Template, EmitterName, Topology, Context);
		return Topology;
	}

	template<typename T>
	void AddValueParameter(UNiagaraSystem* System, FName Name, const FNiagaraTypeDefinition& Type, const T& DefaultValue, FNiagaraExternalEditContext& Context)
	{
		FNiagaraExt_UserVariable Variable;
		Variable.Name = Name;
		Variable.Type = Type;
		FNiagaraVariant Variant;
		Variant.SetBytesValue(Type, DefaultValue);
		Variable.DefaultValue.Set(Type, Variant);
		UNiagaraExternalEditUtilities::AddUserVariable(System, Variable, Context);
	}

	void AddMeshParameter(UNiagaraSystem* System, UStaticMesh* Mesh, FNiagaraExternalEditContext& Context)
	{
		FNiagaraExt_UserVariable Variable;
		Variable.Name = TEXT("TargetMesh");
		Variable.Type = FNiagaraTypeDefinition::GetUStaticMeshDef();
		Variable.DefaultValue.Set(Variable.Type, FNiagaraVariant(TObjectPtr<UObject>(Mesh)));
		UNiagaraExternalEditUtilities::AddUserVariable(System, Variable, Context);
	}

	FName FindModule(UNiagaraSystem* System, FName EmitterName, FName ScriptName, const FString& Match, FNiagaraExternalEditContext& Context)
	{
		FNiagaraExt_EmitterTopology Topology;
		UNiagaraExternalEditUtilities::GetEmitterTopology(FNiagaraExt_StackItemReference(System, EmitterName), Topology, Context);
		const FNiagaraExt_ScriptStackTopology* Stack = nullptr;
		if (ScriptName == TEXT("ParticleSpawnScript")) Stack = &Topology.ParticleSpawnScript;
		else if (ScriptName == TEXT("ParticleUpdateScript")) Stack = &Topology.ParticleUpdateScript;
		else if (ScriptName == TEXT("EmitterUpdateScript")) Stack = &Topology.EmitterUpdateScript;
		else if (ScriptName == TEXT("EmitterSpawnScript")) Stack = &Topology.EmitterSpawnScript;
		if (!Stack)
		{
			Context.Error(FText::FromString(FString::Printf(TEXT("Unsupported script stack %s"), *ScriptName.ToString())));
			return NAME_None;
		}
		for (const FNiagaraExt_ModuleTopology& Module : Stack->Modules)
		{
			if (Module.ModuleName.ToString().Contains(Match, ESearchCase::IgnoreCase))
			{
				return Module.ModuleName;
			}
		}
		Context.Error(FText::FromString(FString::Printf(TEXT("Module containing %s was not found in %s"), *Match, *ScriptName.ToString())));
		return NAME_None;
	}

	void SetExpression(UNiagaraSystem* System, FName EmitterName, FName ScriptName, FName ModuleName, FName InputName, const FString& Expression, FNiagaraExternalEditContext& Context)
	{
		FNiagaraExt_StackItemReference InputRef(System, EmitterName, ScriptName, ModuleName);
		InputRef.InputNameStack.Add(InputName);
		FNiagaraExt_StackInputValue Value;
		FNiagaraExt_StackInputData_HlslExpression& Data = Value.InitializeAs<FNiagaraExt_StackInputData_HlslExpression>();
		Data.HlslExpression = Expression;
		UNiagaraExternalEditUtilities::SetStackInputData(InputRef, Value, Context);
	}

	void SetExpressionBySuffix(UNiagaraSystem* System, FName EmitterName, FName ScriptName, FName ModuleName, const FString& InputSuffix, const FString& Expression, FNiagaraExternalEditContext& Context)
	{
		FNiagaraExt_ModuleTopology Module;
		UNiagaraExternalEditUtilities::GetModuleTopology(FNiagaraExt_StackItemReference(System, EmitterName, ScriptName, ModuleName), Module, Context);
		for (const FNiagaraExt_StackInputTopology& Input : Module.Inputs)
		{
			const FString Name = Input.Name.ToString();
			if (Name == InputSuffix || Name.EndsWith(InputSuffix))
			{
				SetExpression(System, EmitterName, ScriptName, Module.ModuleName, Input.Name, Expression, Context);
				return;
			}
		}
		Context.Error(FText::FromString(FString::Printf(TEXT("Input ending in %s was not found on %s"), *InputSuffix, *Module.ModuleName.ToString())));
	}

	FNiagaraExt_ModuleTopology AddModule(UNiagaraSystem* System, FName EmitterName, FName ScriptName, FName AfterModule, const TCHAR* AssetPath, FNiagaraExternalEditContext& Context)
	{
		UNiagaraScript* Script = LoadObject<UNiagaraScript>(nullptr, AssetPath);
		FNiagaraExt_ModuleTopology Module;
		if (!Script)
		{
			Context.Error(FText::FromString(FString::Printf(TEXT("Missing module asset %s"), AssetPath)));
			return Module;
		}
		UNiagaraExternalEditUtilities::AddModule(FNiagaraExt_StackItemReference(System, EmitterName, ScriptName, AfterModule), Script, Module, Context);
		return Module;
	}

	FNiagaraExt_ModuleTopology AddPositionAssignments(UNiagaraSystem* System, FName EmitterName, FName ScriptName, FName AfterModule, const TArray<FName>& Targets, FNiagaraExternalEditContext& Context)
	{
		TArray<FNiagaraExt_SetParameterEntry> Entries;
		for (FName Target : Targets)
		{
			FNiagaraExt_SetParameterEntry Entry;
			Entry.Variable.Name = Target;
			Entry.Variable.Type = FNiagaraTypeDefinition::GetPositionDef();
			FNiagaraVariant Variant;
			const FNiagaraPosition Zero;
			Variant.SetBytesValue(Entry.Variable.Type, Zero);
			Entry.DefaultValue.Set(Entry.Variable.Type, Variant);
			Entries.Add(Entry);
		}
		FNiagaraExt_ModuleTopology Module;
		UNiagaraExternalEditUtilities::AddSetParametersModule(
			FNiagaraExt_StackItemReference(System, EmitterName, ScriptName, AfterModule), Entries, Module, Context);
		return Module;
	}

	bool EditRenderer(UNiagaraSystem* System, FName EmitterName, const TFunction<void(const TSharedPtr<FJsonObject>&)>& Edit, FNiagaraExternalEditContext& Context)
	{
		FNiagaraExt_EmitterTopology Topology;
		UNiagaraExternalEditUtilities::GetEmitterTopology(FNiagaraExt_StackItemReference(System, EmitterName), Topology, Context);
		if (Topology.Renderers.Num() == 0)
		{
			Context.Error(FText::FromString(TEXT("No renderer exists on the added emitter")));
			return false;
		}
		FNiagaraExt_StackItemReference Ref(System, EmitterName);
		Ref.RendererIndex = Topology.Renderers[0].RendererIndex;
		FNiagaraExt_RendererData Data;
		UNiagaraExternalEditUtilities::GetRendererData(Ref, Data, Context);
		TSharedPtr<FJsonObject> Json;
		if (!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Data.PropertyValues), Json) || !Json.IsValid())
		{
			Context.Error(FText::FromString(TEXT("Renderer property data is not valid JSON")));
			return false;
		}
		Edit(Json);
		if (!FJsonSerializer::Serialize(Json, TJsonWriterFactory<>::Create(&Data.PropertyValues)))
		{
			Context.Error(FText::FromString(TEXT("Could not serialize renderer edits")));
			return false;
		}
		UNiagaraExternalEditUtilities::SetRendererData(Ref, Data, Context);
		return true;
	}

	bool CompileAndSave(UNiagaraSystem* System, const FString& ReportPath, FNiagaraExternalEditContext& Context)
	{
		if (!System)
		{
			WriteReport(ReportPath, TEXT(""), false, FNiagaraExt_SystemCompileState(), ContextErrors(Context));
			return false;
		}
		const FString AssetPath = System->GetPathName();
		const FString ExistingErrors = ContextErrors(Context);
		if (!ExistingErrors.IsEmpty())
		{
			WriteReport(ReportPath, AssetPath, false, FNiagaraExt_SystemCompileState(), ExistingErrors);
			return false;
		}
		if (!System->RequestCompile(true))
		{
			WriteReport(ReportPath, AssetPath, false, FNiagaraExt_SystemCompileState(), TEXT("RequestCompile returned false"));
			return false;
		}
		System->WaitForCompilationComplete(false, true);
		FNiagaraExt_SystemCompileState State;
		UNiagaraExternalEditUtilities::GetSystemCompileState(System, State, Context);
		const bool bStatusValid = State.AggregateStatus == ENiagaraExt_ScriptCompileStatus::UpToDate ||
			State.AggregateStatus == ENiagaraExt_ScriptCompileStatus::UpToDateWithWarnings ||
			State.AggregateStatus == ENiagaraExt_ScriptCompileStatus::ComputeUpToDateWithWarnings;
		const bool bSuccess = bStatusValid && !State.bHasErrors && SaveAsset(System);
		WriteReport(ReportPath, AssetPath, bSuccess, State, ContextErrors(Context));
		return bSuccess;
	}
}

bool UFourRealmNiagaraEditorBridge::CreateWingRibbonSystem(const FString& ReportPath)
{
	using namespace FourRealmNiagara;
	FNiagaraExternalEditContext Context;
	UNiagaraSystem* System = CreateSystem(TEXT("NS_Butterfly_WingRibbon"), Context);
	const FName EmitterName = TEXT("ButterflyWingRibbon");
	FNiagaraExt_EmitterTopology Topology = AddEmitter(System, RibbonTemplate, EmitterName, Context);
	if (!System || Topology.EmitterName != EmitterName)
	{
		return CompileAndSave(System, ReportPath, Context);
	}

	UMaterialInterface* LocalMaterial = LoadObject<UMaterialInterface>(nullptr, TEXT("/Game/FX/M_LuxRibbon"));
	if (!LocalMaterial)
	{
		UMaterialInterface* Source = LoadObject<UMaterialInterface>(nullptr, RibbonMaterial);
		if (Source)
		{
			LocalMaterial = Cast<UMaterialInterface>(FAssetToolsModule::GetModule().Get().DuplicateAsset(TEXT("M_LuxRibbon"), FxPath, Source));
		}
	}
	if (!LocalMaterial)
	{
		Context.Error(FText::FromString(TEXT("Could not create the local ribbon material")));
		return CompileAndSave(System, ReportPath, Context);
	}
	LocalMaterial->CheckMaterialUsage(EMaterialUsage::MATUSAGE_NiagaraRibbons);
	SaveAsset(LocalMaterial);
	EditRenderer(System, EmitterName, [&LocalMaterial](const TSharedPtr<FJsonObject>& Json)
	{
		Json->SetStringField(TEXT("Material"), LocalMaterial->GetPathName());
		Json->SetStringField(TEXT("FacingMode"), TEXT("Screen"));
		Json->SetStringField(TEXT("Shape"), TEXT("Plane"));
	}, Context);
	return CompileAndSave(System, ReportPath, Context);
}

bool UFourRealmNiagaraEditorBridge::CreateGateMeshSwarmSystem(UStaticMesh* TargetMesh, UStaticMesh* RenderMesh, const FString& ReportPath)
{
	using namespace FourRealmNiagara;
	FNiagaraExternalEditContext Context;
	if (!TargetMesh || !RenderMesh)
	{
		WriteReport(ReportPath, TEXT("/Game/FX/NS_Gate_MeshSwarm"), false, FNiagaraExt_SystemCompileState(), TEXT("TargetMesh or RenderMesh is null"));
		return false;
	}
	(void)TargetMesh;
	UNiagaraSystem* System = CreateSystem(TEXT("NS_Gate_MeshSwarm"), Context);
	const FName EmitterName = TEXT("GateMeshSwarm");
	FNiagaraExt_EmitterTopology Topology = AddEmitter(System, MeshTemplate, EmitterName, Context);
	if (!System || Topology.EmitterName != EmitterName)
	{
		return CompileAndSave(System, ReportPath, Context);
	}

	const float MeshSpan = FMath::Max(1.0f, static_cast<float>(RenderMesh->GetBounds().GetBox().GetSize().GetMax()));
	const float ParticleScale = 4.0f / MeshSpan;
	EditRenderer(System, EmitterName, [&RenderMesh, ParticleScale](const TSharedPtr<FJsonObject>& Json)
	{
		TSharedPtr<FJsonObject> Slot = MakeShared<FJsonObject>();
		Slot->SetStringField(TEXT("Mesh"), RenderMesh->GetPathName());
		TSharedPtr<FJsonObject> Scale = MakeShared<FJsonObject>();
		Scale->SetNumberField(TEXT("X"), ParticleScale);
		Scale->SetNumberField(TEXT("Y"), ParticleScale);
		Scale->SetNumberField(TEXT("Z"), ParticleScale);
		Slot->SetObjectField(TEXT("Scale"), Scale);
		Slot->SetNumberField(TEXT("LODLevel"), 0);
		TArray<TSharedPtr<FJsonValue>> Meshes;
		Meshes.Add(MakeShared<FJsonValueObject>(Slot));
		Json->SetArrayField(TEXT("Meshes"), Meshes);
		Json->SetBoolField(TEXT("bCastShadows"), false);
	}, Context);
	for (const FStaticMaterial& MaterialSlot : RenderMesh->GetStaticMaterials())
	{
		UMaterialInterface* Material = MaterialSlot.MaterialInterface;
		if (Material && !Material->GetOutermost()->GetName().StartsWith(TEXT("/Engine")) && !Material->GetOutermost()->GetName().StartsWith(TEXT("/Niagara")))
		{
			Material->CheckMaterialUsage(EMaterialUsage::MATUSAGE_NiagaraMeshParticles);
			SaveAsset(Material);
		}
	}
	return CompileAndSave(System, ReportPath, Context);
}

#else

bool UFourRealmNiagaraEditorBridge::CreateWingRibbonSystem(const FString& ReportPath)
{
	return false;
}

bool UFourRealmNiagaraEditorBridge::CreateGateMeshSwarmSystem(UStaticMesh* TargetMesh, UStaticMesh* RenderMesh, const FString& ReportPath)
{
	return false;
}

#endif
