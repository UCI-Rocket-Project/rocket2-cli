#/usr/bin/env python3
import click
import threading
import sys
import select
import socket
import queue
import shlex
import struct

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
        try:
            t = args[2].trim()
        except IndexError as e:
            t = 'gse'
        c = socket.create_connection((addr, int(port)))
        main_state.conns.append((c, {'type':t}))
        main_state.read_fds.append(c.fileno())
        return  True

def cmd_output(args):
    if args[0] == 'add':
        addr, port = args[1].split(':')
        try:
            t = args[2].trim()
        except IndexError as e:
            t = 'gse'
        c = socket.create_connection((addr, int(port)))
        main_state.conns.append((c, {'type':t}))
        main_state.write_fds.append(c.fileno())
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
'''
struct gseData {
    uint32_t timestamp;
    bool igniterArmed;
    bool igniter1Continuity;
    bool igniter2Continuity;
    float supplyVoltage1;
    float supplyVoltage2;
    float solenoidCurrentGn2Fill;
    float solenoidCurrentGn2Vent;
    float solenoidCurrentMvasFill;
    float solenoidCurrentMvasVent;
    float solenoidCurrentMvas;
    float solenoidCurrentLoxFill;
    float solenoidCurrentLoxVent;
    float solenoidCurrentLngFill;
    float solenoidCurrentLngVent;
    float temperatureLox;
    float temperatureLng;
    float pressureGn2;
};
'''
GSE_DATA_STRUCT_FORMAT = 'I???ffffffffffffff'
GSE_DATA_TUPLE_FORMAT = [
    'timestamp',
    'igniterArmed',
    'igniter1Continuity',
    'igniter2Continuity',
    'supplyVoltage1',
    'supplyVoltage2',
    'solenoidCurrentGn2Fill',
    'solenoidCurrentGn2Vent',
    'solenoidCurrentMvasFill',
    'solenoidCurrentMvasVent',
    'solenoidCurrentMvas',
    'solenoidCurrentLoxFill',
    'solenoidCurrentLoxVent',
    'solenoidCurrentLngFill',
    'solenoidCurrentLngVent',
    'temperatureLox',
    'temperatureLng',
    'pressureGn2'
]
'''
struct ecuData {
    uint32_t timestamp;
    float packetRssi;
    float packetLoss;
    float supplyVoltage;
    float batteryVoltage;
    float solenoidCurrentCopvVent;
    float solenoidCurrentPv1;
    float solenoidCurrentPv2;
    float solenoidCurrentVent;
    float temperatureCopv;
    float pressureCopv;
    float pressureLox;
    float pressureLng;
    float pressureInjectorLox;
    float pressureInjectorLng;
    float angularVelocityX;
    float angularVelocityY;
    float angularVelocityZ;
    float accelerationX;
    float accelerationY;
    float accelerationZ;
    float magneticFieldX;
    float magneticFieldY;
    float magneticFieldZ;
    float temperature;
    float altitude;
    float ecefPositionX;
    float ecefPositionY;
    float ecefPositionZ;
    float ecefPositionAccuracy;
    float ecefVelocityX;
    float ecefVelocityY;
    float ecefVelocityZ;
    float ecefVelocityAccuracy;
};
'''
ECU_DATA_STRUCT_FORMAT = 'Ifffffffffffffffffffffffffffffffff'
ECU_DATA_TUPLE_FORMAT = [
    'timestamp',
    'packetRssi',
    'packetLoss',
    'supplyVoltage',
    'batteryVoltage',
    'solenoidCurrentCopvVent',
    'solenoidCurrentPv1',
    'solenoidCurrentPv2',
    'solenoidCurrentVent',
    'temperatureCopv',
    'pressureCopv',
    'pressureLox',
    'pressureLng',
    'pressureInjectorLox',
    'pressureInjectorLng',
    'angularVelocityX',
    'angularVelocityY',
    'angularVelocityZ',
    'accelerationX',
    'accelerationY',
    'accelerationZ',
    'magneticFieldX',
    'magneticFieldY',
    'magneticFieldZ',
    'temperature',
    'altitude',
    'ecefPositionX',
    'ecefPositionY',
    'ecefPositionZ',
    'ecefPositionAccuracy',
    'ecefVelocityX',
    'ecefVelocityY',
    'ecefVelocityZ',
    'ecefVelocityAccuracy'
]
'''
struct ecuCommand {
    bool solenoidStateCopvVent;
    bool solenoidStatePv1;
    bool solenoidStatePv2;
    bool solenoidStateVent;
    uint32_t crc;
};
'''
ECU_COMMAND_TUPLE_FORMAT = [
    'solenoidStateCopvVent',
    'solenoidStatePv1',
    'solenoidStatePv2',
    'solenoidStateVent',
    'crc'
]
ECU_COMMAND_STRUCT_FORMAT = '????I'
'''
struct gseCommand {
    bool igniter0Fire;
    bool igniter1Fire;
    bool alarm;
    bool solenoidStateGn2Fill;
    bool solenoidStateGn2Vent;
    bool solenoidStateMvasFill;
    bool solenoidStateMvasVent;
    bool solenoidStateMvas;
    bool solenoidStateLoxFill;
    bool solenoidStateLoxVent;
    bool solenoidStateLngFill;
    bool solenoidStateLngVent;
    uint32_t crc;
};
'''
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

def cmd_command(args):
    if args[0] == 'gse':
        if args[1] == 'setall':
            print("gse.setall")
            values = [int(x) for x in args[2].split(',')]
            if len(values) != 12:
                print("Too many or too few arguments in:", values)
            values.append(0)
            data = struct.pack(GSE_COMMAND_STRUCT_FORMAT, *values)
            for f in main_state.write_fds:
                for c,attrs in main_state.conns:
                    if c.fileno() == f and attrs['type'] == 'gse':
                        print("Sending")
                        c.send(data)
        elif args[1] == 'set':
            # Need to track/query state to implement this otherwise all others will
            # be reset
            k,v = args[2].split('=')
            try:
                idx = GSE_COMMAND_TUPLE_FORMAT.index(k)
            except ValueError:
                print(f"Could not find field {k}")
            # values = 


    elif args[0] == 'ecu':
        if args[1] == 'setall':
            values = [int(x) for x in args[2].split(',')]
            crc = 0
            values.append(crc)
            if len(values) != 4:
                print("Too many or too few arguments in:", values)
            data = struct.pack(ECU_COMMAND_STRUCT_FORMAT, *values)
            for f in main_state.write_fds:
                for c,attrs in main_state.conns:
                    if c.fileno() == f and attrs['type'] == 'ecu':
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
            "monitor" : (cmd_monitor, "Monitor specific selected messages by outputting to stdout"),
            "command" : (cmd_command, "Send command")
        }
        self.gse_values = dict()


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

def process_telem(conn, attrs):
    # Helpful reference code for connection handling
    # https://github.com/ArduPilot/pymavlink/blob/f7a2f29607f7f2a72499a3fc19e555aaace51ba8/mavutil.py#L1217
    d = conn.recv(1024)
    if len(d) == 0:
        print("EOF on TCP socket")

        for i, x in enumerate(main_state.conns):
            if x[0]== conn:
                break
        main_state.conns.pop(i)
        return None, False
    else:
        print("Recv'd len", len(d))
        print("Recv'd",d)
        if attrs['type'] == 'gse':
            try:
                v = struct.unpack(GSE_DATA_STRUCT_FORMAT, d)
            except struct.error as e:
                print("Failed to decode message")
                print(e)
            res = dict()
            for k,v in zip(GSE_DATA_TUPLE_FORMAT, v):
                res[k] = v
        return res, True
    

def main_thread():
    while True:
        if main_thread_end_evt.is_set():
            for conn,_ in main_state.conns:
                conn.close()
            try:
                main_data_lock.release()
            except RuntimeError:
                pass
            exit()

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
            for c,attrs in main_state.conns:
                if c.fileno() == fd:
                    data, status = process_telem(c, attrs)
                    print(data)
                    if attrs['type'] == 'gse':
                        main_state.gse_values = data
                    if not status:
                        main_state.read_fds = [s.fileno() for s,_ in main_state.conns]
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


