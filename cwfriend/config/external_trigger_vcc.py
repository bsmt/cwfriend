from .base import ConfigBase


class ExternalOneShotTriggerVCCGlitchConfig(ConfigBase):
    '''Configuration for voltage glitching with an external trigger and no clock sent to the target.
    
    This uses the ext_single, which will only glitch once per scope arm.
    Depending on your attack this may or may not be desired.
    
    By default, the trigger pin is GPIO4, labelled as "TRIG" on CW308.
    You can find information on supported trigger pins here:
    https://chipwhisperer.readthedocs.io/en/latest/api.html?highlight=update#chipwhisperer.scopes.OpenADC.trigger
    '''
    def __init__(self, scope, synchronized=False, clkgen_freq=None, trigger_pin="tio4", high_power=False):
        super().__init__(scope)
        
        self.high_power = high_power

        # TODO: should we mess with the ADC config?
        # i don't think we need it, might be better to disable it if possible
        if synchronized:
            pass
        else:
            self.scope.glitch.clk_src = "clkgen"
            self.scope.io.hs2 = "disabled"

        self.scope.clock.clkgen_freq = clkgen_freq

        self.scope.glitch.output = "glitch_only"
        self.scope.glitch.trigger_src = "ext_single"
        # after_scope seems to work best.
        # you might need before_scope if you're triggering right after the scope arms
        # but I typically just arm the scope after resetting the chip, so it'll be ready whenever
        self.scope.glitch.arm_timing = "after_scope"

        self.scope.trigger.triggers = trigger_pin

        if self.high_power:
            self.scope.io.glitch_hp = True
            self.scope.io.glitch_lp = False
        else:
            self.scope.io.glitch_lp = True
            self.scope.io.glitch_hp = False

    def teardown(self):
        self.scope.io.glitch_lp = False
        self.scope.io.glitch_hp = False



class ExternalContinuousTriggerVCCGlitchConfig(ExternalOneShotTriggerVCCGlitchConfig):
    '''Similar to ExternalOneShotTriggerVCCGlitchConfig, 
    just with continuous triggering instead.
    
    This is useful when you want to trigger at several different points
    in one test case.
    A test case here means one instance where the scope is armed.'''

    def __init__(self, scope, trigger_pin="tio4"):
        super().__init__(self, scope, trigger_pin)

        self.scope.glitch.trigger_src = "ext_continuous"

