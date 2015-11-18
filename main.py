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


def defaultTests(verbosity="default"):
        """ create and run a set of standard test scenarios """
        # create a list of tests to be run
        mlist = list()

        m = Model("prim: v,      0 cp, 5/30s, 1G/200MiB/s")
        m.copies = 1
        m.cache_1 = 4 * GB
        m.nv_1 = False
        mlist.append(m)

        m = Model("prim: nv,     0 cp, 5/30s, 1G/200MiB/s")
        m.copies = 1
        m.cache_1 = 4 * GB
        m.nv_1 = True
        mlist.append(m)

        m = Model("symmetric:  2 v cp, 5/30s, 1G/200MiB/s")
        m.symmetric = True
        m.copies = 2
        m.cache_1 = 8 * GB
        m.nv_1 = False
        m.cache_2 = 0
        m.nv_2 = False
        mlist.append(m)

        m = Model("prim: v,    1 v cp, 5/30s, 1G/200MiB/s")
        m.copies = 2
        m.cache_1 = 4 * GB
        m.nv_1 = False
        m.cache_2 = 40 * GB
        m.nv_2 = False
        mlist.append(m)

        m = Model("prim: v,   1 nv cp, 5/30s, 1G/200MiB/s")
        m.copies = 2
        m.cache_1 = 4 * GB
        m.nv_1 = False
        m.cache_2 = 40 * GB
        m.nv_2 = True
        mlist.append(m)

        m = Model("symmetric: 2 nv cp, 5/30s, 1G/200MiB/s")
        m.symmetric = True
        m.copies = 2
        m.cache_1 = 8 * GB
        m.nv_1 = True
        m.cache_2 = 0
        m.nv_2 = True
        mlist.append(m)

        m = Model("prim: nv,  1 nv cp, 5/30s, 1G/200MiB/s")
        m.copies = 2
        m.cache_1 = 8 * GB
        m.nv_1 = True
        m.cache_2 = 40 * GB
        m.nv_2 = True
        mlist.append(m)

        m = Model("symmetric:  3 v cp, 5/30s, 1G/200MiB/s")
        m.symmetric = True
        m.copies = 3
        m.cache_1 = 12 * GB
        m.nv_1 = False
        m.cache_2 = 0
        m.nv_2 = False
        mlist.append(m)

        m = Model("prim: v,    2 v cp, 5/30s, 1G/200MiB/s")
        m.copies = 3
        m.cache_1 = 4 * GB
        m.nv_1 = False
        m.cache_2 = 40 * GB
        m.nv_2 = False
        mlist.append(m)

        m = Model("prim: v,   2 nv cp, 5/30s, 1G/200MiB/s")
        m.copies = 3
        m.cache_1 = 4 * GB
        m.nv_1 = False
        m.cache_2 = 40 * GB
        m.nv_2 = True
        mlist.append(m)

        m = Model("symmetric: 3 nv cp, 5/30s, 1G/200MiB/s")
        m.copies = 3
        m.symmetric = True
        m.cache_1 = 12 * GB
        m.nv_1 = True
        m.cache_2 = 0
        m.nv_2 = True
        mlist.append(m)

        m = Model("prim: nv,  2 nv cp, 5/30s, 1G/200MiB/s")
        m.copies = 3
        m.cache_1 = 4 * GB
        m.nv_1 = True
        m.cache_2 = 40 * GB
        m.nv_2 = True
        mlist.append(m)

        # run all the specified models
        run(mlist, verbosity)


def main():
    """ process command line arguments, run specified tests """

    # process the command line arguments arguments
    from optparse import OptionParser
    parser = OptionParser(usage="usage: %prog [options] [modules]")
    parser.add_option("-g", "--gui", dest="gui", action="store_true",
                      default=False, help="GUI control panel")
    parser.add_option("-v", "--verbosity", dest="verbose",
                      metavar="data|headings|parameters|debug|all",
                      default="")
    (opts, files) = parser.parse_args()

    # file names are test modules
    if len(files) > 0:
        for f in files:
            module = import_module(f)
            method = getattr(module, 'tests')
            method(opts.verbose)
    else:
        defaultTests(opts.verbose)

if __name__ == "__main__":
    main()
