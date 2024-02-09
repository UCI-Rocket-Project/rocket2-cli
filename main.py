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


