import logging

import chipwhisperer as cw

from cwfriend.config import ExternalOneShotTriggerVCCGlitchConfig
from cwfriend.context import STM32ReadoutLevel1Context
from cwfriend.search import LinearVCCGlitchSearch


logging.getLogger().setLevel(logging.DEBUG)

offset_range = (48.5e-6, 52e-6, 100e-9)
width_range = (60e-9, 170e-9, 10e-9)

scope = cw.scope()

cfg = ExternalOneShotTriggerVCCGlitchConfig(scope, synchronized=False,
                                            clkgen_freq=24e6, high_power=False)
ctx = STM32ReadoutLevel1Context(scope)
search = LinearVCCGlitchSearch(scope, ctx, offset_range, width_range,
                               iteration_delay=0.75, ext_only=False,
                               min_width_percent=35.0)

try:
    search.search()
except KeyboardInterrupt:
    cfg.teardown()
    search.plot_results()