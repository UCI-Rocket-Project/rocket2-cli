import socket
import time
import struct
import select

GSE_DATA_STRUCT_FORMAT = 'I???ffffffffffffff'
GSE_COMMAND_TUPLE_FORMAT = [
    'igniter0Fire',
    'igniter1Fire',
    'alarm',
    'solenoidStateGn2Fill',
    'solenoidStateGn2Vent',
    'solenoidStateMvasFill',
    'solenoidStateMvasVent',
    'solenoidStateMvas',
    'solenoidStateLoxFill',
    'solenoidStateLoxVent',
    'solenoidStateLngFill',
    'solenoidStateLngVent',
    'crc'
]
GSE_COMMAND_STRUCT_FORMAT = '????????????I'

if __name__ == '__main__':

    s = socket.create_server(("", 5001))
    clients = []
    read_list = [s]
    start = time.time_ns()
    try:
        while True:
            r, w, x = select.select(read_list, [], read_list, 0.01)
            r_socks = [cn for cn in clients  if cn.fileno() in r]
            removed = []
            for rs in r_socks:
                print("Recv data")
                try:
                    data = rs.recv(1024)
                except socket.error as e:
                    removed.append(rs)
                    continue
                res = struct.unpack(GSE_COMMAND_STRUCT_FORMAT, data)
                print(dict(zip(GSE_COMMAND_TUPLE_FORMAT, res)))
            for rs in removed:
                clients.pop(clients.index(rs))
                read_list.pop(read_list.index(rs.fileno()))

            for rs in r:
                if rs is s:
                    news,_ = rs.accept()
                    clients.append(news)
                    read_list.append(news.fileno())

            for xs in x:
                read_list.pop(read_list.index(xs))
                clients = [cn for cn in clients if cn.fileno() != xs]

            if time.time_ns() - start > 10**8:
                start = time.time_ns()
                removed = []
                for c in clients:
                    try:
                        c.send(struct.pack(GSE_DATA_STRUCT_FORMAT, 
                        int(time.time()),
                        True,
                        True,
                        True,
                        1.0,
                        2.0,
                        1.0,
                        2.0,
                        1.0,
                        2.0,
                        1.0,
                        2.0,
                        1.0,
                        2.0,
                        1.0,
                        2.0,
                        1.0,
                        2.0,
                        )
                        )
                    except IOError as io:
                        print("Failed to send msg")
                        removed.append(c)
                for rs in removed:
                    clients.pop(clients.index(rs))
                    read_list.pop(read_list.index(rs.fileno()))

    except KeyboardInterrupt as k:
        for c in clients:
            c.close()
        exit(0)


