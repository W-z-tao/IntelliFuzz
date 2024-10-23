import socket
import re
import time
import queue
import psutil
import signal
import os
import subprocess
import random
import threading

# 设置目标服务器的IP地址和端口
target_ip = "127.0.0.1"
temporary_port = 1234
supervise_flag = True
slave_id = 0
afl_id = 0
true_reward = 0
afl_queue_folder_path = 'fuzz_out/main/queue/'
Regions_cover = Functions_Executed = Lines_cover = '0%'
cov_num = 0
q = queue.Queue()
q_flag = False
afl_id_semaphore = threading.Semaphore(1)
supervise_flag_semaphore = threading.Semaphore(2)
def find_process_listening_on_port(port):
    for proc in psutil.process_iter(['pid', 'name', 'connections']):
        try:
            for conn in proc.connections():
                if conn.laddr.port == port:
                    return proc.pid
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            pass
    return None

def send_signal_to_process(pid, signal=signal.SIGUSR1):
    """向指定的进程发送信号."""
    try:
        os.kill(pid, signal)
    except OSError as error:
        pass


def compare_percentages(pct1, pct2):
    # Convert percentage strings to float numbers
    num1 = float(pct1.rstrip('%'))
    num2 = float(pct2.rstrip('%'))
    return num2 - num1


def check_good_seed(file_path=None, content=None, flag=0):
    global Regions_cover, Functions_Executed, Lines_cover, cov_num, temporary_port
    profdata_id = random.randint(1, 100000)
    env = os.environ.copy()
    new_profaw_file = f"get_cov/profraw/cov:{cov_num}.profraw"
    env['LLVM_PROFILE_FILE'] = new_profaw_file
    process = subprocess.Popen(f'./live555-cov/testProgs/testOnDemandRTSPServer {temporary_port}',
                               stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, env=env, shell=True)

    now_time =time.time()
    while True:
        children = psutil.Process(process.pid).children()
        if children:
            break
        else:
            #print("无法获取启动的服务器的 PID")
            if time.time()-now_time >= 0.5:
                _, stderr = process.communicate()
                print(stderr.decode())
                print('重启')
                process_1 = subprocess.run(f'netstat -tulnp | grep {temporary_port}',stdout=subprocess.PIPE,shell=True)
                stdout = process_1.stdout
                print(stdout.decode())
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                #subprocess.run(f'sudo lsof -ti:{temporary_port} | xargs sudo kill -9', shell=True)
                return 0

    #pid = find_process_listening_on_port(temporary_port)
    pid = children[0].pid
    # 创建一个 socket 对象
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((target_ip, temporary_port))

        if flag == 0:
            # 打开文件，读取内容，然后发送
            with open(file_path, 'rb') as file:
                file_content = file.read()
                s.sendall(file_content)
        elif flag == 1:
            s.sendall(content)

    send_signal_to_process(pid)
    while process.poll() is None:
        pass
    # send_signal_to_process(pid, signal.SIGINT)
    process.terminate()

    subprocess.run(f'llvm-profdata merge -sparse -o get_cov/{profdata_id}.profdata get_cov/profraw/cov*.profraw', shell=True)

    report = subprocess.run(
        f'llvm-cov report -instr-profile=get_cov/{profdata_id}.profdata ./live555-cov/testProgs/testOnDemandRTSPServer',
        stdout=subprocess.PIPE, shell=True, text=True)
    # 使用正则表达式匹配最后一行中的百分比
    pattern = r'(\d+\.\d+%)'
    # 使用 re.findall 找到所有匹配的百分比数字
    matches = re.findall(pattern, report.stdout)
    percentages = matches[-3:]
    # 如果有匹配的，那么它们应该是最后一行的百分数
    true_reward = compare_percentages(Regions_cover, percentages[0])
    if (true_reward > 0):
        Regions_cover = percentages[0]
        Functions_Executed = percentages[1]
        Lines_cover = percentages[2]
        os.remove(f'get_cov/{profdata_id}.profdata')
        cov_num = cov_num + 1
        #print(f"{float(Regions_cover.strip('%'))}",Functions_Executed,Lines_cover)
        #print(percentages)  # 这应该会打印类似于 ['0.69%', '1.95%', '0.89%'] 的列表
        return True, true_reward, percentages
    else:
        os.remove(f'get_cov/{profdata_id}.profdata')
        return False,

def get_max_id(folder_path):
    max_id = -1
    id_pattern = re.compile(r'id:(\d+)')

    for filename in os.listdir(folder_path):
        matches = id_pattern.findall(filename)
        if matches:
            current_id = int(matches[0])
            if current_id > max_id:
                max_id = current_id

    return max_id


def get_file_path_by_id(folder_path, file_id):
    id_pattern = re.compile(rf'id:{file_id:06}')

    for filename in os.listdir(folder_path):
        if id_pattern.search(filename):
            return os.path.abspath(os.path.join(folder_path, filename))
    return None

def supervise_afl_queue():
    global afl_id, true_reward, supervise_flag, q, q_flag
    true_reward = 0
    q_flag = False

    t_1 = threading.Thread(target=queue_handler)
    t_1.start()
    while True:
        supervise_flag_semaphore.acquire()
        if supervise_flag:
            supervise_flag_semaphore.release()
            file_path = get_file_path_by_id(afl_queue_folder_path, afl_id)
            if file_path is None:
                continue
            else:
                q.put(file_path)
                afl_id_semaphore.acquire()
                afl_id += 1
                afl_id_semaphore.release()
        else:
            supervise_flag_semaphore.release()
            break
    t_1.join()



def queue_handler():
    global q, true_reward, q_flag
    while True:
        if q.empty():
            supervise_flag_semaphore.acquire()
            if not supervise_flag:
                supervise_flag_semaphore.release()
                q_flag = True
                break
            else:
                supervise_flag_semaphore.release()
                continue
        else:
            file = q.get()
            print(f'!!!!!!!!!!!!{file}     队列{q.qsize()}')
            judge= check_good_seed(file)
            if judge == 0:
                q.put(file)
                continue
            if judge[0] == True:
                true_reward = true_reward + judge[1]

