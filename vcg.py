from __future__ import print_function, division
import random
import serial
import time

STARTBYTE = bytearray(b"\x20")
RESPLEN   = 200
TIMEOUT   = 0.2

# -9.8 to 4.2


EVCG_TIMEOUT_COUNTER = 0

class VCG_ReadTimeout(Exception):
    """Raise when board doesn't respond"""
    pass

class VCG_BusyTimeout(Exception):
    """Raise when VCG gets stuck in evcg_busy()"""
    pass

class VCG(object):

    def __init__(self):

        from vcglitcher import (VCGlitcher, GLITCH_MODE, RST_SRC, EVCG_RST_POLARITY,
                                EVCG_TRIGGER_SRC, EVCG_TRIGGER_EDGE)

        self.vcg = VCGlitcher()
        # necessary for opening the VCGlitcher
        self.vcg.device_list()
        self.vcg.device_get_info(0)
        try:
            self.vcg.open()
            self.n_patterns = self.vcg.evcg_get_guaranteed_pattern_number()

            # use EMBEDDED_LASER, it seems to be the same thing as embedded EMFI (which is not present)
            self.vcg.set_mode(GLITCH_MODE.EMBEDDED_LASER)
            # we'll do our own resets (polarity is ignored here)
            self.vcg.smartcard_reset_config(RST_SRC.SW_RST, EVCG_RST_POLARITY.ACTIVE_HIGH)
            # set reset line voltage to 3.3V (i.e. power is on)
            self.vcg.set_smartcard_soft_reset(1)

            # Set Embedded Glitcher to be triggered by the "trigger in" input
            self.vcg.evcg_trigger_config(EVCG_TRIGGER_SRC.TRIGGER_IN, EVCG_TRIGGER_EDGE.RISING)
        

            self.ser = serial.Serial(port = "COM6", baudrate = 115200, parity = serial.PARITY_NONE,
                                     stopbits = serial.STOPBITS_ONE, bytesize = serial.EIGHTBITS,
                                     timeout=TIMEOUT)
            assert self.ser.isOpen()

        except Exception as e:
            print("Exception occured: " + str(e))
            raise e


    def __del__(self):
        if self.vcg:    self.vcg.close()
        if self.ser:    self.ser.close()


    def glitch(self, intensity, offset, repeat):
        """Does one glitch with specified intensity, offset, and repetitions.
        Returns the board response.
        Throws a "Timeout!" exception if it doesn't receive a response.
        """

        # flush any uncommited pattern sequences
        self.vcg.evcg_clear_pattern()

        # It's possible to add up to n_pattern glitch-patterns:
        self.vcg.evcg_add_glitch(offset, 40//2, repeat)        # duration must be 40ns
        self.set_intensity_level(intensity)

        # Play out the pattern:
        self.vcg.evcg_set_pattern()        # commits patterns into VCG
        self.vcg.evcg_set_arm(True)        # arms the VCG
        self.ser.write(STARTBYTE)

        # NOTE:
        #  evcg_busy() might get stuck always returning True
        t0 = time.time()
        while(self.vcg.evcg_busy()):
            if time.time()-t0 > 0.5:
                global EVCG_TIMEOUT_COUNTER
                EVCG_TIMEOUT_COUNTER += 1
                self.vcg.evcg_set_arm(False)           # disarm, just in case
                raise VCG_BusyTimeout("VCG stuck busy")
            pass                        # waits until glitching finishes
        self.vcg.evcg_set_arm(False)    # disarms the VCG

        response = self.ser.read(RESPLEN)
        if len(response) != RESPLEN:
            raise VCG_ReadTimeout("board not responding")

        return response


    def reset(self, secs=0.1):
        self.vcg.set_smartcard_soft_reset(0)
        time.sleep(secs)
        self.vcg.set_smartcard_soft_reset(1)

        time.sleep(0.01)


    def set_intensity_level(self, intensity):
        assert 0<=intensity<=1
        HI = 4.2
        LO = -9.8
        self.vcg.set_laser_glitch_parameter(v_amplitude=(intensity*(HI-LO)+LO), v_vcc_clk=3.3)
