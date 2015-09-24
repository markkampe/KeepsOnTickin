#

from sizes import MB, MiB, GB, PiB
from RelyFuncts import YEAR, HOUR

from Model import Model, Sizes, Rates, Results
from ColumnPrint import ColumnPrint


def printParms(m, s, r):
    """ print out selected parameters for this test
        model -- the model to be printed
        sizes -- the computed cluster sizes
        rates -- the computed FIT rates
    """
    print ""
    print "Parameters:"
    dram = "DRAM, %d FITs/MB (%f uncorrectable)" %\
           (m.f_dram, m.dram_2bit)
    nvram = "NVRAM, UBER=%e" % (m.uer_nvm)
    print("\tprimary:  \t%dMB %s" %
          (m.cache_1/MB, nvram if m.nv_1 else dram))
    if not m.symmetric:
        print("\tsecondary:\t%dMB %s" %
              (m.cache_2/MB, nvram if m.nv_2 else dram))
    print("\tcapacity:  \tused=%d%%, active=%d%%" %
          (m.cap_used * 100, m.lun_active * 100))
    print("\tLUNs:      \tsize=%dGB, %3.1f/VM, %d/primary" %
          (m.lun_size / GB, m.lun_per_vm,
           m.lun_per_vm * m.prim_vms))
    print("\tI/O load:  \t%d(%dK)IOPS/VM, %d%% writes / %d (aggregation)" %
          (m.iops, m.bsize/1024, 100 * m.write_fract, m.write_aggr))
    print("\tdetection:  \tnodefail=%ds, timeout=%ds" %
          (m.time_detect, m.time_timeout))
    if (m.remirror):
        print("\trecover:  \tmax_dirty=%dMB, flush=%dMiB/s, remirror=%dMiB/s" %
              (m.max_dirty/MB, m.rate_flush/MiB, m.rate_mirror/MiB))
    else:
        print("\trecovery:  \tmax_dirty=%dMB, flush=%dMiB/s" %
              (m.max_dirty/MB, m.rate_flush/MiB))
    print("\tsoftware:  \tFITs=%d, hard=%6.3f%%" %
          (m.f_sw, 100 * m.sw_hard))
    if s is not None:
        print("\tcopies:    \t%d, decluster=%d" %
              (m.copies, m.decluster))
        if (m.symmetric):
            print("\tcluster:   \tn=%d, fan-out=%d, fan-in=%d" %
                  (s.n_primary, s.fan_out, s.fan_in))
        else:
            print("\tcluster:   \tnP=%d, nS=%d, fan-out=%d, fan-in=%d" %
                  (s.n_primary, s.n_secondary,
                   s.fan_out, s.fan_in))
        print("\tcache/LUN: \ttotal=%f, dirty=%f" %
             (s.cache_tot, s.cache_dirty))
    if r is not None:
        print("\tcache/Prim:\tdirty=%f, lifetime=%fs" %
              (r.fract_dirty, r.cache_life))
        if (m.symmetric):
            print("\tloss:      \tFITs=%d" % (r.fits_1_loss))
        else:
            print("\tloss(1):   \tFITs=%d" % (r.fits_1_loss))
            print("\tloss(2):   \tFITs=%d" % (r.fits_2_loss))


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
        printParms(models[0], None, None)

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
            printParms(m, sizes, rates)

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
