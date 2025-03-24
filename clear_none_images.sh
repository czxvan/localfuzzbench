#!/bin/bash
set -e

# 清理悬空镜像（dangling images）[1](@ref)
echo "正在清理悬空镜像..."
dangling_images=$(docker images -f "dangling=true" -q)
if [ -z "$dangling_images" ]; then
    echo "没有可清理的悬空镜像"
else
    docker rmi $dangling_images || echo "部分镜像删除失败（可能被容器引用）"
fi

# 清理<none>标签镜像[1,3](@ref)
echo "正在清理<none>标签镜像..."
none_images=$(docker images | grep "<none>" | awk '{print $3}')
if [ -z "$none_images" ]; then
    echo "没有可清理的<none>标签镜像"
else
    docker rmi $none_images || {
        echo "删除失败，可能原因："
        echo "1. 镜像被容器引用（需先删除相关容器）[1](@ref)"
        echo "2. 磁盘空间不足（建议先执行悬空镜像清理）[1](@ref)"
        exit 1
    }
fi

echo "清理完成！剩余镜像列表："
docker images