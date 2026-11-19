import { readFileSync } from "node:fs";
import {
  ArticulationAnimationResource,
  HumanoidAnimationRetargetResource,
  HumanoidAutoRigResource,
  ImageToFourViewResource,
  ImgTo3dResource,
  MaterialTransferResource,
  MultiFormatExportResource,
  MultimodalToImageResource,
  PartSplitResource,
  TasksResource,
  TextTo3dResource,
} from "@manycore/aholo-sdk-lux3d";
import { AssetClient } from "@manycore/aholo-sdk-asset";
import { workspacePath } from "./paths.ts";

const region = process.env.AHOLO_REGION ?? "cn";
if (region !== "cn" && region !== "com") throw new Error("AHOLO_REGION must be cn or com");

function methods(prototype: object): string[] {
  return Object.getOwnPropertyNames(prototype)
    .filter((name) => name !== "constructor" && typeof prototype[name] === "function")
    .sort();
}

const packages = ["lux3d", "asset", "core"].map((name) => {
  const file = workspacePath(`Tools/lux-authoring/node_modules/@manycore/aholo-sdk-${name}/package.json`);
  const manifest = JSON.parse(readFileSync(file, "utf8"));
  return { name: manifest.name, version: manifest.version, license: manifest.license };
});

const resourceTypes = {
  multimodalToImage: MultimodalToImageResource,
  imageToFourView: ImageToFourViewResource,
  imgTo3d: ImgTo3dResource,
  textTo3d: TextTo3dResource,
  materialTransfer: MaterialTransferResource,
  multiFormatExport: MultiFormatExportResource,
  partSplit: PartSplitResource,
  articulationAnimation: ArticulationAnimationResource,
  humanoidAutoRig: HumanoidAutoRigResource,
  humanoidAnimationRetarget: HumanoidAnimationRetargetResource,
  tasks: TasksResource,
};
const resources = Object.fromEntries(Object.entries(resourceTypes)
  .map(([name, resourceType]) => [name, methods(resourceType.prototype)]));

console.log(JSON.stringify({
  status: "LOCAL_OFFICIAL_SDK_INSPECTION",
  packages,
  region,
  apiKeyConfigured: Boolean(process.env.AHOLO_API_KEY),
  lux3d: resources,
  assetUpload: methods(AssetClient.prototype),
  clientInstantiationRequiredKey: true,
  networkRequestMade: false,
  realGenerationVerified: false,
  note: "Local SDK surface only; authentication, quota, pricing, and generation require separately recorded real requests.",
}, null, 2));
