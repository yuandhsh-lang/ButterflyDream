# 《蝶梦》四境架构与资产合规说明

[四境最新版交接](../蝶梦_四境最新版交接_20261119.md) 记录可运行的主工程、实测范围及逐境待恢复布景。

## 一、当前版本边界

当前工程为 `Unreal/ButterflyDream/ButterflyDream.uproject`，使用 **Unreal Engine 5.8.4**。

最新版本只包含四个运行地图：

1. `/Game/Maps/Lux_StarSeaDream`
2. `/Game/Maps/Lux_InkCloudDream`
3. `/Game/Maps/Lux_CrystalMirageDream`
4. `/Game/Maps/Lux_TaijiAwakeningDream`

`F06_SakuraDream` 及其运行时第三方资源已移出当前 Content。最近一次修复前的地图和资源快照位于 `Evidence/Unreal/Backups/20261119_142415_BeforeFourRealmRecovery/`，其中 `RemovedRuntime/` 和 `RemovedRuntime_143945/` 存放本轮 F06 隔离记录。

**本项目不是独立 EXE，需要 UE5.8 引擎及对应 Windows C++ 构建环境才能打开运行。当前不执行 Cook 或独立打包。**具体启动方式见 `Unreal/ButterflyDream/README_运行说明.md`。

历史六场景采集计划不再作为当前四境版本的完成度声明。四套未购买的 Fab 场景没有被改名放进当前工程，也不得以当前四境冒充六场景完成。

## 二、视觉与空间架构

四境必须作为不同空间验收，而不是同一展示廊换色：

| 地图 | 空间方向 | 光照与材质原则 |
|---|---|---|
| 星海 | 开阔横向水面、分散岛亭与桥、远处琼楼 | 星空与水面视差、局部青碧和琥珀光，不以浓雾盖远景 |
| 水墨 | 层叠山体、琴桥、云谷与高度变化 | 墨灰山体、宣纸色层次、局部暖光，不复用极光全景和全球镜面水 |
| 琉璃 | 不同高度的晶体浮岛、局部反射池与棱镜通道 | 虹彩仅用于晶体与关键机关，不做全屏 RGB 泛光 |
| 太极 | 径向太极空间、环形柱阵、中心浑天球与轨道出口 | 暗色宇宙、金白局部对比，不使用莲台水廊 |

旧 `Tools/unreal/build-all-5-lux-realms.py` 和 `rebuild-butterfly-lux-scenes.py` 不再是修复入口。它们曾统一覆盖材质、灯光和地图，不能用于当前四境恢复。

材质以可追溯的 GLB 与清单为恢复源。当前场景地标使用 `M_LuxScenePBR` 绑定各自的 Base Color 和金属度／粗糙度贴图。AO、Metallic、Roughness 和专用 Emissive 按来源处理。天空使用 `IsSky` 材质，天空球与水面使用 `NoCollision`，各境分别设置光照和雾。

用户确认的玩家蝴蝶是蓝紫翼、金色翅脉的 Lux3D G1 任务 `8345356`。原包中的 `MODEL.glb` 与 `Assets/LuxGenerated/G1_Textures/MODEL.glb` 已核对一致。游戏使用以此来源制作的蝶身及左右翼，分件位于 `Assets/LuxGenerated/V2_Butterfly/Ready/`，UE 网格位于 `/Game/LuxGenerated/Butterfly_B01/`。`ReconstructedButterfly_20261119/` 保存的是另一份历史外观及旧清单对照。

## 三、飞行、门与特效的真实归因

目标交互为：

`靠近仙门 → 按住 Shift 振翅蓄能 → 门到安全开度且净空通过 → 玩家穿过门平面 → 飞越完整三维隧道 → 到达出口后切换地图`

门必须保留各自配置的目标，不得按当前地图统一覆盖。E/Enter 瞬移、纯距离自动切图和无 Sweep 吸附不属于当前目标实现。

Lux3D 负责已有门、蝶、建筑和隧道模块的几何来源。门扇、星环和交互动画由 **UE/C++ 驱动**；没有真实官方动画播放证据时，不得写成“官方关节动画已在 UE 播放”。

只有资产内存在真实 `UNiagaraComponent`、对应 Renderer 和有效粒子，且输入能改变效果，才能把某项效果标为 Niagara。启用 Niagara 插件、ISM 网格群或旋转高模叶片本身都不是 Niagara 实现。

## 四、Lux3D 资产与来源证据

现有本地证据支持：

- 当前导入网格存在，本地 manifest 记录了 Lux3D 任务来源。
- 既有审计重算的 102 个哈希条目与记录匹配。
- 已记录的主要任务 ID 与七个禁用历史任务 ID 没有交集。
- 字体文件、场景源文件和当前地图均有本地文件可核查。

限制必须保留：

- 102 项匹配不等于完整账本；此前 V2 另有 103 个文件未纳入哈希。新增低模、材质和 Niagara 派生资产必须另记来源与处理后哈希。
- 本地 manifest 不等于完整的服务端原始创建/查询响应链，缺失部分不得补写。
- Aholo SDK 的 MIT 许可是工具代码许可，不自动等于 Lux3D 生成物的参赛或商用授权。生成输出授权仍需依据实际服务条款确认。
- 不使用“核心视觉 >85%”“100% 官方生成”等没有统一分母和测量方法的表述。

## 五、字体、叙事和第三方内容

### 字体

源工程中实际随附三款字体及各自 SIL OFL 1.1 文本：

- `MaShanZheng-Regular.ttf` / `MaShanZheng-OFL.txt`
- `ZCOOLXiaoWei-Regular.ttf` / `ZCOOLXiaoWei-OFL.txt`
- `ZhiMangXing-Regular.ttf` / `ZhiMangXing-OFL.txt`

已核验证件内部名称和许可元数据匹配。字体加载使用项目相对路径，不依赖 `V:` 或 `E:\紫萱2版`。当前不制作独立包，因此不存在“已验证随独立包附带”的声明。

### 剧情

当前两份 `story_config.json` 相同，包含 **4 个场景、28 个唯一文本 ID**。配置和加载数量可以验证，但不能把 28 条全部称为原创：其中包含《庄子》原典及白居易化用，准确说明应为“原创与公有领域原典/化用混合”。

叙事使用不遮挡主航线的短 HUD 回响，不再于出生后 0.5 秒在玩家正前方生成大诗卷，也不在世界与 HUD 同时重复同一内容。逐条触发仍须实机验证。

### 第三方文件

当前运行工程已移出 F06 第三方背景。历史 `SourceScenes/`、Blendkit 原始文件、转换 GLB、预览图和 F09 备份仍可能存在于工作区及备份区，**不得直接把整个工作区作为公开源码或素材包分发**。公开代码时应排除受限原始资产并保留合法获取指引、作者与许可记录。

## 六、验证状态标签

| 项目 | 当前状态 |
|---|---|
| 四境范围、默认星海、四境加载与 28 条叙事配置 | 最新模块已编译，四境均完成 UE 试玩加载，日志确认载入 28 条配置 |
| F06 从当前 Content 移除 | 已核对 `Content/Maps` 只有四个 Lux 地图，`Content/ThirdParty/F06` 已归档 |
| 出生点、相机初始朝向与前飞 | 试玩核对四境出生点与相机，星海实测蝶头朝向和 `W` 前飞 |
| 主要地标、贴图与空间区分 | 四境 DX12 试玩截图已核对。灯笼、锦鲤等旧场景实例待增量恢复 |
| 门链与特效 | 已核对八扇门的目标。完整穿越待验收，运行日志记录两套 Niagara 系统缺失 |
| 连续 20 次穿越、失败恢复、帧时间与 RAM/VRAM | NOT_TESTED |
| 独立 Windows 包与免 UE 运行 | 不在当前范围；明确需要 UE5.8 |

本轮实测范围以 [运行验证](../Evidence/Unreal/FourRealms_20261119/RecoveryValidation/runtime-checks.json) 和 [最新交接](../蝶梦_四境最新版交接_20261119.md) 为准。
