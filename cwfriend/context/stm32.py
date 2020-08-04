'''STM32 context. Used to break readout protection level 1.

Bootloader docs: https://www.st.com/content/ccc/resource/technical/document/application_note/51/5f/03/1e/bd/9b/45/be/CD00264342.pdf/files/CD00264342.pdf/jcr:content/translations/en.CD00264342.pdf
Chip-specific bootloader info: https://www.st.com/content/ccc/resource/technical/document/application_note/b9/9b/16/3a/12/1e/40/0c/CD00167594.pdf/files/CD00167594.pdf/jcr:content/translations/en.CD00167594.pdf
'''

import logging

from .base import SerialContext
from .result import Result, OddResultException


BOOTLOADER_INIT = b"\x7f"
ACK = b"\x79"
NACK = b"\x1f"
COMMAND_GV = b"\x01\xfe"
COMMAND_READ = b"\x11\xee"


class STM32ReadoutLevel1Context(SerialContext):
    '''Context for testing the STM32 bootloader's level 1 readout protection.
    
    BOOT0 must be high and BOOT1 must be low to activate the ROM bootloader.
    This context will try to read `size` bytes from `address`.
    If successful, the data will be stored in `self.data`.
    If you want to read all addresses, simply reinstantiate the
    context and search in a loop.
    '''

    def __init__(self, scope, address=0x08000000, size=256, 
                 baudrate=9600):
        # AFAIK all STM32 bootloaders use even parity and 1 stop bit
        super().__init__(self, scope, baudrate=baudrate,
                         stopbits=1, parity="even")

        self.address = address
        self.size = size
        self.data = None

        self.check_bootloader()

    def read_ack(self):
        '''Read an ACK byte from serial.
        
        If the byte read isn't actually an ACK,
        raise a ValueError exception.
        If the byte read IS an ACK, return True.
        '''
        
        ack_maybe = self.read(1)[0]
        if ack_maybe == ACK:
            return True
        elif ack_maybe == NACK:
            raise ValueError("NACK")
        else:
            raise OddResultException(f"Received unknown response ({ack_maybe})")

    def init_bootloader(self):
        '''Initialize the bootloader.
        
        This is done by simply sending an 0x7f byte and checking for an ACK.
        This method will not reset the target.
        '''
        self.write(BOOTLOADER_INIT)
        try:
            self.read_ack()
        except ValueError, OddResultException:
            return False
        else:
            return True

    def get_version(self):
        '''Get bootloader version using GV command.
        
        This is supposed to also return readout protection status,
        but it actually doesn't in the bootrom I looked at.'''
        self.write(COMMAND_GV)
        self.read_ack()
        bootloader_version = int.from_bytes(self.read(1)[0], byteorder="big")
        bootloader_major = bootloader_version & 0xf0
        bootloader_minor = bootloader_version & 0x0f
        # options hardcoded to 0 in the bootrom I reversed (stm32f103 v2.2)
        option_1 = self.read(1)[0]
        option_2 = self.read(1)[0]
        self.read_ack()  # it sends an ack again, idk why
        return (bootloader_major, bootloader_minor)

    def start_read_memory(self):
        '''Try to read memory using the bootloader's read command (0x11).
        
        If RDP is enabled (or not glitched around), this will raise a ValueError.
        If an odd value (neither ACK nor NACK) is returned, an OddResultException is raised.
        '''
        self.write(COMMAND_READ)
        return self.read_ack()  # will raise exceptions

    def send_address(self, address):
        '''Send the address to be read to the bootrom.
        
        This should happen after the read command (0x11ee) is ACKed.
        Send 4 address bytes MSB to LSB followed by a checksum.
        '''
        
        # MSB to LSB, so big endian
        addr_bytes = address.to_bytes(4, byteorder="big")
        checksum = (addr_bytes[3] ^ addr_bytes[2] ^ addr_bytes[1] ^ addr_bytes[0]).to_bytes(1, byteorder="big")
        self.write(addr_bytes + checksum)
        return self.read_ack()  # will raise exceptions

    def send_size(self, size):
        '''Send the number of bytes to be read by the bootrom.
        
        This should happen after the read command is ACKed,
        and the address is ACKed.
        Note that size - 1 is sent, as the max size is 256 and min is 1.
        '''

        wire_size = (size - 1).to_bytes(1, byteorder="big")
        checksum = (~wire_size & 0xff).to_bytes(1, byteorder="big")
        self.write(wire_size + checksum)
        return self.read_ack()  # will raise exceptions

    def check_bootloader(self):
        '''Check that we can communicate with the bootloader.
        
        Also check if RDP is enabled.
        Returns True if RDP is enabled, False if not.'''

        self.reset()
        
        try:
            self.init_bootloader()
        except:
            logging.error("Could not initialize bootloader. Check connections (BOOT pins, power, etc)")
            return False
        
        v_major, v_minor = get_version()
        logging.info(f"Bootloader version: {v_major}.{v_minor}")
        try:
            self.read_memory()
        except ValueError:
            logging.info("Readout protection is enabled.")
            return True
        # we don't handle OddValueException, because we aren't glitching
        # so if it's not returning an expected value, something is probably wrong
        else:
            logging.info("Readout protection is disabled. Nothing to do here.")
            return False

    def test_one(self):
        '''Try to read from memory through the bootloader.
        
        The 0x11 command is used to read memory.
        After sending 0x11,0xee, the bootloader will respond with an ACK/NACK.
        ACK if readout protection is disabled, NACK if enabled.
        So, if we can get it to ACK, we may have gotten around RDP.
        '''
        
        self.reset()
        self.init_bootloader()
        try:
            ack = self.start_read_memory()
        except ValueError:  # NACK, not interesting
            return Result.NORMAL
        except OddResultException:  # neither ACK nor NACK
            return Result.ODD
        except IndexError:  # read() returned [], no data
            return Result.MUTE
        
        if ack:
            # this doesn't necessarily mean we win
            # for instance, I can get it to ACK my initial command
            # but then not respond when i send address or size
            # or maybe it'll ACK all three but not send data
            # but, it's a start
            return Result.SUCCESSFUL