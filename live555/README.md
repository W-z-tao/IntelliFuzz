fuzz_generator 文件夹中保存由LLM生成的5个不同的generator   它们各自发送的数据包构成一个典型的RTSP请求流程

fuzz_in 文件夹里是AFL初次运行提供的种子

fuzz_out 保存了AFL的输出(记得-M main)和伪造的同步文件夹fake_slave/queue

get_cov 保留了重放种子时候产生的profraw文件  该文件能够保存相关的代码覆盖率信息

capture_seed.py 是抓包脚本

main.py 是主程序  需管理员身份运行

matate.sh 用了radamsa变异工具变异generator需要的input 致使生成的种子不同

send.py 有一些函数的定义

重要：

1.live555下载安装可以查看https://github.com/profuzzbench/profuzzbench/tree/master/subjects/RTSP/Live555

2.还需使用llvm-cov对live555进行插装  得到live555-cov 构建重放模块

3.AFLplusplusnet https://github.com/zyingp/AFLplusplusnet

