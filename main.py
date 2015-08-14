#!/usr/bin/python
#

"""
main routine for driving simulations
    process args and invoke gui or a default set of tests
"""

from Model import Model
from run import run


def defaultTests(verbosity="default"):
        """ create and run a set of standard test scenarios """
        # create a list of tests to be run
        mlist = list()

        m = Model("prim: v,  no copies, 30s, 50MB/s")
        m.nv_1 = False
        m.copies = 0
        m.time_detect = 30
        m.rate_flush = 50000000
        mlist.append(m)

        m = Model("prim: nv, no copies, 30s, 50MB/s")
        m.nv_1 = True
        m.copies = 0
        m.time_detect = 30
        m.rate_flush = 50000000
        mlist.append(m)

        m = Model("prim: v,  1 nv copy, 30s, 50MB/s")
        m.nv_1 = False
        m.nv_2 = True
        m.copies = 1
        m.time_detect = 30
        m.rate_flush = 50000000
        mlist.append(m)

        m = Model("prim: nv, 1 nv copy, 30s, 50MB/s")
        m.copies = 1
        m.nv_1 = True
        m.nv_2 = True
        m.rate_flush = 50000000
        mlist.append(m)

        m = Model("prim: v,  2 nv copy, 30s, 50MB/s")
        m.copies = 2
        m.nv_1 = False
        m.nv_2 = True
        m.rate_flush = 50000000
        mlist.append(m)

        m = Model("prim: nv, 2 nv copy, 30s, 50MB/s")
        m.copies = 2
        m.nv_1 = True
        m.nv_2 = True
        m.rate_flush = 50000000
        mlist.append(m)

        # run all the specified models
        run(mlist, verbosity)


def main():
    """ process command line arguments, run specified tests """

    # process the command line arguments arguments
    from optparse import OptionParser
    parser = OptionParser(usage="usage: %prog [options]")
    parser.add_option("-g", "--gui", dest="gui", action="store_true",
                      default=False, help="GUI control panel")
    parser.add_option("-v", "--verbosity", dest="verbose",
                      metavar="data|headings|parameters|debug",
                      default="")
    (opts, files) = parser.parse_args()

    for f in files:
        if f == "gui" or f == "GUI":
            opts.gui = True

    # instantiate, run, and report results from a model
    if opts.gui:
        print "GUI not yet implemented"
        # from RelyGUI import RelyGUI
        # gui = RelyGUI(cfg, oneTest)
        # gui.mainloop()
    else:
        defaultTests(opts.verbose)

if __name__ == "__main__":
    main()
