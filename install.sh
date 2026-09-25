#!/usr/bin/env bash
#
# TMSU Studio 安装脚本
#
# 功能：
#   1. 安装系统依赖
#   2. 编译安装 TMSU（若未安装）
#   3. 创建 Python 虚拟环境并安装依赖
#   4. 生成命令行启动脚本 ~/.local/bin/tmsu-studio
#   5. 生成桌面入口 ~/.local/share/applications/tmsu-studio.desktop
#
# 用法：
#   chmod +x install.sh
#   ./install.sh
#
set -euo pipefail

# ---------- 路径 ----------
APP_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV="$APP_DIR/.venv"
BIN_DIR="$HOME/.local/bin"
DESKTOP_DIR="$HOME/.local/share/applications"
DESKTOP_FILE="$DESKTOP_DIR/tmsu-studio.desktop"
LAUNCHER="$BIN_DIR/tmsu-studio"
TMSU_BUILD_DIR="${TMPDIR:-/tmp}/tmsu-build"

# ---------- 工具函数 ----------
info()  { echo "==> $*"; }
warn()  { echo "⚠  $*" >&2; }
error() { echo "✗  $*" >&2; exit 1; }

require_cmd() {
    command -v "$1" >/dev/null 2>&1 || error "缺少命令：$1"
}

# ---------- 1. 系统依赖 ----------
info "更新软件包列表"
sudo apt update

info "安装系统依赖"
sudo apt install -y \
    python3 python3-venv python3-pip \
    golang-go build-essential git \
    ffmpeg libimage-exiftool-perl xdg-utils

# ---------- 2. 安装 TMSU（如果未安装） ----------
if command -v tmsu >/dev/null 2>&1; then
    info "已检测到 TMSU：$(tmsu --version 2>&1 | head -n 1)"
else
    info "未检测到 TMSU，开始从源码编译安装"

    mkdir -p "$TMSU_BUILD_DIR"
    cd "$TMSU_BUILD_DIR"

    if [ ! -d TMSU ]; then
        info "克隆 TMSU 仓库"
        git clone https://github.com/oniony/TMSU.git
    fi

    cd TMSU

    info "配置 Go 模块代理"
    export GOPROXY=https://goproxy.cn,direct

    info "固定依赖版本"
    go get github.com/hanwen/go-fuse@v1.0.0
    go get github.com/mattn/go-sqlite3@v1.14.7
    go mod tidy

    info "编译 TMSU"
    go build -o bin/tmsu .

    info "安装到 /usr/local/bin"
    sudo install -m 0755 bin/tmsu /usr/local/bin/tmsu

    command -v tmsu >/dev/null 2>&1 || \
        error "TMSU 安装失败，请检查编译输出"

    info "TMSU 安装成功：$(tmsu --version 2>&1 | head -n 1)"
fi

# ---------- 3. Python 虚拟环境 ----------
info "创建 Python 虚拟环境"
cd "$APP_DIR"

if [ ! -d "$VENV" ]; then
    python3 -m venv "$VENV"
fi

"$VENV/bin/pip" install --upgrade pip
"$VENV/bin/pip" install -r "$APP_DIR/requirements.txt"

# ---------- 4. 命令行启动脚本 ----------
info "生成命令行启动脚本：$LAUNCHER"
mkdir -p "$BIN_DIR"

cat > "$LAUNCHER" <<EOF
#!/usr/bin/env bash
# 由 tmsu-studio install.sh 生成，请勿手动编辑
cd "$APP_DIR" || exit 1
exec "$VENV/bin/python" -m tmsu_studio "\$@"
EOF

chmod +x "$LAUNCHER"

# ---------- 5. 桌面入口 ----------
info "生成桌面入口：$DESKTOP_FILE"
mkdir -p "$DESKTOP_DIR"

cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Type=Application
Version=1.0
Name=TMSU Studio
GenericName=文件标签管理器
Comment=以文件为记录、标签为字段的文件数据库客户端
Exec="$LAUNCHER" %U
Path=$APP_DIR
Icon=folder-videos
Terminal=false
StartupNotify=true
Categories=Utility;FileTools;
Keywords=tmsu;tag;file;database;media;
EOF

chmod +x "$DESKTOP_FILE"

# 刷新 desktop 数据库
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true
fi

# ---------- 6. PATH 检查 ----------
if ! echo ":$PATH:" | grep -q ":$BIN_DIR:"; then
    warn "$BIN_DIR 不在 PATH 中"
    echo "   如需在终端直接使用 tmsu-studio，请把下面一行加入 ~/.bashrc："
    echo "   export PATH=\"\$HOME/.local/bin:\$PATH\""
    echo
fi

# ---------- 7. 完成 ----------
echo
echo "════════════════════════════════════════════"
echo "  TMSU Studio 安装完成"
echo "════════════════════════════════════════════"
echo
echo "  命令行启动   : $LAUNCHER"
echo "  桌面菜单     : TMSU Studio"
echo "  项目目录     : $APP_DIR"
echo
echo "  首次使用："
echo "    cd <你的素材目录>"
echo "    tmsu init"
echo "    tmsu-studio"
echo
echo "  或指定数据库根启动："
echo "    TMSU_ROOT=/path/to/root tmsu-studio"
echo
