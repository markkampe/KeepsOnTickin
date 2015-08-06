#! /usr/bin/python

from sizes import PiB
from RelyFuncts import YEAR, HOUR

from Model import Model


def run(model, capacity=1*PiB, period=1*YEAR, repair=24*HOUR):
    """ execute a single model and print out the results
        capacity -- total system capacity (bytes)
        period -- modeled time period (hours)
        repair -- modeled repair time (hours)
    """

    # FIX   ... figure out what I want to output
    #       ... and then get the pretty print stuff working again
    (primaries, secondaries) = model.calculate_size(capacity)
    print("primaries = %d" % primaries)
    print("secondaries = %d" % secondaries)

    model.calculate_rates(repair)
    print("primary FITs = %d" % model.fits_1)
    print("secondary FITs = %d" % model.fits_2)

    results = model.calculate_durability(primaries, secondaries, period)
    print("Ploss(node) = %e, exp = %d" %
          (results.p_loss_node, results.exp_loss_node))
    print("Ploss(copy) = %e, exp = %d" %
          (results.p_loss_copy, results.exp_loss_copy))
