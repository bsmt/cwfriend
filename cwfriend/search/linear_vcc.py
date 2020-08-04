from .base import SearchStrategy


class LinearVCCGlitchSearch(SearchStrategy):
    '''Search through a given parameter space linearly.

    The supported variables are offset and width, as ChipWhisperer uses
    a crowbar for voltage glitching.
    This is a simple but inefficient strategy.'''
    pass