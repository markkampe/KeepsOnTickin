#
# Ceph - scalable distributed file system
#
# Copyright (C) Inktank
#
# This is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License version 2.1, as published by the Free Software
# Foundation.  See file COPYING.
#

# FIX: merge these enhancements back to ceph-tools

"""
basic mathematical functions used in reliability modeling

   for some reason I felt inclined not to ask clients to know what the
   denominator for FIT rates was, so I have provided routines to
   convert between FITs and convenient units
"""

import math

# units of time (FIT rates)
HOUR = 1
MINUTE = float(HOUR) / 60
SECOND = float(HOUR) / 3600
DAY = float(HOUR * 24)
YEAR = (HOUR * 24 * 365.25)

BILLION = 1000000000


def FitRate(events, period=YEAR):
    """ FIT rate corresponding to a rate in other unit
            events -- number of events
            period --  period in which that many events happen
    """
    return events * BILLION / period


def mttf(fits):
    """ MTTF corresponding to an FIT rate
            fits --- FIT rate
    """
    return BILLION / fits


def Pfail(fitRate, hours, n=1):
    """ probability of exactly n failures during an interval
            fitRate -- nominal FIT rate
            hours -- number of hours to await event
            n -- number of events for which we want estimate
    """

    expected = float(fitRate) * hours / 1000000000
    p = math.exp(-expected)
    if n > 0:
        p *= (expected ** n)
        p /= math.factorial(n)
    return p


def Pn(expected=1, n=0):
    """ probability of n events occurring when exp are expected
            exp -- number of events expected during this period
            n -- number of events for which we want estimate
    """
    p = math.exp(-expected)
    if n > 0:
        p *= (expected ** n)
        p /= math.factorial(n)
    return p


def allFail(fitRate, total, required, repair):
    """ effective FIT rate required/total redundant components
            fitRate -- FIT rate of a single component
            total -- number of redundant components in system
            required -- number required for continued operation
            repair -- repair time (in hours)
    """

    # FIX
    #   I could not readily find this formula, and needed one,
    #   so I made this up.  I should do some research and use
    #   a correct one.
    #
    #   start with the FITs of the initial set of components
    #   for each remaining redundant component
    #       multiply by probability of next faiulre (within repair window)
    #
    fits = total * fitRate      # initial FIT rate
    total -= 1
    while total >= required:    # probability of succesive failures
        P_nextfail = total * fitRate * repair * 10E-9
        fits *= P_nextfail
        total -= 1

    return fits
