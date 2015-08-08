#!/usr/bin/python
#

"""
main routine for driving simulations
    process args and invoke gui or a default set of tests
"""

from Model import Model
from run import run


def defaultTests():
        """ create and run a set of standard test scenarios """
        # create a list of tests to be run
        mlist = list()

        m = Model("primary: v,  no copies")
        m.copies = 0         # secondary copies
        m.n_dram_1 = 16      # DRAM DIMMs / primary node
        m.n_nvram_1 = 0      # NVRAM DIMMs / primary node
        m.n_dram_2 = 0       # DRAM DIMMs / secondary node
        m.n_nvram_2 = 0      # NVRAM DIMMs / secondary node
        mlist.append(m)

        m = Model("primary: nv, no copies")
        m.copies = 0         # secondary copies
        m.n_dram_1 = 0       # DRAM DIMMs / primary node
        m.n_nvram_1 = 16     # NVRAM DIMMs / primary node
        m.n_dram_2 = 0       # DRAM DIMMs / secondary node
        m.n_nvram_2 = 0      # NVRAM DIMMs / secondary node
        mlist.append(m)

        m = Model("primary: v,  1 nv copy")
        m.copies = 1         # secondary copies
        m.n_dram_1 = 16      # DRAM DIMMs / primary node
        m.n_nvram_1 = 0      # NVRAM DIMMs / primary node
        m.n_dram_2 = 0       # DRAM DIMMs / secondary node
        m.n_nvram_2 = 16     # NVRAM DIMMs / secondary node
        mlist.append(m)

        m = Model("primary: nv, 1 nv copy")
        m.copies = 1         # secondary copies
        m.n_dram_1 = 0       # DRAM DIMMs / primary node
        m.n_nvram_1 = 16     # NVRAM DIMMs / primary node
        m.n_dram_2 = 0       # DRAM DIMMs / secondary node
        m.n_nvram_2 = 16     # NVRAM DIMMs / secondary node
        mlist.append(m)

        m = Model("primary: v,  2 nv copy")
        m.copies = 2         # secondary copies
        m.n_dram_1 = 16      # DRAM DIMMs / primary node
        m.n_nvram_1 = 0      # NVRAM DIMMs / primary node
        m.n_dram_2 = 0       # DRAM DIMMs / secondary node
        m.n_nvram_2 = 16     # NVRAM DIMMs / secondary node
        mlist.append(m)

        m = Model("primary: nv, 2 nv copy")
        m.copies = 2         # secondary copies
        m.n_dram_1 = 0       # DRAM DIMMs / primary node
        m.n_nvram_1 = 16     # NVRAM DIMMs / primary node
        m.n_dram_2 = 0       # DRAM DIMMs / secondary node
        m.n_nvram_2 = 16     # NVRAM DIMMs / secondary node
        mlist.append(m)

        # run all the specified models
        run(mlist, verbosity="headings")


def main():
    """ process command line arguments, run specified tests """

    # process the command line arguments arguments
    from optparse import OptionParser
    parser = OptionParser(usage="usage: %prog [options]")
    parser.add_option("-g", "--gui", dest="gui", action="store_true",
                      default=False, help="GUI control panel")
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
        defaultTests()

if __name__ == "__main__":
    main()
