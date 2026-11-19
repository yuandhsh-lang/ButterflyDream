# 《蝶梦》四境运行说明

接手请先读 [四境最新版交接](../../蝶梦_四境最新版交接_20261119.md)，其中记录本轮实测、缺失布景和恢复来源。

> **本项目必须使用 Unreal Engine 5 引擎打开运行，不是独立 EXE。**
>
> 当前工程使用 **UE 5.8**，并需要与其兼容的 Windows C++ 构建工具链。仅双击 `.uproject` 但电脑没有 UE5，无法运行本项目。本项目不执行独立打包，也不提供免引擎安装包。

## 当前范围

当前版本只包含四境：

1. `Lux_StarSeaDream` —— 太虚瑶池星海，默认启动地图。
2. `Lux_InkCloudDream` —— 墨染云海琴台。
3. `Lux_CrystalMirageDream` —— 七宝琉璃幻境。
4. `Lux_TaijiAwakeningDream` —— 混沌太极归一。

第一张樱花地图 `F06_SakuraDream` 已从当前运行版本移除。历史备份和审计证据不属于当前运行内容。

## 运行条件

- Windows 64 位。
- Unreal Engine 5.8；本机路径为 `E:\Android\UE_5.8`。
- UE5.8 支持的 Windows C++ 编译工具链，用于构建 `ButterflyDream` 模块。
- 能运行本项目的 DirectX 12 显卡。历史开发机为 RTX 3050 Laptop 4 GB，不构成其他设备的性能保证。
- 已预生成的 Lux3D 资产随工程保存；运行现有资产不需要 Node、Blender、Lux3D API Key 或在线重新生成。

## 打开与构建

工程文件：`Unreal/ButterflyDream/ButterflyDream.uproject`。

可先用 UE5.8 打开该文件。如果提示模块缺失或需要重新构建，请先关闭本工程的 UE 编辑器，再在本机工作区根目录执行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File 'E:\紫萱2版\Tools\unreal\build-current-ue5.ps1'
```

当前工作区含中文目录，直接把中文工程路径传给 MSVC 可能损坏响应文件。该脚本在 `E:\ButterflyDream_Build\CurrentProject` 创建指向**当前工程**的 NTFS 目录联接，以 ASCII 路径调用 UE5.8 的标准 `Build.bat`；生成的模块仍写入 `Unreal/ButterflyDream/Binaries`，不需要维护另一份源码副本，也不是另一个游戏版本。脚本默认 UE 路径为 `E:\Android\UE_5.8`，可用 `-EngineRoot` 和 `-BuildRoot` 参数指定其他 ASCII 路径。

构建成功后，再用 UE5.8 打开工程并运行默认星海地图。编辑器加载、材质/Shader 初始化和缓存生成可能耗时，不能把编辑器启动速度当作独立游戏性能。

也可通过 UE5.8 的编辑器可执行文件进入游戏模式：

```powershell
& 'E:\Android\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe' 'E:\紫萱2版\Unreal\ButterflyDream\ButterflyDream.uproject' '/Game/Maps/Lux_StarSeaDream' -game -windowed -ResX=1280 -ResY=720
```

该命令仍然使用 UE5 引擎，不是独立游戏启动器。

## 操作

- `W / A / S / D`：前后左右飞行。
- 鼠标：调整观察与飞行方向。
- `Space / C`：上升 / 下降。
- `Shift`：加速飞行；靠近仙门时用于振翅共鸣。
- `P`：进入或退出环绕鉴赏视角。
- `R`：恢复当前安全点并清空飞行输入、速度和相机滞后。
- `Tab / Esc`：打开或收起四境罗盘。罗盘提供四境切换、继续、重新开始当前幻境和退出。

以游戏内最新提示为准。瞬移快捷键和近距离自动转场属于旧原型行为，不属于当前目标玩法。

## 画面与性能说明

2026-11-19 的 UE5.8.4 试玩已检查四境加载、出生点、主要地标贴图和 `W` 前飞。[实测记录与截图索引](../../蝶梦_四境最新版交接_20261119.md#已修复及实测)

完整布景仍在恢复范围内。重建前的地图快照保留了灯笼、锦鲤等旧关卡实例，接手时按 [逐境布景清单](../../蝶梦_四境最新版交接_20261119.md#场景为什么还是空) 对照恢复。
