class ConfigBase(object):
    '''Base class for ChipWhisperer configuration.
    This class will also configure the same defaults as Setup_Generic
    
    Depending on what you're doing, you'll want to make changes to the 
    various scope settings.'''

    def __init__(self, scope):
        self.scope = scope
        self.scope.default_setup()

    def teardown(self):
        pass