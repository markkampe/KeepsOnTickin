#

from sizes import PiB
from RelyFuncts import YEAR, HOUR

from Model import Model, Sizes, Rates, Results
from ColumnPrint import ColumnPrint


def printParms(model, rates):
    """ print out selected parameters for this test
        model -- the model to be printed
        rates -- the computed FIT rates
    """
    print ""
    print "Parameters:"
    dram = "%dGB DRAM, %d FITs/GB, 2-bit=%f" %\
           (model.sz_dram, model.f_dram, model.dram_2bit)
    nvram = "%dGB NVRAM, UBER=%e" % (model.sz_nvram, model.uer_nvm)
    if model.n_nvram_1 > 0:
        print("\tprimary:  \t%dx%s" % (model.n_nvram_1, nvram))
    else:
        print("\tprimary:  \t%dx%s" % (model.n_dram_1, dram))
    if model.n_nvram_2 > 0:
        print("\tsecondary:\t%dx%s" % (model.n_nvram_2, nvram))
    elif model.n_dram_2 > 0:
        print("\tsecondary:\t%dx%s" % (model.n_dram_2, dram))
    print("\tcopies:    \t%d, fan-out=%d, fan-in=%d" %
          (model.copies, model.fan_out, model.fan_in))
    print("\tcapacity:  \tused=%d%%, active=%d%%" %
          (model.cap_used * 100, model.lun_active * 100))
    print("\tcache:     \tcached=%d%%, dirty=%d%%" %
          (model.lun_cached * 100, model.lun_dirty * 100))
    print("\tdet/recov: \t%ds, %dMB/s" %
          (model.time_detect, model.rate_flush/1000000))
    print("\tload:      \t%d/%dx%d byte writes/s" %
          (model.write_iops, model.write_reduce, model.bsize))
    print("\tsoftware:  \tFITs=%d, hard=%f" % (model.f_sw, model.sw_hard))

    if rates is not None:
        print("\tloss(1):   \tFITs=%d" % (rates.fits_1_loss))
        print("\tloss(2):   \tFITs=%d" % (rates.fits_2_loss))


def run(models, verbosity="default",
        capacity=1*PiB, period=1*YEAR, repair=24*HOUR):
    """ execute a single model and print out the results
        models -- list of models to be run
        verbosity -- what kind of output we want
        capacity -- total system capacity (bytes)
        period -- modeled time period (hours)
        repair -- modeled repair time (hours)
    """

    # define the column headings
    heads = ("configuration", "<p,s>/PiB", "durability",
             "PL(node)", "PL(NRE)", "loss/PiB")
    legends = [
        "configuration being modeled",
        "<primaries, secondaries> per petabyte",
        "probability of object survival*",
        "probability of loss due to node failures*",
        "probability of loss due to NREs during recovery*",
        "expected data loss per petabyte*"
    ]

    # figure out the longest description
    maxlen = len(heads[0])
    for m in models:
        l = len(m.descr)
        if l > maxlen:
            maxlen = l

    format = ColumnPrint(heads, maxdesc=maxlen)

    # figure out what output he wants
    parm1 = True        # basic parameters at front
    descr = True        # descriptions of columns
    headings = True     # column headings
    parms = True        # all parameters for every model
    debug = False       # diagnostic output
    if verbosity == "parameters":
        parm1 = False
        descr = False
    elif verbosity == "headings":
        parm1 = False
        parms = False
        descr = False
    elif verbosity == "data":
        parm1 = False
        parms = False
        descr = False
        headings = False
    elif verbosity == "debug":
        debug = True
        parm1 = False
    else:
        parms = False

    # print out basic parameters (assumed not to change)
    if parm1:
        printParms(models[0], None)

    # print out column legends
    if descr:
        print ""
        print "Column legends:"
        s = format.printTime(period)
        i = 1
        while i <= len(legends):
            l = legends[i - 1]
            if l.endswith('*'):
                print "\t%d %s (per %s)" % (i, l, s)
            else:
                print "\t%d %s" % (i, l)
            i += 1

    # print out column headings
    if headings:
        format.printHeadings()

    for m in models:
        # compute sizes and rates
        sizes = Sizes(m, capacity, debug)
        rates = Rates(m, repair, debug)

        # print out the model parameters
        if parms:
            printParms(m, rates)

        # compute and print the reliability
        results = Results(m, sizes, rates, period, debug)
        s = list()
        s.append(m.descr)
        s.append("<%d,%d>" % (sizes.n_primary, sizes.n_secondary))
        s.append(format.printDurability(results.durability))
        s.append(format.printProbability(results.p_loss_node))
        s.append(format.printProbability(results.p_loss_copy))
        s.append(format.printFloat(results.exp_loss_all))
        format.printLine(s)
