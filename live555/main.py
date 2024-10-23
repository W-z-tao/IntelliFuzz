import time
import os
import psutil
import numpy
import subprocess
import signal
from SMPyBandits.Policies import *
from tqdm import tqdm
import send
import capture_seed
import threading
import shutil


# 第一层有2个选择（臂）
num_arms1 = 2
# 第二层选择（臂）
num_arms2 = 5
policy1 = Exp3(num_arms1, gamma=0.2)
policy2 = Exp3(num_arms2, gamma=0.2)
# 初始化各个边的执行次数为0
times_2 = numpy.zeros(num_arms2)
# 初始化各个边的reward为0
reward_1 = numpy.zeros(num_arms1)
reward_2 = numpy.zeros(num_arms2)
# 初始给予 0 reward
for i, d in zip(range(num_arms1), reward_1):
    policy1.getReward(i, d)
for i, d in zip(range(num_arms2), reward_2):
    policy2.getReward(i, d)

afl_port = 8888
generator_path = "fuzz_generator"
time_slice = 30 #每轮时间片大小
para = {'cseq': '', 'user_agent': '', 'transport': '', 'range': '', 'scale': '', 'speed': '', 'authorization': '',
            'require': '', 'proxy_require': '', 'content_type': '', 'content_length': '', 'parameter_data': ''}
capture_seed.generator_port = 8848
used_reward_1 = used_reward_2 = 0.00001
ave_reward_1 = reward_count_1 = ave_reward_2 = reward_count_2 =0
alpha = 0.2
reward_update_count = 50
run_time = 60*60*24
warm_up_time = 60*5
seed_folder_id = [0 for _ in range(num_arms2)]
good_seed_flag = [False for _ in range(num_arms2)]
attempt_time = [1 for _ in range(num_arms2)]
array = [[] for _ in range(num_arms2)]
real_time = [0 for _ in range(num_arms2)]

afl_command = ['/home/ygtt/AFLplusplusnet/afl-fuzz',
                           '-P',
                           f'0:{afl_port}',
                           '-o',
                           'fuzz_out',
                           '-i',
                           'fuzz_in',
                           '-H',
                           '1:1000:10:1000:10000:10:10:0',
                           '-M',
                           'main',
                           '--',
                           './live555/testProgs/testOnDemandRTSPServer',
                           f'{afl_port}']
afl_process = subprocess.Popen(afl_command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(5)#先运行5s
# 暂停挂起这个子进程
os.kill(afl_process.pid, signal.SIGSTOP)
#运行目标服务器
server_process = subprocess.Popen(f'./live555/testProgs/testOnDemandRTSPServer {capture_seed.generator_port}', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

start_time = time.time()
min_num = 0

for _ in tqdm(range(10000)):
    print(f"目前覆盖率{send.Regions_cover}")
    if time.time() - start_time >= run_time:#到运行时间就暂停
        break
    if time.time() -start_time >= warm_up_time:
        min_num = 1
    # 第一层进行选择
    c1 = policy1.choice()
    # 选择afl-fuzz
    if c1 == 0:
        print('运行afl-fuzz!!!')
        send.supervise_flag = True
        t_1 = threading.Thread(target=send.supervise_afl_queue)
        t_1.start()
        # 重新启动afl-fuzz
        os.kill(afl_process.pid, signal.SIGUSR2)
        os.kill(afl_process.pid, signal.SIGCONT)
        # 运行一段时间
        time.sleep(time_slice)
        # 暂停挂起这个子进程
        os.kill(afl_process.pid, signal.SIGSTOP)
        max_afl_id = send.get_max_id(send.afl_queue_folder_path)
        while True:#确保重放完所有queue中的种子
            send.afl_id_semaphore.acquire()
            if max_afl_id == send.afl_id-1:
                send.afl_id_semaphore.release()
                for _ in range(2):
                    send.supervise_flag_semaphore.acquire()
                send.supervise_flag = False
                for _ in range(2):
                    send.supervise_flag_semaphore.release()
                t_1.join()
                break
            else:
                send.afl_id_semaphore.release()
                continue
        print(send.true_reward)
        if send.true_reward > 0:
            reward_count_1 = reward_count_1+1
            ave_reward = ave_reward_1*alpha+(1-alpha)*send.true_reward
            if reward_count_1 % reward_update_count == 0:
                used_reward = ave_reward
        policy1.getReward(c1, min(send.true_reward/used_reward_1, 1, min_num)/2)

    elif c1 == 1:
        c2 = policy2.choice()
        print(f'运行generator_{c2+1}!!!')
        #开启抓包
        capture_seed.stop_flag = False
        # 创建一个线程，目标函数是捕获函数
        t_2 = threading.Thread(target=capture_seed.begin_capture)
        # 启动线程
        t_2.start()
        time.sleep(0.2)
        directory_1 = f'fuzz_generator/generator_{c2+1}/sure_parameter'
        directory_2 = f'fuzz_generator/generator_{c2+1}/parameter'
        generator_start_time = time.time()

        while time.time()-generator_start_time < time_slice :
            #开启对应的generator
            if good_seed_flag[c2]:
                attempt_time[c2] = 1
                array[c2] = []
                real_time[c2] = 0
                good_seed_flag[c2] = False
            if seed_folder_id[c2] != 0 and real_time[c2] == 0:
                if len(array[c2]) == 0:
                    array[c2] = [i for i in range(seed_folder_id[c2])]
                    attempt_time[c2] = attempt_time[c2]*2
                real_time[c2] = attempt_time[c2]
                random_value = numpy.random.choice(array[c2])
                array[c2].remove(random_value)
                if os.path.exists(directory_1):# 删除文件夹
                    shutil.rmtree(directory_1)
                subprocess.run(f'cp -r {directory_2}/{random_value} {directory_1}', shell=True)
            result= subprocess.run(f'timeout -s SIGTERM 0.2 python3 ./{generator_path}/generator_{c2+1}/fuzz_generator.py {c2+1}', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)#
            if result.returncode == 124:#超时退出
                children = psutil.Process(server_process.pid).children()
                pid = children[0].pid
                os.kill(pid, signal.SIGTERM)
                server_process.terminate()
                server_process = subprocess.Popen(
                    f'./live555/testProgs/testOnDemandRTSPServer {capture_seed.generator_port}', shell=True,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if seed_folder_id[c2] != 0:
                real_time[c2] = real_time[c2] -1
            capture_seed.next_semaphore.acquire(timeout=0.5)#处理完本次发送的种子
            if capture_seed.temp_reward > 0:
                subprocess.run(f'mv fuzz_generator/generator_{c2+1}/sure_parameter fuzz_generator/generator_{c2+1}/parameter/{seed_folder_id[c2]}', shell=True)#保存有效generator的seed
                seed_folder_id[c2] = seed_folder_id[c2]+1
                good_seed_flag[c2] = True
                capture_seed.temp_reward = 0
            subprocess.run(f'sh mutate.sh fuzz_generator/generator_{c2+1}/sure_parameter', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)#启动shell脚本变异
        # 关闭抓包
        for _ in range(2):
            capture_seed.stop_flag_semaphore.acquire()
        capture_seed.stop_flag = True
        for _ in range(2):
            capture_seed.stop_flag_semaphore.release()
        t_2.join()
        print(capture_seed.true_reward)
        if capture_seed.true_reward > 0:
            reward_count_1 = reward_count_1+1
            reward_count_2 = reward_count_2+1
            ave_reward_1 = ave_reward_1*alpha+(1-alpha)*capture_seed.true_reward
            ave_reward_2 = ave_reward_2 * alpha + (1 - alpha) * capture_seed.true_reward
            if reward_count_1 % reward_update_count == 0:
                used_reward_1 = ave_reward_1
            if reward_count_2 % reward_update_count == 0:
                used_reward_2 = ave_reward_2
        policy1.getReward(c1, min(capture_seed.true_reward / used_reward_1, 1, min_num) / 2)
        policy2.getReward(c2, min(capture_seed.true_reward / used_reward_2, 1, min_num) / 2)
        capture_seed.true_reward = 0


children = psutil.Process(server_process.pid).children()
pid = children[0].pid
os.kill(pid, signal.SIGTERM)
server_process.terminate()










