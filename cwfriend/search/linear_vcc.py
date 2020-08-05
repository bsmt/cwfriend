import logging
import time

import pandas
import plotly.express as px

from ..context.result import Result
from .base import VCCGlitchSearchStrategy


class LinearVCCGlitchSearch(VCCGlitchSearchStrategy):
    '''Search through a given parameter space linearly.

    The supported variables are offset and width, as ChipWhisperer uses
    a crowbar for voltage glitching.
    Input search ranges for offset and width as three-tuples, like this:
    (range_start, range_end, range_increment).
    Supply all values as seconds. You can use e-6 to get microseconds, and e-9 to get nanoseconds.
    Also make sure start is less than end. Or make increment negative, whatever.

    These time values will be converted into clock cycles and percentages of clock cycles,
    which is what ChipWhisperer uses internally.
    
    This is a simple but inefficient strategy. It will search through the width range before incrementing offset
    If you aren't synchronized with your target, it's probably best to keep the offset range increment value
    a multiple of the glitch module clock period.
    '''
    
    def __init__(self, scope, context, offset_range, width_range,
                 attempts=3, iteration_delay=0.1, ext_only=False,
                 min_width_percent=30.0):
        super().__init__(scope, context, iteration_delay=iteration_delay,
                         min_width_percent=min_width_percent)
        
        self.attempts = attempts
        self.ext_only = ext_only

        self.offset_start = offset_range[0]
        self.offset_end = offset_range[1]
        self.offset_inc = offset_range[2]
        self.current_offset = self.offset_start

        self.width_start = width_range[0]
        self.width_end = width_range[1]
        self.width_inc = width_range[2]
        self.current_width = self.width_start
    
    def add_result(self, result):
        # values are in lists to make pandas happy
        result_item = {"offset": [self.current_offset],
                       "width": [self.current_width],
                       "result": [result.name]}
        if result == Result.SUCCESSFUL:
            logging.warning(f"Successful result: {result_item}")
        elif result == Result.ODD:
            logging.info(f"Odd result: {result_item}")
        result_df = pandas.DataFrame.from_dict(result_item)
        self.results = self.results.append(result_df)

    def plot_results(self):
        fig = px.scatter(self.results, x="offset", y="width", color="result")
        fig.show()

    def test_parameter_set(self):
        '''Test current set of parameters self.attempts times.'''
        results = []
        for _ in range(self.attempts):
            self.context.test_setup()
            result = self.context.test_one()
            self.context.test_teardown()
            results.append(result)
            time.sleep(self.iteration_delay)
        
        unique_results = set(results)
        if len(unique_results) == 1:  # consistent results
            self.add_result(results[0])
        else:  # pick highest value
            most_important_result = max(results)
            self.add_result(most_important_result)
        # TODO: improve this logic

    def search(self):
        self.current_offset = self.offset_start
        self.current_width = self.width_start

        while self.current_offset < self.offset_end:
            self.current_width = self.width_start
            self.calculate_offset_parameters(self.current_offset, ext_only=self.ext_only)

            while self.current_width < self.width_end:
                self.calculate_width_parameters(self.current_width)
                self.test_parameter_set()
                self.current_width += self.width_inc
            
            self.current_offset += self.offset_inc