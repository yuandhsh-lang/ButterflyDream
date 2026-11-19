# 蝶梦 · Butterfly Dream

《蝶梦》四境是一个 Unreal Engine 5.8.4 飞行探索项目，包含星海、水墨、琉璃和太极四张关卡。启动后从星海进入，按 `Tab` 打开四境罗盘。

## 获取并打开工程

1. 安装 Git LFS，并在克隆前执行 `git lfs install`。如果已经克隆，在仓库根目录执行 `git lfs pull` 获取关卡和资产。
2. 使用 Unreal Engine 5.8.4 打开 [ButterflyDream.uproject](Unreal/ButterflyDream/ButterflyDream.uproject)。Windows 上构建 C++ 模块需要兼容的 MSVC 工具链。
3. 如果需要从命令行构建，可在仓库根目录执行 `.\Tools\unreal\build-current-ue5.ps1 -EngineRoot 'C:\UE_5.8' -BuildRoot 'C:\ButterflyDream_Build'`，将参数替换为本机的引擎目录和可写的 ASCII 构建目录。

[运行和操作说明](Unreal/ButterflyDream/README_运行说明.md)中使用的 `E:\` 路径来自原开发机。文档引用的证据和备份保存在原工作区。
