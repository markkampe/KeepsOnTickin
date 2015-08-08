#!/usr/bin/python
#

"""
main routine for driving simulations
    process args and invoke gui or a default set of tests
"""

from Model import Model
from run import run


def defaultTests():
        # create a list of tests to be run
        mlist = list()
        model = Model("Default")
        mlist.append(model)

        # run all the specified models
        run(mlist, verbosity="all")


def main():
    """ CLI entry-point:
        process command line arguments, run gui or a standard set of tests
    """

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
