#!/bin/bash
# TMSU 安装脚本 - 适用于 Ubuntu 22.04 (Go 1.18+)
# 项目地址：https://github.com/oniony/TMSU

# 1. 更新软件包列表并安装编译依赖
#    - golang: Go 语言编译器（TMSU 由 Go 编写）
#    - git: 用于克隆源码仓库
sudo apt update
sudo apt install -y golang git

# 2. 进入下载目录（可根据个人习惯修改，如 ~/Gitpro）
APP_DIR="$(cd "$(dirname "$0")" && pwd)"
cd $APP_DIR

# 3. 克隆 TMSU 官方仓库（完整分支）
git clone https://github.com/oniony/TMSU.git

# 4. 进入项目根目录
cd TMSU

# 5. 设置 Go 模块代理为国内高速镜像（goproxy.cn）
#    解决因网络问题导致的依赖包下载超时或 404 错误
export GOPROXY=https://goproxy.cn,direct

# 6. 固定依赖版本（关键！避免因新版不兼容导致编译失败）
#    - go-fuse@v1.0.0 : TMSU 使用的 FUSE 库版本
#    - go-sqlite3@v1.14.7 : 兼容 Go 1.18 及以下版本（更新版需要 Go 1.21+）
go get github.com/hanwen/go-fuse@v1.0.0
go get github.com/mattn/go-sqlite3@v1.14.7

# 7. 整理依赖关系，生成 go.sum 校验文件
go mod tidy

# 8. 编译主程序，输出到 bin/tmsu（自动创建 bin 目录）
#    注意：使用 "." 表示当前目录，因为 main.go 位于项目根目录
go build -o bin/tmsu .

# 9. 将编译好的二进制文件复制到系统路径（供全局调用）
sudo cp bin/tmsu /usr/bin/

# 10. 验证安装是否成功
tmsu --version
