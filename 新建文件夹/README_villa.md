# VILLA AURELIA · Blender 5.2 全娱乐设施现代别墅

> 已在本机 **Blender 5.2.1 LTS** 实际运行验证，可直接在 Blender 的 Scripting 工作区运行，也可通过命令行生成。

## 文件说明

| 文件 | 内容 |
|---|---|
| `villa_entertainment_5_2.py` | 主 Python 脚本，一键清理场景并生成完整别墅 |
| `villa_entertainment_5_2.blend` | 已生成并保存的 Blender 场景（打开即用） |
| `villa_hero.png` | 主摄像机渲染，重点表现别墅、入口与室外泳池 |
| `villa_site_overview.png` | 第二个全景机位，完整收入泳池与半场篮球场 |
| `villa_floorplan_f1.png` | 一层平面裁切渲染：挑高客厅、台球室·吧台、室内恒温泳池 |
| `villa_floorplan_f2.png` | 二层平面裁切渲染：家庭影院、电竞房、专业健身房、走廊 |
| `villa_cutaway_f1.png` | 一层 3D 剖切透视，带空间图例和中英文标签 |
| `villa_cutaway_f2.png` | 二层 3D 剖切透视，可俯瞰挑高客厅中庭，带空间图例 |

## 使用方法

### 方式 A：Blender 内运行

1. 打开 Blender 5.2。
2. 进入 **Scripting** 工作区，点击 **Open**，选择 `villa_entertainment_5_2.py`。
3. 点击 **Run Script**（或 `Alt+P`）。
4. 脚本会清空当前场景并生成别墅，完成后摄像机自动被选中。
5. 按 `F12` 渲染色场景。默认输出为 `//villa_entertainment.png`。

### 方式 B：命令行运行

```powershell
"D:\TapTap\blender.exe" --background --factory-startup --python "villa_entertainment_5_2.py"
```

如需直接渲染：

```powershell
"D:\TapTap\blender.exe" --background --factory-startup --python "villa_entertainment_5_2.py" --python-expr "import bpy; bpy.ops.render.render(write_still=True)"
```

## 模型内容

### 建筑主体

- 20.0 m × 15.0 m 建筑轮廓，外墙按 200 mm 建模。
- 两层空间，层高约 3.2 m；平屋面 + 女儿墙 + 金属压顶。
- 大面积玻璃幕墙、黑色金属竖梃、木格栅、深色石材核心筒。
- 一层挑高客厅上方为真实天窗洞口；客厅通高约 6.4 m。
- 入口挑檐、悬浮楼梯、玻璃栏板、屋顶花池、木格栅遮阳。

### 一层

- **挑高客厅**：L 型沙发、茶几、休闲椅、落地灯、室内植物、吊灯。
- **台球室·吧台**：完整台球桌与球杆、吧台、酒柜、吧椅、桌球吊灯。
- **室内恒温泳池**：约 12 × 3 m 内池、水下灯、压顶、躺椅、绿植、玻璃隔断。

### 二层

- **家庭影院**：双排影院座椅、大屏幕、投影机、吸音木饰面。
- **电竞房**：三套游戏工位、RGB 灯带、霓虹灯牌、电脑机箱、电竞椅。
- **专业健身房**：跑步机、史密斯架、哑铃架、镜面墙、瑜伽垫、瑜伽球、储物柜。
- **走廊**：玻璃栏板、观景走廊、楼梯上方吊灯。

### 室外

- **8 × 4 m 下沉露天泳池**：真实挖空、池壁、池底、泳池台阶、扶梯、水下灯、木铺装。水体带透明折射与程序化池底焦散，室内恒温泳池同样使用透明水体。
- **半场篮球场**：15 × 14 m，三分线、罚球区、罚球圈、篮架、篮板、篮网、球、长凳。
- 草坪、绿篱、乔木、花池、入口台阶与步道灯。

### 材质与光照

- 全部为程序化材质，无外部图片/资产依赖。
- 灰白色墙体、暖色石材、木纹、大理石、绿色球场、蓝色半透明水体。
- 6 种低饱和分区色块 + 中英文字标签。
- 太阳光从西南切入；世界环境光 + 室内分区灯光 + 泳池/RGB 氛围光。
- 默认 Cycles 渲染，自动检测 OptiX / CUDA GPU；检测不到时回退 CPU。

## 剖切展示

`villa_cutaway_f1.png` 与 `villa_cutaway_f2.png` 使用同一套模型制作：隐藏 `03_SHELL_Roof`、屋面附属物，并对南/东立面进行展示性剖切；二层视图同时打开中庭和走廊，便于观察挑高关系。图例颜色与场景内的分区地台颜色一致。渲染后叠加的标题和空间图例只是展示排版，不包含在 `.blend` 模型中。

## 摄像机

| 名称 | 用途 |
|---|---|
| `Camera` | 主视角，强调别墅、入口和泳池 |
| `Camera_Site_Overview` | 全景视角，完整展示建筑、泳池和半场篮球场 |

在场景中选中摄像机，进入 `Scene > Camera` 选择活动相机，或在大纲视图中右键摄像机、选择 **Set Active Object as Camera**。

## 可编辑结构

大纲视图中的集合：

```text
VILLA_AURELIA_20x15
├─ 00_SITE
├─ 01_VILLA_SHELL
│  ├─ 01_SHELL_Body
│  ├─ 02_SHELL_Glazing
│  ├─ 03_SHELL_Roof       ← 直接隐藏可查看二层布置
│  └─ 04_SHELL_Stair
├─ 02_OUTDOOR_POOL
├─ 03_BASKETBALL_COURT
├─ 04_INTERIOR_F1
├─ 05_INTERIOR_F2
├─ 06_ROOM_LABELS
├─ 07_LANDSCAPE
├─ 08_LIGHTING
└─ 09_CAMERA
```

屋顶、幕墙、家具、灯光、标签均按前缀命名，便于后期细分、替换材质或导入现成资产。

## 调整建议

- **更换引擎**：脚本顶部把 `RENDER_ENGINE = "CYCLES"` 改为 `"EEVEE"` 可快速预览。
- **接入 HDRI/PBR**：可将 Poly Haven 的 HDRI 替换 World 中的环境光，并保持两点：World 只影响环境光，天空穹顶负责摄像机可见背景。
- **增强娱乐区**：在 `F1_Billiard_Bar`、`F2_Esports`、`F2_Home_Theater` 等集合中可直接替换为精细资产。
- **剖面/平面**：隐藏 `03_SHELL_Roof` 即可查看二层；隐藏二层集合与 F2 楼板即可查看一层。`villa_cutaway_*.png` 即按此方式渲染。
- **中文标签字体**：脚本会自动寻找 Windows 的 Microsoft YaHei、SimHei，macOS 的 PingFang 及 Linux 的 Noto CJK；找不到时仅显示英文标签。

## 已知边界

这是用于空间关系和氛围表达的基础布局模型，不是施工图模型。家具、树木和灯具均为程序化简模；场景中没有外部 HDRI 或第三方资产。若要达到照片级，可在保留体块、开洞与灯光结构的基础上替换材质、贴图和家具资产。
