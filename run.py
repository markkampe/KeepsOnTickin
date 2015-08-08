#

from sizes import PiB
from RelyFuncts import YEAR, HOUR

from Model import Model, Sizes, Rates, Results
from ColumnPrint import ColumnPrint


def run(models, capacity=1*PiB, period=1*YEAR, repair=24*HOUR,
        verbosity="headings"):
    """ execute a single model and print out the results
        models -- list of models to be run
        capacity -- total system capacity (bytes)
        period -- modeled time period (hours)
        repair -- modeled repair time (hours)
        verbosity -- what kind of output we want
    """

    # set up the column headings and descriptions
    heads = ("configuration", "durability", "PL(copies)", "PL(NRE)",
             "loss/PiB")
    legends = [
        "configuration being modeled",
        "probability of object survival",
        "probability of loss due to node failures",
        "probability of loss due to NREs during recovery",
        "expected data loss per Petabyte"
    ]
    format = ColumnPrint(heads)

    # figure out what output he wants
    headings = True
    parms = True
    descr = True
    debug = False
    if verbosity == "parameters":
        descr = False
    elif verbosity == "headings":
        parms = False
        descr = False
    elif verbosity == "data only":
        parms = False
        descr = False
        headings = False
    elif verbosity == "debug":
        debug = True

    if descr:
        print ""
        print "Column legends"
        s = format.printTime(period)
        i = 1
        while i <= len(legends):
            l = legends[i - 1]
            if i == 1:
                print "\t%d %s" % (i, l)
            else:
                print "\t%d %s (per %s)" % (i, l, s)
            i += 1

    if headings:
        format.printHeadings()

    for m in models:

        sizes = Sizes(m, capacity)
        if debug:
            print("primaries = %d" % sizes.n_primary)
            print("secondaries = %d" % sizes.n_secondary)

        rates = Rates(m, repair)
        if debug:
            print("primary HW FITs = %d" % rates.fits_primary_hw)
            print("primary SW FITs = %d" % rates.fits_primary_sw)
            print("secondary HW FITs = %d" % rates.fits_secondary_hw)
            print("secondary SW FITs = %d" % rates.fits_secondary_sw)

        # run the model
        results = Results(m, sizes, rates, period)

        # print out the report results
        s = list()
        s.append(m.descr)
        s.append(format.printDurability(results.durability))
        s.append(format.printProbability(results.p_loss_node))
        s.append(format.printProbability(results.p_loss_copy))

        l = results.p_loss_node * results.exp_loss_node
        l += results.p_loss_copy * results.exp_loss_copy
        # FIX: l *= PiB / raw capacity
        s.append(format.printFloat(l))
        format.printLine(s)
