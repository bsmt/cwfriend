class ConfigBase(object):
    '''Base class for ChipWhisperer configuration.
    This class will also configure the same defaults as Setup_Generic
    
    Depending on what you're doing, you'll want to make changes to the 
    various scope settings.'''

    def __init__(self, scope, clkgen_freq=None):
        self.scope = scope
        self.scope.default_setup()

        if clkgen_freq:
            # The library will automagically set clock multiplier
            # and divider to get as close as possible to the desired freq.
            self.scope.clock.clkgen_freq = clkgen_freq