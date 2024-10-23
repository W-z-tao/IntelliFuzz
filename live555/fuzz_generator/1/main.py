import socket
import sys
# RTSP server details
host = '127.0.0.1'
port = 8848
stream_url = 'rtsp://192.168.75.145:8848/mp3AudioTest'  # Replace 'testStream' with the actual stream name
session = '000022B8'
target_directory = f'fuzz_generator/generator_{sys.argv[1]}/sure_parameter'
def read_rtsp_parameters(file_path):
    global para
    para = {'cseq':'', 'user_agent':'', 'transport':'', 'range':'', 'scale':'', 'speed':'', 'authorization':'', 'require':'', 'proxy_require':'', 'content_type':'', 'content_length':'', 'parameter_data':''}
    for key in para:
        with open(file_path+f'/{key}.bin', 'rb') as f:
            para[key] = f.read().rstrip()

read_rtsp_parameters(target_directory)

# Establish a TCP connection with the RTSP server
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect((host, port))
def send_rtsp_request(request):
    sock.sendall(request)


# OPTIONS request
options_request = f"OPTIONS {stream_url} RTSP/1.0\r\nCSeq: {para['cseq']}\r\nUser-Agent: {para['user_agent']}\r\nAuthorization: {para['authorization']}\r\n\r\n".encode()

# DESCRIBE request
describe_request = f"DESCRIBE {stream_url} RTSP/1.0\r\nCSeq: {para['cseq']}\r\nUser-Agent: {para['user_agent']}\r\nAccept: application/sdp\r\nAuthorization: {para['authorization']}\r\n\r\n".encode()

# SETUP request
setup_request = f"SETUP {stream_url}/track1 RTSP/1.0\r\nCSeq: {para['cseq']}\r\nUser-Agent: {para['user_agent']}\r\nTransport: {para['transport']}\r\nAuthorization: {para['authorization']}\r\n\r\n".encode()

# PLAY request
play_request = f"PLAY {stream_url} RTSP/1.0\r\nCSeq: {para['cseq']}\r\nUser-Agent: {para['user_agent']}\r\nSession: {session}\r\nRange: {para['range']}\r\nScale: {para['scale']}\r\nSpeed: {para['speed']}\r\nAuthorization: {para['authorization']}\r\n\r\n".encode()

# PAUSE request
pause_request = f"PAUSE {stream_url} RTSP/1.0\r\nCSeq: {para['cseq']}\r\nUser-Agent: {para['user_agent']}\r\nSession: {session}\r\nRange: {para['range']}\r\nAuthorization: {para['authorization']}\r\n\r\n".encode()

# GET_PARAMETER request
get_parameter_request = f"GET_PARAMETER {stream_url} RTSP/1.0\r\nCSeq: {para['cseq']}\r\nUser-Agent: {para['user_agent']}\r\nSession: {session}\r\nContent-Type: {para['content_type']}\r\nContent-Length: {para['content_length']}\r\nAuthorization: {para['authorization']}\r\n\r\n{para['parameter_data']}".encode()

# SET_PARAMETER request
set_parameter_request = f"SET_PARAMETER {stream_url} RTSP/1.0\r\nCSeq: {para['cseq']}\r\nUser-Agent: {para['user_agent']}\r\nSession: {session}\r\nContent-Type: {para['content_type']}\r\nContent-Length: {para['content_length']}\r\nAuthorization: {para['authorization']}\r\n\r\n{para['parameter_data']}".encode()

# TEARDOWN request
teardown_request = f"TEARDOWN {stream_url} RTSP/1.0\r\nCSeq: {para['cseq']}\r\nUser-Agent: {para['user_agent']}\r\nSession: {session}\r\nAuthorization: {para['authorization']}\r\n\r\n".encode()


send_rtsp_request(options_request+describe_request+setup_request+play_request+teardown_request)
sock.close()

