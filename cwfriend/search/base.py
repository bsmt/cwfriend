import math
import logging

import pandas


class SearchStrategy(object):
    '''Base class for search strategies.
    
    Search strategies should iterate through a supplied search range,
    set the parameters in the scope, tell the context what to do, and
    interpret results.
    
    Results are stored in a Pandas DataFrame. You can add results by
    '''

    def __init__(self, scope, context, iteration_delay=0.1):
        '''
        scope: ChipWhisperer scope class
        context: cwfriend Context class
        iteration_delay: Time to delay between attempts
        '''
        self.scope = scope
        self.context = context
        self.iteration_delay = iteration_delay

        self.results = pandas.DataFrame()

    def search(self):
        '''Start iterating through test cases.
        
        Call test_one on context each iteration and store results.
        '''
        pass

    def add_result(self, result):
        '''Store the result for the last test case.
        
        This will be placed in the self.results pandas dataframe.
        Items are a dictionary with parameter names as keys,
        and the Result enum under a "result" key.
        '''
        self.results = self.results.append({"result": result.name})


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
    
    def __init__(self, scope, context, iteration_delay=0.1, min_width_percent=1.0):
        super().__init__(scope, context, iteration_delay=iteration_delay)

        self.min_width_percent = min_width_percent

    def constrain_width(self, desired_width):
        '''ChipWhisperer may not make substantial glitches at low width percentages.
        
        Use this to constrain a desired width into a range from
        self.min_width_percent to 49.8. Calculation is based on a simple proportion.

        desired_width / 100 = new_width / (49.8 - min_width)
        '''

        new_width = (desired_width * (49.8 - self.min_width_percent)) / 100
        # this gets us a width between 0 and (49.8 - min_width)
        # add it back to min_width to get us in the range we want
        new_width += self.min_width_percent
        return new_width

    def calculate_offset_parameters(self, desired_offset, ext_only=False):
        '''Configure ChipWhisperer to place a glitch at `desired_offset` from trigger.
        
        This will find a combination of Chipwhisperer's ext_offset and offset to get as close as possible.
        If ext_only is True, it will only use the ext_offset parameter.
        This is necessary when you cannot synchronize with the target's clock.
        offset_fine will be set to zero always.
        '''

        logging.info(f"Calculating parameters for offset of {desired_offset}")

        # TODO: Incorporate CW triggering delay?
        # Even at ext_offset = 0, i seem to be a little after the trigger
        
        glitch_clk_freq = self.scope.clock.clkgen_freq
        glitch_clk_period = 1 / glitch_clk_freq

        # calculate rough ext_offset
        ext_offset_ideal = desired_offset / glitch_clk_period
        ext_offset = math.floor(ext_offset_ideal)
        logging.debug(f"Setting ext_offset to {ext_offset}")
        self.scope.glitch.ext_offset = ext_offset
        #self.scope.glitch.offset = 1.0
        self.scope.glitch.offset_fine = 0  # ignore offset_fine for now
        if ext_only:  # we're done
            return

        # turn the remaning fraction of a cycle into offset
        # TODO: Can chipwhisperer handle 0%?
        ## if it logs a lot, let's just set it to 1% or something in those cases
        ext_frac = math.modf(ext_offset_ideal)[0]
        if ext_frac > 0.50:
            # we can't go over ~50% of a clock
            # so if it's above that there, let's increment ext_off and use negative width
            self.scope.glitch.ext_offset += 1
            negative_offset = (1.0 - ext_frac) * -10.0
            if -1.0 < negative_offset < 1.0:
                negative_offset = -10.0  # low offsets don't work
            logging.debug(f"Setting offset to {negative_offset}")
            self.scope.glitch.offset = negative_offset
        else:
            if -1.0 < ext_frac < 1.0:
                ext_frac = 10.0
            else:
                ext_frac *= 10.0
            logging.debug(f"Setting offset to {ext_frac}")
            self.scope.glitch.offset = ext_frac

    def calculate_width_parameters(self, desired_width):
        '''Configure ChipWhisperer to make a pules of `desired_width`.
        
        If the desired width is longer than one clock cycle for the glitch module,
        the repeat paramter will be used to attempt to make one large pulse.
        
        Unfortunately, ChipWhisperer's MOSFETs often cannot do extremely quick pulses.
        These tend to show up as little blips in the power, barely dropping 0.25V.
        It probably depends a lot on your target, but I've had the most luck keeping
        my width percentage above 35%. You can use the class min_width_percent variable
        to set this.

        This will only use positive width parameters to keep things simple.
        '''

        logging.info(f"Calculating parameters for width of {desired_width}")

        glitch_clk_freq = self.scope.clock.clkgen_freq
        glitch_clk_period = 1 / glitch_clk_freq
        max_single_width = glitch_clk_period
        self.scope.glitch.width_fine = 0  # ignore width_fine for now

        if desired_width < max_single_width:
            # we can use one cycle
            width_percentage = self.constrain_width((desired_width / max_single_width) * 100)
            self.scope.glitch.width = width_percentage
            logging.debug(f"Setting glitch width to {width_percentage}%")
            self.scope.glitch.repeat = 1
            logging.debug("Setting glitch repeat to 1")
        else:
            # we need to use repeat to make multiple pulses
            # the pulses will be pretty distinct until you get to widths close to 50%
            # they look the same for positive/negative
            repeat_ideal = desired_width / glitch_clk_period
            repeat = math.floor(repeat_ideal)
            repeat_frac = self.constrain_width(math.modf(repeat_ideal)[0])
            # constrain_width will clamp the fractional part between (min_width, 49.8)
            width_percentage = self.constrain_width(repeat_frac)
            logging.debug(f"Setting glitch width to {width_percentage}%")
            self.scope.glitch.width = width_percentage
            logging.debug(f"Setting glitch repeat to {repeat}")
            self.scope.glitch.repeat = repeat
