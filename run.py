#! /usr/bin/python

from sizes import PiB
from RelyFuncts import YEAR, HOUR

from Model import Model, Sizes, Rates, Results


def run(model, capacity=1*PiB, period=1*YEAR, repair=24*HOUR):
    """ execute a single model and print out the results
        capacity -- total system capacity (bytes)
        period -- modeled time period (hours)
        repair -- modeled repair time (hours)
    """

    # FIX   ... figure out what I want to output
    #       ... and then get the pretty print stuff working again
    sizes = Sizes(model, capacity)
    print("primaries = %d" % sizes.n_primary)
    print("secondaries = %d" % sizes.n_secondary)

    rates = Rates(model, repair)
    print("primary HW FITs = %d" % rates.fits_primary_hw)
    print("primary SW FITs = %d" % rates.fits_primary_sw)
    print("secondary HW FITs = %d" % rates.fits_secondary_hw)
    print("secondary SW FITs = %d" % rates.fits_secondary_sw)

    results = Results(model, sizes, rates, period)
    print("Ploss(node) = %e, exp = %d" %
          (results.p_loss_node, results.exp_loss_node))
    print("Ploss(copy) = %e, exp = %d" %
          (results.p_loss_copy, results.exp_loss_copy))
    print("Ploss(total) = %e, exp = %d" %
          (results.p_loss_all, results.exp_loss_all))
    print("durability = %e, nines = %d" %
          (results.durability, results.nines))
