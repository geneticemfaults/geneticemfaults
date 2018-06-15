from __future__ import print_function, division
import serial
from enum import Enum
import time
import struct
import numpy as np

try:     # Python 2
    from Tkinter import *
    bytes_fromhex = lambda h: h.decode("hex")
except:
    from tkinter import *
    bytes_fromhex = bytes.fromhex


class Axis(Enum):
    z = 0
    x = 1
    y = 2

class Command(Enum):
    ROR = 1     # extend
    ROL = 2     # contract
    MST = 3     # motor STOP
    MVP = 4     # move to position
                #  type is 0 for absolute (w.r.t. origin, which is reset on startup)
                #          1 for relative (w.r.t. current position)
                #          2 for stored coordinate
    SAP = 5     # set axis parameter
    GAP = 6     # get axis parameter

    GCO = 31    # get coordinate

class AxisParameter(Enum):
    target_pos  = 0
    actual_pos  = 1
    max_accel   = 5
    pos_reached = 8

class Point(object):
    def __init__(self, x, y, z):
        self.x = int(x)
        self.y = int(y)
        self.z = int(z)

    def as_array(self):
        return np.array((self.x, self.y, self.z))

    def __add__(self, p):
        assert type(p) is Point
        return Point(self.x+p.x, self.y+p.y, self.z+p.z)

    def __neg__(self):
        return Point(-self.x, -self.y, -self.z)

    def __sub__(self, p):
        assert type(p) is Point
        return self + (-p)

    def __mul__(self, p):
        if type(p) is Point:
            return Point(self.x*p.x, self.y*p.y, self.z*p.z)
        else:
            return Point(p*self.x, p*self.y, p*self.z)

    __rmul__ = __mul__
    __radd__ = __add__

    def __str__(self):
        #return "(x={},y={},z={})".format(self.x, self.y, self.z)
        return "({}, {}, {})".format(self.x, self.y, self.z)

class Reply(object):
    def __init__(self, reply):
        reply = bytearray(reply)
        self.reply_addr  = reply[0]
        self.module_addr = reply[1]
        self.status      = reply[2]
        self.cmd_number  = reply[3]
        self.value       = struct.unpack(">i", reply[4:8])[0]
        self.checksum    = reply[8]
        
        if self.checksum != sum(reply[:-1]) % 256:
            raise Exception("Invalid reply checksum!")

        self.ok = self.status == 100

class Request(object):
    def __init__(self, cmd, type, axis, value):

        self.cmdHex = hex(cmd.value)[2:].zfill(2)
        self.typeHex = hex(type)[2:].zfill(2)
        self.axisHex = hex(axis.value)[2:].zfill(2)
        value = (2**32+value)&0xFFFFFFFF
        self.valueHex = "%08x"%value

    def as_hex(self):
        command = '01' + self.cmdHex + self.typeHex + self.axisHex + self.valueHex
        checksum = "%02x" % (sum(bytearray(bytes_fromhex(command))) % 256)
        return command + checksum

    def as_bytes(self):
        return bytes_fromhex(self.as_hex())


class XYTable:

    ser = serial.Serial()

    # for the chip-coordinates,
    #  y-axis points down,
    #  x-axis points right
    origin = None    # NW corner
    xpoint = None    # NE corner
    ypoint = None    # SE corner
    # These must be set

    directions = {
        "left"     : (Axis.x, Command.ROR),   # -x
        "right"    : (Axis.x, Command.ROL),   # +x
        "forward"  : (Axis.y, Command.ROL),   # +y
        "backward" : (Axis.y, Command.ROR),   # -y
        "up"       : (Axis.z, Command.ROR),   # +z
        "down"     : (Axis.z, Command.ROL)    # -z
    }

    def __init__(self, points_file=None):
        if points_file:
            self.read_from_file(points_file)

    def set_origin(self):
        self.origin = self.get_position()

    def set_xpoint(self):
        self.xpoint = self.get_position()

    def set_ypoint(self):
        self.ypoint = self.get_position()

    def gen2coord(self, x, y):
        # We do a simple affine transformation:
        #     P = x*E1 + y*E2
        # where E1=(xpoint-origin) and E2=(ypoint-xpoint)
        #  are the basis vectors of the new vector space
        assert self.origin and self.xpoint and self.ypoint
        assert 0<=x<=1 and 0<=y<=1
        return x*(self.xpoint-self.origin) + y*(self.ypoint-self.xpoint) + self.origin

    def coord2gen(self, coord):
        # The transformation from point p0 (in tablespace) to p1 (in 01space)
        #  can be represented as:
        #     A*p0 + b = p1
        #  where the columns of A are the new basis vectors.
        #
        # This function does the inverse transformation:
        #     p0 = inv(A) * (p1 - b)
        #
        #  (That is, we first align the origins
        #   and then we invert the linear part)
        assert self.origin and self.xpoint and self.ypoint
        p1 = (coord - self.origin).as_array()
        
        xv = (self.xpoint - self.origin).as_array()
        yv = (self.ypoint - self.xpoint).as_array()
        #zv = np.cross(xv, yv); zv = zv/np.linalg.norm(zv)
        zv = np.array([0.0, 0.0, 1.0])        # any plane normal is OK

        A = np.vstack((xv, yv, zv)).T
        Ainv = np.linalg.inv(A)
        p0 = Ainv.dot(p1)
        assert p0[2] < 0.01, "Point not in plane!"
        return (p0[0], p0[1])


    def connect(self):
        self.ser.baudrate = 9600 #115200
        self.ser.port = 'COM1'
        self.ser.open()
        print('Connection is open: ' + str(self.ser.is_open))
        if self.ser.is_open:
            return True
        else:
            return False

    def disconnect(self):
        self.ser.close()
        if self.ser.is_open:
            print('Disconnect failed!')
            return False
        else:
            print('Connection closed!')
            return True

    def action(self, cmd, type, axis, value):

        req = Request(cmd, type, axis, value)
        self.ser.write(req.as_bytes())
        reply = Reply(self.ser.read(9))

        assert reply.ok, "Action failed!"
        return reply.value

    def move(self, direction, speed=10000, stop=False, sleeptime=1):
        if direction not in self.directions:
            raise Exception("{} is not a valid direction".format(direction))
        axis, cmd = self.directions[direction]

        self.action(cmd, 0, axis, value=speed)
        if stop:
            time.sleep(sleeptime)
            self.action(Command.MST, 0, axis, 0)

    def move_to_position(self, position):
        self.action(Command.MVP, 0, Axis.x, position.x)
        self.action(Command.MVP, 0, Axis.y, position.y)
        self.action(Command.MVP, 0, Axis.z, position.z)

    def get_position(self):
        """Returns the current position, in absolute coordinates"""
        xpos = self.action(Command.GAP, AxisParameter.actual_pos.value, Axis.x, 0)
        ypos = self.action(Command.GAP, AxisParameter.actual_pos.value, Axis.y, 0)
        zpos = self.action(Command.GAP, AxisParameter.actual_pos.value, Axis.z, 0)
        return Point(xpos, ypos, zpos)

    def wait(self):
        """Returns when target position has been reached"""
        while True:
            xstop = self.action(Command.GAP, AxisParameter.pos_reached.value, Axis.x, 0)
            ystop = self.action(Command.GAP, AxisParameter.pos_reached.value, Axis.y, 0)
            zstop = self.action(Command.GAP, AxisParameter.pos_reached.value, Axis.z, 0)
            if xstop and ystop and zstop:
                return
            
    def stop(self, direction=None):
        if direction:
            axis = self.directions[direction][0]
            self.action(Command.MST, 0, axis, 0)
        else:
            for axis in Axis:
                self.action(Command.MST, 0, axis, 0)
            #print("Stopped.")

    def read_from_file(self, points_file):
        p1, p2, p3 = [l.strip() for l in points_file.readlines()]
        self.origin = Point(*(p1.split(",")))
        self.xpoint = Point(*(p2.split(",")))
        self.ypoint = Point(*(p3.split(",")))

    def write_to_file(self, points_file):
        if self.origin and self.xpoint and self.ypoint:
            print("{},{},{}".format(self.origin.x, self.origin.y, self.origin.z), file=points_file)
            print("{},{},{}".format(self.xpoint.x, self.xpoint.y, self.xpoint.z), file=points_file)
            print("{},{},{}".format(self.ypoint.x, self.ypoint.y, self.ypoint.z), file=points_file)



if __name__ == "__main__":

    try:
        tab = XYTable()
        tab.connect()

        from gui import GUI
        interface = GUI(tab)
        interface.start()

        print(tab.get_position())
        
    except KeyboardInterrupt:
        print("Killed by KeyboardInterrupt")
    finally:
        tab.stop()
        tab.disconnect()
