#!/usr/bin/python
#

"""
main routine for driving simulations
    process args and invoke gui or a default set of tests
"""

from importlib import import_module
from Model import Model
from run import run
from sizes import GB, MiB, GiB
from ColumnPrint import printSize


def defaultTests(columns="", verbosity="default"):
        """ create and run a set of standard test scenarios """
        # note the key background parameters
        m = Model("")
        misc = ", %d/%ds, %s/%s/s" % (m.time_timeout, m.time_detect,
                                      printSize(m.rate_mirror, 1000),
                                      printSize(m.rate_flush, 1000))

        # create a list of tests to be run
        mlist = list()

        # run tests for all the interesting combinations
        for cp in (1, 2, 3):
            for primary in (" v", "nv"):
                sList = ["none"] if cp == 1 else [" v", "nv", "symmetric"]
                for secondary in sList:
                    # suppress irrelevent combinations
                    if primary == "nv" and secondary == " v":
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
        run(mlist, columns, verbosity)


def main():
    """ process command line arguments, run specified tests """

    # process the command line arguments arguments
    from optparse import OptionParser
    parser = OptionParser(usage="usage: %prog [options] [modules]")
    parser.add_option("-g", "--gui", dest="gui", action="store_true",
                      default=False, help="GUI control panel")
    parser.add_option("-r", "--report", dest="columns",
                      metavar="bw,time", help="output columns",
                      default="")
    parser.add_option("-v", "--verbosity", dest="verbose",
                      metavar="data|headings|parameters|debug|all",
                      default="")
    (opts, files) = parser.parse_args()

    # file names are test modules
    if len(files) > 0:
        for f in files:
            module = import_module(f, package=__package__)
            method = getattr(module, 'tests')
            method(opts.columns, opts.verbose)
    else:
        defaultTests(opts.columns, opts.verbose)

if __name__ == "__main__":
    main()
