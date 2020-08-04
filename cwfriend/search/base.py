import math
import logging


class SearchStrategy(object):
    '''Base class for search strategies.
    
    Search strategies should iterate through a supplied search range,
    set the parameters in the scope, tell the context what to do, and
    interpret results.'''

    def __init__(self, scope, context, iteration_delay=0.1):
        '''
        scope: ChipWhisperer scope class
        context: cwfriend Context class
        iteration_delay: Time to delay between attempts
        '''
        self.scope = scope
        self.context = context
        # results map a parameter set to a Result
        # you can order this however you want, as long as it's consistent
        self.results = []

    def search(self):
        '''Start iterating through test cases.
        
        Call test_one on context each iteration and store results.
        '''
        pass


class VCCGlitchSearchStrategy(SearchStrategy):
    '''Base class for VCC glitching strategies.
    
    These will all have the same input parameters for ChipWhisperer,
    so a common class makes sense.
    
    VCC Glitching on ChipWhisperer has two basic parameters: offset and width.
    Both are split into a few different granularities.
    
    Offset has ext_offset, offset, and offset_fine.
    ext_offset is a number of clock cycles (chipwhisperer's glitch clock) that it should
    wait after triggering to start the glitch module.
    offset allows you to place the glitch pulse within a single clock cycle.
    So, it's a position in a clock cycle as position, referenced from the rising edge.
    Negative values move you closer to the beginning from the rising edge, positive away.
    Note that the clock offset will not be very reliable if you do not have the glitch clock
    synchronized with the target. If your target has an internal clock, you can leave this value alone.
    To get more accurate positioning, you can increase the glitch clock to get more granularity.
    offset_fine is a dimensionless fine tuning value.

    Width has width and width_fine.
    Width is a percentage of a clock cycle, similar to offset.
    Negative width percentages simply move the pulse left of the rising edge.
    width_fine is similar to offset_fine.
    Smaller widths will also make the pulse voltage drop smaller,
    I've noticed widths closer to 0% only drop a volt or so.
    To get long pulses (longer than one clock cycle), you may be able to use
    repeat with a high width to get them to merge into one big pulse.

    Working with all of these different variables is tedious, so I plan
    on working with simple time values and calculating parameters based on those.
    This way you can simply specify an offset range in time (say, 20-30us from trigger),
    and a width range in time (maybe 50-100ns).
    We'll see if that is reliable with ChipWhisperer.
    '''
    
    def __init__(self, scope, context, offset_range, width_range,
                 iteration_delay=0.1):
        '''Initialize VCC Glitch strategy.
        
        offset_range and width_range are three-tuples with
        (start, end, granularity). All values in seconds.
        You can use e-6 to get microseconds, and e-9 for nanoseconds.
        '''
        
        super().__init__(self, scope, context, iteration_delay=iteration_delay)

        self.offset_start = offset_range[0]
        self.offset_end = offset_range[1]
        self.offset_granularity = offset_range[2]

        self.width_start = width_range[0]
        self.width_end = width_range[1]
        self.width_granularity = width_range[2]

    def calculate_offset_parameters(self, desired_offset, ext_only=False):
        '''Configure ChipWhisperer to place a glitch at `desired_offset` from trigger.
        
        This will find a combination of Chipwhisperer's ext_offset and offset to get as close as possible.
        If ext_only is True, it will only use the ext_offset parameter.
        This is necessary when you cannot synchronize with the target's clock.
        offset_fine will be set to zero always.
        '''

        # TODO: Incorporate CW triggering delay?
        # Even at ext_offset = 0, i seem to be a little after the trigger
        
        glitch_clk_freq = self.scope.clock.clkgen_freq
        glitch_clk_period = 1 / glitch_clk_freq

        # calculate rough ext_offset
        ext_offset_ideal = desired_offset / glitch_clk_period
        ext_offset = math.floor(ext_offset_ideal)
        logging.debug(f"Setting ext_offset to {ext_offset} for desired offset of {desired_offset}")
        self.scope.glitch.ext_offset = ext_offset
        self.scope.glitch.offset = 1.0
        self.scope.glitch.offset_fine = 0.0  # ignore offset_fine for now
        if ext_only:  # we're done
            return

        # turn the remaning fraction of a cycle into offset
        # TODO: Can chipwhisperer handle 0%?
        ## if it logs a lot, let's just set it to 1% or something in those cases
        ext_frac = math.modf(ext_offset_ideal)
        if ext_frac > 0.50:
            # we can't go over ~50% of a clock
            # so if it's above that there, let's increment ext_off and use negative width
            self.scope.glitch.ext_offset += 1
            negative_offset = (1.0 - ext_frac) * -1
            self.scope.glitch.offset = negative_offset
        else:
            self.scope.glitch.offset = ext_frac

    def calculate_width_parameters(self, desired_width):
        '''Configure ChipWhisperer to make a pules of `desired_width`.
        
        If the desired width is longer than one clock cycle for the glitch module,
        the repeat paramter will be used to attempt to make one large pulse.
        This may not be very accurate, however.
        '''
        
        glitch_clk_freq = self.scope.clock.clkgen_freq
        glitch_clk_period = 1 / glitch_clk_freq
        max_single_width = glitch_clk_period / 2

        if desired_width < max_single_width:
            # we can use one cycle
            width_percentage = (desired_width / glitch_clk_period) * 100
            self.scope.glitch.width = width_percentage
        else:
            # we need to use repeat to make multiple pulses, and try to join them
            pass

# 07384615.384615385
# 16000000.0