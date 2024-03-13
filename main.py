#/usr/bin/env python3
import click
import threading
import sys
import select
import socket
import queue
import shlex

main_data_lock = threading.Lock()

main_thread_lock = threading.Lock()
main_thread = None
main_thread_end_evt = threading.Event()
main_state = None 

# OUr software is quite simmilar to mavporxy. We can study its code
# for proper error handling techniques for various compoenets that
# we use so that we can have higher quality code.
# We stole the idea about having 2 threads and their roles from there.

def shlex_quotes(value):
    '''see http://stackoverflow.com/questions/6868382/python-shlex-split-ignore-single-quotes'''
    lex = shlex.shlex(value)
    lex.quotes = '"'
    lex.whitespace_split = True
    lex.commenters = ''
    return list(lex)


def cmd_status(args):
    if len(args) != 0:
        print("No arguments necessary")
    # Print socket states

def cmd_input(args):
    #TODO: Am I accepting connections or is the ECU.
    # Assuming ECU is server.
    if args[0] == 'add':
        addr, port = args[1].split(':')
        c = socket.create_connection((addr, int(port)))
        main_state.conns.append(c)
        main_state.read_fds.append(c.fileno())
        return  True

def cmd_output(args):
    if args[0] == 'add':
        addr, port = args[1].split(':')
        return True

def cmd_log(args):
    pass

def cmd_monitor(args):
    pass

# Refer:https://github.com/UCI-Rocket-Project/rocket2-overview?tab=readme-ov-file#gse-command-packet
GSE_COMMAND_TUPLE_FORMAT = ['igniterFire'
    ,'solenoidStateGn2Fill'
    ,'solenoidStateGn2Vent'
    ,'solenoidStateMvasFill'
    ,'solenoidStateMvasVent'
    ,'solenoidStateMvas'
    ,'solenoidStateLoxFill'
    ,'solenoidStateLoxVent'
    ,'solenoidStateLngFill'
    ,'solenoidStateLngVent'
]

#Refer: https://github.com/UCI-Rocket-Project/rocket2-overview?tab=readme-ov-file#ecu-command-packet
ECU_COMMAND_TUPLE_FORMAT = [
    'solenoidStateGn2Vent',
    'solenoidStatePv1',
    'solenoidStatePv2',
    'solenoidStateVent'
]
def cmd_command(args):
    if args[0] == 'gse':
        if args[1] == 'setall':
            values = [int(x) for x in args[2].split(',')]
            if len(values) != 10:
                print("Too many or too few arguments in:", values)
            data = struct.pack('??????????', *values)
            for f in main_state.write_fds:
                for c in main_state.conns:
                    if c.fileno() == f:
                        c.send(data)
        elif args[1] == 'set':
            # Need to track/query state to implement this otherwise all others will
            # be reset
            k,v = args[2].split('=')
            try:
                idx = GSE_COMMAND_TUPLE_FORMAT.index(k)
            except ValueError:
                print(f"Could not find field {k}")
            values = 


    elif args[0] == 'ecu':
        if args[1] == 'setall':
            values = [int(x) for x in args[2].split(',')]
            if len(values) != 4:
                print("Too many or too few arguments in:", values)
            data = struct.pack('????', *values)
            for f in main_state.write_fds:
                for c in main_state.conns:
                    if c.fileno() == f:
                        c.send(data)





class MainState:
    def __init__(self):
        self.conns = []
        self.read_fds = []
        self.write_fds = []
        self.input_queue = queue.Queue()
        self.command_map = {
            "help" : (None, "Gives help"),
            "status" : (cmd_status,"Provides status of the connections"),
            "input" : (cmd_input, "Manage input connections for telemetry data"),
            "output" : (cmd_output, "Manage output connections for commands"),
            "log" : (cmd_log, "Log specific selected messages to a file"),
            "monitor" : (cmd_monitor, "Monitor specific selected messages by outputting to stdout")
            "command" : (cmd_command, "Send command")
        }


    def process_input(self, inp):
        try:
            args = shlex_quotes(inp)
        except Exception as e:
            print("Caught shlex exception: %s" % e.message);
            return
        if args[0] not in self.command_map.keys():
            print(f"ERROR in command: {inp}")
        cmd = args[0]
        if cmd == 'help':
            k = self.command_map.keys()
            k = sorted(k)
            for cmd in k:
                (fn, help) = self.command_map[cmd]
                print("%-15s : %s" % (cmd, help))
            return
        fn, help_text = self.command_map[cmd]
        fn(args[1:])



def close_process(exctype, value, traceback):
    print("Closing")
    main_thread_end_evt.set()
    main_thread.join(2)
    if main_data_lock.locked():
        main_data_lock.release()
    sys.__excepthook__(exctype, value, traceback)

def process_telem(conn):
    # Helpful reference code for connection handling
    # https://github.com/ArduPilot/pymavlink/blob/f7a2f29607f7f2a72499a3fc19e555aaace51ba8/mavutil.py#L1217
    d = conn.recv(1024)
    if len(d) == 0:
        print("EOF on TCP socket")
        main_state.conns.pop(main_state.conns.index(conn))
        return None, False
    else:
        return d, True
    

def main_thread():
    while True:
        if main_thread_end_evt.is_set():
            for conn in main_state.conns:
                conn.close()
            try:
                main_data_lock.release()
            except RuntimeError:
                pass
        while not main_state.input_queue.empty():
            inp = main_state.input_queue.get(block=False)
            main_state.process_input(inp)
        r_ready = []
        w_ready = []
        try:
            # How to use select?
            # https://github.com/ArduPilot/MAVProxy/blob/e2b03aab02775cad6214990c213ad023800f2112/MAVProxy/mavproxy.py#L1127
            r_ready, w_ready, _ = select.select(
                main_state.read_fds, 
                main_state.write_fds, 
                [], 1)
        except select.error as se:
            print("Select error: ", se)
            continue

        for fd in r_ready:
            for c in main_state.conns:
                if c.fileno() == fd:
                    data, status = process_telem(c)
                    if not status:
                        main_state.read_fds = [s.fileno() for s in main_state.conns]
                    else:
                        print(data)

@click.command()
def main():
    global main_state
    main_state = MainState()
    global main_thread
    main_thread = threading.Thread(target=main_thread)
    main_thread.start()
    sys.excepthook = close_process
    while True:
        cmd = input('>')
        main_state.input_queue.put(cmd.rstrip())




if __name__ == '__main__':
    print("Welcome to UCIRP CLI")
    main()


