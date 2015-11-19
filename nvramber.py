#!/usr/bin/python
#

"""
    Test suite to explore implications of NVRAM BIT error rates
"""

from Model import Model
from run import run
from sizes import GB, MiB, GiB


def tests(verbosity="default"):
        """ create and run a set of standard test scenarios """
        # create a list of tests to be run
        mlist = list()

        rates = (1.0E-5, 1.0E-6, 1.0E-7, 1.0E-8, 1.0E-9, 1.0E-10, 1.0E-11,
                 1.0E-12, 1.0E-13, 1.0E-14, 1.0E-15, 1.0E-16, 1.0E-17)

        for ber in (rates):
            misc = ", %7.1e" % (ber)
            for cp in (1, 2, 3):
                for primary in ("v ", "nv"):
                    sList = ["none"] if cp == 1 else ["nv", "symmetric"]
                    for secondary in sList:
                        # skip uninteresting combinations
                        if primary != "nv" and cp < 2:
                            continue
                        if primary != "nv" and secondary == "symmetric":
                            continue

                        # figure out how to caption this configuration
                        if secondary == "symmetric":
                            desc = ("symmetric: %d %s cp" % (cp, primary))
                        elif (cp > 1):
                            desc = ("prim: %s   %d %s cp" %
                                   (primary, cp - 1, secondary))
                        else:
                            desc = "prim: %s      0 cp" % (primary)

                        # instantiate the model
                        m = Model(desc + misc)
                        m.ber_vm_r = ber
                        m.copies = cp
                        m.nv_1 = (primary == "nv")
                        m.cache_1 = 4 * GB
                        if secondary == "symmetric":
                            m.symmetric = True
                            m.cache_1 *= cp
                            m.nv_2 = (primary == "nv")
                            m.cache_2 = 0
                        elif cp > 1:
                            m.nv_2 = (secondary == "nv")
                            m.cache_2 = 40 * GB
                        mlist.append(m)

        # run all the specified models
        run(mlist, verbosity)
