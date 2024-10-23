from scapy.all import sniff, IP, TCP, Raw
import os
import re
import send
import queue
import threading
generator_port=8848
stop_flag = False
temp_reward = 0
true_reward = 0
last_request = ''
process_flag = False
q = queue.Queue(maxsize=50)
stop_flag_semaphore = threading.Semaphore(2)
process_flag_semaphore = threading.Semaphore(1)
next_semaphore = threading.Semaphore(0)
def save_rtsp_request_to_binary_file(data, filename):
    # 直接以二进制格式写入文件
    with open(filename, 'wb') as file:
        file.write(data)

def request_handler(packet):
    global generator_port, stop_flag,last_request, q, process_flag
    stop_flag_semaphore.acquire()
    if stop_flag:
        stop_flag_semaphore.release()
        exit()
    stop_flag_semaphore.release()
    if packet[IP].src == "127.0.0.1" and packet.haslayer(Raw) and packet[TCP].dport == generator_port:
        request_data = packet['Raw'].load
        if request_data == last_request:
            pass
        elif not q.full():
            q.put(request_data)#往队列里加请求包数据
            if not process_flag :
                process_flag_semaphore.acquire()
                process_flag = True
                process_flag_semaphore.release()
            last_request = request_data


def queue_handler():
    global q, stop_flag, true_reward, temp_reward, process_flag
    #print('开启抓包')
    while True:
        stop_flag_semaphore.acquire()
        if stop_flag:
            stop_flag_semaphore.release()
            q = queue.Queue()#清空队列
            break
        if q.empty():
            stop_flag_semaphore.release()
            process_flag_semaphore.acquire()
            if process_flag:
                next_semaphore.release()
            process_flag_semaphore.release()
            continue
        else:
            stop_flag_semaphore.release()
            request_data = q.queue[0]
            judge = send.check_good_seed(content=request_data, flag=1)
            if judge == 0:
                continue
            else:
                q.get()
            #print(f'!!!!!!!!!!!!队列{q.qsize()}')
            if judge[0]:
                save_rtsp_request_to_binary_file(request_data, 'fuzz_out/fake_slave/queue/id:{:06d}'.format(send.slave_id))
                send.slave_id = send.slave_id + 1
                temp_reward = judge[1]
                true_reward = temp_reward + true_reward

    #print('处理q结束')




def begin_capture():
    global generator_porta, stop_flag
    #print('启动抓包')
    t_1 = threading.Thread(target=queue_handler)
    t_1.start()
    while True:
        stop_flag_semaphore.acquire()
        if not stop_flag:
            stop_flag_semaphore.release()
            sniff(filter=f"tcp and port {generator_port}", prn=request_handler,iface='lo',store=False, timeout=0.5)
        else:
            stop_flag_semaphore.release()
            break
    t_1.join()



