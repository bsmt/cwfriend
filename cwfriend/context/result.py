from enum import Enum


class Result(Enum):
    '''
    Results have a few different categories:
    * NORMAL - The target is behaving normally.
        Therefore, the glitch had no noticable effect.
    * MUTE - The target reset or is no longer responding.
        This likely means it crashed.
    * ODD - The target is doing something unexpected.
        It is up to the context class to determine what requirements
        this case has.
    * SUCCESSFUL - The target behaves as we'd like it to.
    '''
    NORMAL = 1
    MUTE = 2
    ODD = 3
    SUCCESSFUL = 4


class OddResultException(Exception):
    '''An exception class that can be used to distinguish between
    normal errors and errors that might be interesting, should you
    choose to use exceptions to pass results around your code.'''
    pass