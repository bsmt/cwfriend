import time

from chipwhisperer.hardware.newaeusb.serial import USART

from .result import Result


class Context(object):
    '''Base class for target contexts.
    
    The job of the context class is to interface with the target
    and interpret results. See the Result class for more information.
    '''

    def __init__(self, scope):
        '''
        scope: ChipWhisperer Scope object.
            This is needed to do serial communications from CW.
        '''
        self.scope = scope

    def reset(self, hold_time=0.1, cut_power=False):
        '''Reset the target.
        
        This is done by the target NRST line low for `hold_time` seconds.
        
        If `cut_power` = True, this will be done instead by
        powering off the target.
        If you're powering the target with an external supply,
        `cut_power` will have no effect.
        '''

        if cut_power:
            self.scope.io.target_pwr = False
        else:
            self.scope.io.nrst = "low"
        time.sleep(hold_time)

        if cut_power:
            self.scope.io.target_pwr = True
        else:
            self.scope.io.nrst = "high"
        time.sleep(hold_time)

    def test_one(self):
        '''Perform one test iteration. Return a result
        
        This should do any target communications needed to get to the
        state that will be attacked.
        Then, resulting behavior should be observed and returned as a
        Result enum.'''
        pass


class SerialContext(Context):
    '''Base context for targets that need serial communications.
    
    UART is the only IO CWLite has, so you probably need this.
    
    This discards the chipwhisperer library's target system,
    as I've found it's a little obtuse to work with unless your
    target is already made by NewAE, which it won't be unless you're
    doing exercises. This just gives you some serial read/write methods
    and you can do what you want. Easy.

    See https://github.com/newaetech/chipwhisperer/blob/4fdaf07d7c573b5b78109f66e964e0217ae6b6d0/software/chipwhisperer/capture/targets/simpleserial_readers/cwlite.py
    for how the USB-serial interface is implemented in the chipwhisperer library.
    '''
    
    def __init__(self, scope, baudrate, stopbits=1, parity="none"):
        '''
        up to 250000 baud is supported
        stopbits can be 1, 1.5, or 2
        parity can be one of "none","odd","even","mark","space
        '''
        super().__init__(self, scope)

        # TODO: sanity check these
        self.baudrate = baudrate
        self.stopbits = stopbits
        self.parity = parity

        self.serial = USART(self.scope._cwusb)
        self.serial.init(baudrate, stopbits, parity)

    def read(self, n_chars, timeout=250):
        '''Read `n_chars` over UART.
        
        Timeout isn't necessarily a time value, just an indicator
        that it will wait a while for data to show up.
        
        If n_chars = 0, all data present is returned.
        This will return data in a list, so if there is no data you will receive an empty list.
        '''
        return self.serial.read(n_chars, timeout)
    
    def write(self, data):
        '''Write `data` over UART.
        
        Data can be a bytestring or normal string.
        If it's a normal string, it will be encoded as latin-1.
        '''
        self.serial.write(data)

    def flush(self):
        '''Delete all data from the UART Rx buffer.'''
        self.serial.flush()
