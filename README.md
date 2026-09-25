# TMSU Studio

> 一个以**文件为记录**、以**标签为字段**、以**查询为接口**的可视化文件数据库客户端。

本项目是 **TMSU 的图形前端**。TMSU 是一个独立的第三方命令行工具（Go 编写），提供标签存储和查询引擎。本项目不包含 TMSU 源码，只调用它的 CLI。**不修改任何原始文件**，只读写标签。

## 系统要求

- **Ubuntu 22.04 LTS (Jammy Jellyfish)** — 主要开发与测试环境
- 其他 Debian 系发行版（Ubuntu 24.04、Linux Mint 21+、Debian 12+）理论可用
- 桌面环境：GNOME / KDE / Xfce 均可（依赖 xdg-utils）
- 需要 FUSE 支持（仅 TMSU 的 VFS 功能需要，本项目不依赖）

---

## 目录

- [核心理念](#核心理念)
- [功能](#功能)
- [界面布局](#界面布局)
- [依赖](#依赖)
- [安装](#安装)
- [快速开始](#快速开始)
- [使用指南](#使用指南)
- [快捷键](#快捷键)
- [设计原则](#设计原则)
- [项目结构](#项目结构)
- [数据存储](#数据存储)
- [常见问题](#常见问题)
- [故障排除](#故障排除)
- [相关项目](#相关项目)

---

## 核心理念

| 原则 | 说明 |
| :--- | :--- |
| **不修改原始文件** | 不移动、不重命名、不删除，只读写标签 |
| **目录与标签分离** | 目录是文件系统的组织方式，标签是数据库的组织方式 |
| **查询是对话** | 对结果集继续施加条件，形成**查询链** |
| **分面探索** | 基于当前结果动态计算可选下一步 |
| **查询可沉淀** | 常用查询链保存为**智能集合**，一键调用 |
| **只读引用** | 拖拽、复制只传路径引用，不做剪切 |

TMSU Studio 的本质是一个**文件数据库客户端**：

- **存储引擎**：[TMSU](https://github.com/oniony/TMSU)（外部依赖，SQLite）
- **查询语言**：TMSU 标签表达式
- **终端**：本项目（PyQt6）
- **消费端**：视频剪辑软件、文件管理器、播放器

本项目只通过 `subprocess` 调用 `tmsu` 命令，不链接其源码，不修改其行为。

---

## 功能

| 模块 | 能力 |
| :--- | :--- |
| **目录树** | 导航 + 展开状态持久化（界面状态，不入数据库） |
| **查询链** | 逐步叠加条件，可回退、可分支 |
| **分面面板** | 基于结果集**异步**计算标签 / 类型 / 年份分面 |
| **智能集合** | 保存查询链为命名集合，一键调用 |
| **缩略图** | 图片直接显示，视频 ffmpeg 抓帧 + md5 缓存，**异步生成** |
| **元数据** | ffprobe（视频）+ exiftool（图片） |
| **标签管理** | 重命名 / 合并 / 删除 |
| **标签补全** | 查询框与标签输入框均支持补全 |
| **拖拽** | 原始绝对路径拖入剪辑软件 |
| **多数据库** | 最近 DB 记忆，一键切换，智能向上查找 |
| **右键菜单** | 加 / 移除 / 编辑标签，复制路径，打开所在目录 |
| **启动助手** | 找不到数据库时弹窗选择或初始化 |
| **键盘导航** | 目录树回车展开/折叠，文件列表回车打开 |

---

## 界面布局

```
┌──────────────────────────────────────────────────────────────┐
│ 数据库: [/home/user/files ▾] [切换…]              [标签管理] │
├──────────────┬───────────────────────────────────────────────┤
│ 智能集合     │ [查询: ........................] [执行] [重置] │
│  ★ 2024航拍  │ [存为集合]                                     │
│  ★ 未调色    │ [video] › [year>=2020] › [时长>10min] ✕       │
│  ★ 本周新增  ├──────────────────────┬────────────────────────┤
│              │ 结果列表             │ 预览                   │
│ 目录         │ IMG_001.jpg          │ [缩略图]               │
│ 📁 files     │ drone_001.mp4        │ 路径：/home/.../x.mp4  │
│  📁 photos   │ ...                  │ 标签：video 航拍 2024  │
│  📁 videos   │                      │ 时长：00:03:21         │
│   📁 raw     │                      │ 分辨率：3840x2160      │
│              ├──────────────────────┴────────────────────────┤
│              │ 分面                                           │
│              │ 标签 [music(32)] [jazz(12)] [live(5)]          │
│              │ 类型 [视频(48)] [图片(2)]                      │
│              │ 年份 [2024(30)] [2023(15)] [2022(5)]           │
└──────────────┴───────────────────────────────────────────────┘
```

左侧自上而下：**智能集合** + **目录树**。右侧自上而下：**查询行** + **面包屑** + **文件列表/预览** + **分面**。

---

## 依赖

| 类别 | 依赖 | 用途 |
| :--- | :--- | :--- |
| **外部工具** | `tmsu` | 标签存储引擎（第三方） |
| 系统 | `ffmpeg` | 视频缩略图 + ffprobe 元数据 |
| 系统 | `libimage-exiftool-perl` | 图片 EXIF |
| 系统 | `xdg-utils` | `xdg-open` 打开文件 |
| Python | `python3` `python3-venv` `python3-pip` | 运行环境 |
| Python | `PyQt6>=6.6` | GUI 框架 |

以上依赖由两个安装脚本自动处理。

---

## 安装

安装分两步：**先装 TMSU 引擎，再装本项目**。两个脚本各司其职。

### 第一步：安装 TMSU（外部依赖）

```bash
chmod +x install_tmsu.sh
./install_tmsu.sh
```

`install_tmsu.sh` 会：

1. 安装编译依赖（`golang-go` `git` `build-essential` `libfuse-dev`）
2. 从 GitHub 克隆 TMSU 源码到项目目录下的 `TMSU/`
3. 设置 Go 模块代理（`goproxy.cn`）
4. 固定依赖版本（`go-fuse@v1.0.0`、`go-sqlite3@v1.14.7`）
5. 编译并安装到 `/usr/bin/tmsu`
6. 验证 `tmsu --version`

> **如果你已经有 `tmsu`**，可以跳过这一步：
> ```bash
> tmsu --version   # 有版本号输出即可
> ```
> Ubuntu 官方仓库没有 `tmsu` 包，可以从源码编译，或从 GitHub Releases 下载二进制。

### 第二步：安装 TMSU Studio

```bash
chmod +x install.sh
./install.sh
```

`install.sh` 会：

1. 安装系统依赖（`python3` `python3-venv` `python3-pip` `ffmpeg` `libimage-exiftool-perl` `xdg-utils`）
2. 创建 Python 虚拟环境 `.venv`
3. 安装 PyQt6
4. 生成命令行启动器 `~/.local/bin/tmsu-studio`
5. 生成桌面入口 `~/.local/share/applications/tmsu-studio.desktop`

### 一次性完成（可选）

```bash
chmod +x install_tmsu.sh install.sh
./install_tmsu.sh && ./install.sh
```

### PATH 提示

若 `~/.local/bin` 不在 `PATH` 中，安装脚本会提示。按提示把下面一行加入 `~/.bashrc` 或 `~/.zshrc`：

```bash
export PATH="$HOME/.local/bin:$PATH"
```

然后：

```bash
source ~/.bashrc
```

---

## 快速开始

### 1. 初始化一个数据库

```bash
cd ~/Videos           # 你的素材根目录
tmsu init             # 创建 ~/Videos/.tmsu/db
tmsu-studio           # 启动
```

TMSU 会在当前目录创建 `.tmsu/` 隐藏目录，数据库文件是 `.tmsu/db`（SQLite）。

### 2. 首次启动

如果启动时当前目录及其父目录**没有** `.tmsu`，会弹出启动对话框：

- 从最近打开的数据库中选择
- 浏览已有数据库（自动向上查找 `.tmsu`）
- 在当前目录初始化
- 选择其他目录并初始化

也可以显式指定：

```bash
TMSU_ROOT=~/Videos tmsu-studio
```

### 3. 打第一批标签

1. 左侧目录树点击 `photos/2024`（或选中后用 `Enter` 展开）
2. 右侧列表出现该目录下的文件
3. `Ctrl+A` 全选
4. 右键 → 添加标签 → 输入 `photo 2024`
5. 清空查询框，列表回到浏览模式

### 4. 用标签查询

在查询框输入表达式并回车：

```
photo
photo and 2024
(photo or video) and not raw
type=video and project=A
```

### 5. 保存为智能集合

构建好查询链后，点 **“存为集合”** 或按 `Ctrl+S`：

```
名称：2024 航拍未调色
```

左侧“智能集合”区域出现 `★ 2024 航拍未调色`，以后点击即可一键调用。

---

## 使用指南

### 目录浏览模式

- 左侧目录树：导航 + 范围限定
- 单击目录 → 立即刷新右侧列表
- `Enter` → 展开或折叠；**仅展开时刷新列表**
- `↑/↓` → 移动光标，不刷新
- 清空查询框 → 回到浏览模式
- **目录树只做导航，不给目录打标签**

### 标签查询模式

查询框输入 TMSU 表达式，回车追加到查询链。支持：

| 语法 | 示例 |
| :--- | :--- |
| 单标签 | `music` |
| AND | `music and jazz` |
| OR | `mp3 or flac` |
| NOT | `not jazz` |
| 括号 | `(mp3 or flac) and not jazz` |
| 值比较 | `year >= 2020`、`rating = 5` |
| 组合 | `type=video and year>=2020 and not raw` |

**标签补全**：输入时自动弹出匹配的已有标签（只需输入最后一个词的片段）。打完标签后补全列表自动刷新。

### 分级查询

查询链显示在面包屑栏：

```
[video] › [year>=2020] › [时长>10min] ✕
```

- 点任一步骤 → 回退到那一步
- 点 `✕` → 清空整条链
- 点分面按钮 → 追加一步
- `Ctrl+Z` → 撤销最后一步

### 分面探索

底部显示基于当前结果的动态分面，**异步计算**：

```
标签  [music(32)] [jazz(12)] [live(5)]
类型  [视频(48)] [图片(2)]
年份  [2024(30)] [2023(15)] [2022(5)]
```

点击任一按钮 = 追加该条件到查询链。分面随结果集**动态变化**。

**分两批异步计算**：

1. **第一批**：类型 + 年份（只看路径，毫秒级）
2. **第二批**：标签（对每个文件调 `tmsu tags`，秒级）

先显示快分面，慢分面到达后追加，UI 全程不卡。

> 结果超过 `FACET_LIMIT`（默认 200）时暂不计算分面，只显示提示。

### 智能集合

左侧“智能集合”区域显示所有保存的查询链。

| 操作 | 方式 |
| :--- | :--- |
| 调用 | 单击集合名 → 查询链自动加载并执行 |
| 保存 | `Ctrl+S` 或点“存为集合”按钮 |
| 重命名 | 双击集合，或右键 → 重命名 |
| 更新为当前查询 | 右键 → 更新为当前查询 |
| 删除 | 右键 → 删除 |
| 新建 | 在空白处右键 → 新建集合 |

**每个数据库有独立的集合列表**，切换 DB 时集合跟着换。

### 打标签

1. `Ctrl/Shift` 多选文件
2. 右键 → 添加 / 移除 / 编辑标签
3. 输入时支持标签补全

| 操作 | 行为 |
| :--- | :--- |
| **添加** | 对选中文件追加标签，保留已有标签 |
| **移除** | 对选中文件移除指定标签（只列共同标签供选） |
| **编辑** | 用新标签集替换所有选中文件的标签 |

**打完标签后，列表保持原选中状态**，不会跳回第一个文件。

### 拖拽到剪辑软件

查询出结果 → 多选 → 直接拖到 DaVinci / Premiere / Kdenlive 的媒体池。

拖拽使用**原始绝对路径**，不依赖 VFS，工程永久有效。

### 复制路径

右键 → 复制路径，写入剪贴板：

- `file://` URL（给文件管理器和剪辑软件）
- 纯文本路径（给文本编辑器）

### 切换数据库

顶部下拉选择最近 DB，或点“切换…”选择其他目录。

| 操作 | 行为 |
| :--- | :--- |
| 选择当前 DB 的子目录 | 只改 scope，不换 DB |
| 选择其他 DB 的根或子目录 | 切换到新 DB |
| 选择无 `.tmsu` 的目录 | 智能向上查找最近的 DB |

每个 DB 有独立的标签、目录树状态、查询历史、智能集合。

---

## 快捷键

| 键 | 功能 |
| :--- | :--- |
| `Ctrl+A` | 全选文件 |
| `Enter` | 执行查询 / 打开选中文件 / 目录树展开折叠 |
| `Ctrl+Z` | 撤销一步查询 |
| `Ctrl+S` | 保存当前查询为智能集合 |
| `F5` | 刷新 |
| `Ctrl/Shift + 点击` | 多选 |
| `Tab` | 切换控件焦点 |

---

## 设计原则

| 支持 | 不支持 |
| :--- | :--- |
| 拖拽到外部程序 | ❌ 剪切 |
| 复制路径到剪贴板 | ❌ 移动文件 |
| 默认应用打开 | ❌ 重命名文件 |
| 打开所在目录 | ❌ 删除文件 |
| 加 / 移除 / 编辑标签 | ❌ 修改原始文件 |

**TMSU Studio 是标签数据库的可视化客户端，不是文件管理器。**

文件移动、重命名、删除交给系统文件管理器。如果文件路径变化，到数据库根目录执行 `tmsu repair` 即可修复。

---

## 项目结构

```
tmsu-studio/
├── README.md
├── requirements.txt
├── install_tmsu.sh             编译安装 TMSU（外部依赖）
├── install.sh                  安装本项目
├── run.sh                      开发时直接运行
├── TMSU/                       TMSU 源码（install_tmsu.sh 克隆到此，不提交）
└── tmsu_studio/                本项目的全部源码
    ├── __init__.py             版本号
    ├── __main__.py             入口，启动流程
    ├── config.py               常量、路径、DB 解析
    ├── state.py                UI 状态持久化
    ├── tmsu_client.py          TMSU 命令行封装
    ├── query_chain.py          查询链模型
    ├── facets.py               分面计算
    ├── facets_async.py         分面异步加载器
    ├── thumbnail.py            缩略图缓存
    ├── thumbnail_async.py      异步缩略图加载器
    ├── metadata.py             ffprobe/exiftool 元数据
    ├── directory_tree.py       目录树导航
    ├── file_list.py            文件列表
    ├── preview.py              预览面板
    ├── tag_input.py            带补全的标签输入对话框
    ├── tag_manager.py          标签管理对话框
    ├── collections_panel.py    智能集合面板
    ├── startup.py              启动选择/初始化对话框
    └── main_window.py          主窗口
```

> **关于 `TMSU/` 目录**：运行 `install_tmsu.sh` 会在项目根目录下克隆 TMSU 源码（Go 编写），仅用于本地编译。**这不是本仓库的代码，应加入 `.gitignore` 不提交。** 本仓库与 TMSU 项目无源码级耦合，只通过 `tmsu` 命令交互。

### 架构层次

```
┌──────────────────────────────────────────────────┐
│                     UI 层                         │
│  MainWindow   DirectoryTree   FileListWidget     │
│  PreviewPanel CollectionsPanel  TagManagerDialog │
│  TagInputDialog  StartupDialog                    │
└────────────────────┬─────────────────────────────┘
                     │ 信号槽 / 方法
┌────────────────────▼─────────────────────────────┐
│                   服务层                          │
│  TmsuClient（Repository）                        │
│  QueryChain（查询模型）                          │
│  FacetLoader / ThumbnailLoader（异步）           │
│  metadata（Adapter）                             │
│  state（UI 状态持久化）                          │
└────────────────────┬─────────────────────────────┘
                     │ subprocess
┌────────────────────▼─────────────────────────────┐
│  tmsu（外部） / ffmpeg / ffprobe / exiftool      │
└──────────────────────────────────────────────────┘
```

### 设计模式

| 模式 | 位置 | 职责 |
| :--- | :--- | :--- |
| Repository | `TmsuClient` | 隔离 UI 与命令行 |
| Facade | `MainWindow` | 组装所有模块 |
| Adapter | `metadata` | ffprobe/exiftool 输出 → UI 字典 |
| Value Object | `QueryStep` | 不可变查询单元 |
| Chain of Responsibility | `QueryChain` | 多步过滤累积 |
| Observer | Qt 信号槽 | 查询/选中变化驱动 UI |
| Producer-Consumer | `ThumbnailLoader` / `FacetLoader` | 工作线程生成，主线程消费 |

---

## 数据存储

| 数据 | 位置 | 说明 |
| :--- | :--- | :--- |
| **标签** | `<root>/.tmsu/db` | TMSU 数据库，SQLite 格式 |
| 目录树展开状态 | `~/.config/tmsu-studio/state.json` | 界面状态，不入数据库 |
| 最近打开的 DB | 同上 | 启动时供选择 |
| 查询历史 | 同上 | 按 DB 分别保存 |
| **智能集合** | 同上 | 保存的查询链，按 DB 分别存储 |
| 缩略图缓存 | `~/.cache/tmsu-studio/thumbs/` | key = md5(path + mtime) |

**标签是唯一持久化的数据。** 删掉配置目录和缓存目录不影响任何标签，只是要重新展开目录树、重新抓缩略图、重新建立集合。

### 备份

```bash
# 备份标签数据库
cp -r ~/files/.tmsu ~/backup/tmsu-files-$(date +%F)

# 备份集合和界面配置
cp ~/.config/tmsu-studio/state.json ~/backup/

# 或使用 SQLite 在线备份
sqlite3 ~/files/.tmsu/db ".backup '/backup/tmsu-db.sqlite'"
```

---

## 常见问题

**Q: 启动后列表为空？**

A: 当前目录（或其父目录）没有 `.tmsu`。启动时会弹出选择/初始化对话框，或用 `TMSU_ROOT` 显式指定：

```bash
TMSU_ROOT=~/files tmsu-studio
```

**Q: 提示“未检测到 tmsu 命令”？**

A: TMSU 是本项目的外部依赖，需要单独安装。运行 `./install_tmsu.sh` 或手动编译。Ubuntu 官方仓库没有 `tmsu` 包。

**Q: 视频缩略图很慢？**

A: 首次抓帧慢，之后走缓存。缓存 key 是 `md5(path + mtime)`，文件变了会自动重抓。**生成过程是异步的，UI 不会冻结。**

**Q: 分面为什么有时显示“计算中…”？**

A: 分面分两批异步计算。快批（类型/年份）毫秒级返回，慢批（标签）需要为每个文件调 `tmsu tags`，秒级返回。先显示快分面，慢分面到达后追加。

**Q: 拖到剪辑软件没反应？**

A: 确认拖到的是媒体池或时间线。文件路径必须是绝对路径（本项目已保证）。

**Q: 文件移动后标签丢了？**

A: 到数据库根目录执行：

```bash
cd ~/files
tmsu repair
```

TMSU 会尝试根据文件名匹配新位置。如果失败，需要重新打标签。

**Q: 想给目录打标签？**

A: 不支持，也不应该。目录是文件系统结构，标签是数据库字段，两者正交。

**Q: 标签里出现了文件路径？**

A: 这是 TMSU 对未索引文件的回显。本项目已过滤。如果仍出现，说明该文件在当前 DB 中确实没有标签记录。

**Q: 切换数据库时提示“没有 .tmsu 目录”？**

A: 已修复。现在会智能向上查找最近的 `.tmsu`。如果整个路径链上都没有，会弹出提示。

**Q: 智能集合丢失？**

A: 集合存储在 `~/.config/tmsu-studio/state.json`，按 DB 分别保存。如果文件被删，集合会丢失，但**标签不受影响**。定期备份该文件。

**Q: 打完标签后光标跳到第一个文件？**

A: 已修复。刷新列表时会保留原选中状态、当前项和滚动位置。

**Q: 桌面图标点击没反应？**

A: 用终端手动跑一次 `~/.local/bin/tmsu-studio`，看是否有报错。如果手动能启动而桌面不行，临时把 desktop 文件的 `Terminal=false` 改成 `true`，再点一次看报错。

**Q: 输入查询时没有补全提示？**

A: 补全数据来自当前 DB 的标签列表。空 DB 或未打标签时补全列表为空，属正常。检查 `.tmsu/db` 是否真的有标签：

```bash
cd ~/files
tmsu tags
```

---

## 故障排除

### 查看启动日志

```bash
# 直接用终端启动
~/.local/bin/tmsu-studio

# 或用 gio 启动 desktop 文件，错误直接打屏
gio launch ~/.local/share/applications/tmsu-studio.desktop
```

### 检查依赖

```bash
tmsu --version         # 应有版本号
ffmpeg -version        # 应有版本号
exiftool -ver          # 应有版本号
```

### 重新安装本项目

```bash
cd /path/to/tmsu-studio       # 换成你的项目实际路径
rm -rf .venv
./install.sh
```

### 重新编译 TMSU（外部依赖）

```bash
cd /path/to/tmsu-studio       # 换成你的项目实际路径
./install_tmsu.sh
```

或手动（在项目根目录下执行）：

```bash
cd TMSU
export GOPROXY=https://goproxy.cn,direct
go mod tidy
go build -o bin/tmsu .
sudo install -m 0755 bin/tmsu /usr/local/bin/tmsu
```

常见原因：

- 缺少 `build-essential`（cgo 需要 gcc）
- Go 版本过低（需要 1.18+）
- 网络问题（`GOPROXY` 未设置或失效）

### 重置配置（不影响标签）

```bash
rm -rf ~/.config/tmsu-studio
rm -rf ~/.cache/tmsu-studio
```

---

## 相关项目

- [TMSU](https://github.com/oniony/TMSU) — 标签存储引擎（**外部依赖，克隆到本地 `TMSU/` 目录用于编译，非本项目代码**）
- [PyQt6](https://www.riverbankcomputing.com/software/pyqt/) — GUI 框架
- [FFmpeg](https://ffmpeg.org/) — 视频处理
- [ExifTool](https://exiftool.org/) — 图片元数据

---

## 许可

本项目采用 **GNU General Public License v3.0** 发布。

```
Copyright (C) 2026 FGwsz

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
```

完整许可文本见 [LICENSE](LICENSE)。

### 为什么是 GPL-3.0

本项目使用 **PyQt6**，它采用 GPL-3.0 / 商业双许可。由于 GPL 的传染性，**任何链接 PyQt6 的软件都必须以 GPL-3.0 兼容的许可证发布**。因此本项目也采用 GPL-3.0。

如果希望以 MIT 等宽松许可发布，需改用 **PySide6**（Qt 官方绑定，LGPL）。

### 第三方依赖许可

| 依赖 | 许可 | 与本项目的关系 |
| :--- | :--- | :--- |
| [TMSU](https://github.com/oniony/TMSU) | GPL-3.0 | 独立运行的外部命令，通过 subprocess 调用，不链接 |
| [PyQt6](https://www.riverbankcomputing.com/software/pyqt/) | GPL-3.0 / 商业 | **链接式依赖，决定本项目许可** |
| [FFmpeg](https://ffmpeg.org/) | LGPL / GPL | 独立运行的外部命令 |
| [ExifTool](https://exiftool.org/) | Artistic / GPL | 独立运行的外部命令 |
