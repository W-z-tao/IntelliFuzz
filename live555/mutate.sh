#!/bin/bash

# 指定要进行变异的文件夹的绝对路径
input_folder="$1"

# 检查输入文件夹是否存在
if [ ! -d "$input_folder" ]; then
    echo "Error: Input folder does not exist: $input_folder"
    exit 1
fi

# 初始化变量，用来记录是否处理了文件
processed_files=0

# 遍历文件夹中的所有 .bin 文件
for file in "$input_folder"/*.bin; do
    # 检查文件是否存在
    if [ -f "$file" ]; then
        # 检查文件大小是否为0
        if [ ! -s "$file" ]; then
            # 如果文件大小为0，则写入一个字节
            echo -n -e "\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01" > "$file"
        elif [ $(stat -c %s "$file") -gt 1024 ]; then
            # 如果文件大小超过1KB，则重新写入一个字节
            echo -n -e "\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01" > "$file"
        fi
        # 使用 radamsa 进行变异并保存到临时文件中
        radamsa "$file" > "$file.tmp" && mv "$file.tmp" "$file"
        # 标记已处理文件
        processed_files=1
    fi
done

# 检查是否处理了任何文件
if [ $processed_files -eq 0 ]; then
    echo "No .bin files found in folder: $input_folder"
    exit 1
fi
