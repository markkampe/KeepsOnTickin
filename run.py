#

from sizes import MB, MiB, GB, PiB
from RelyFuncts import YEAR, HOUR

from Model import Model, Sizes, Rates, Results
from ColumnPrint import ColumnPrint, printTime, printSize, printFloat, printExp
from ColumnPrint import printDurability, printProbability


#
# This routine can be called at different times when different amounts
# of information are available.  It tries to do the most meaningful and
# readable possible presentation with the information it is given.
#
def printParms(m, s, r):
    """ print out selected parameters for this test
        model -- the model to be printed
        sizes -- the computed cluster sizes
        rates -- the computed FIT rates
    """
    print ""
    print "System Parameters:"
    print("\tcache size:\tprimary=%dMB, secondary=%dMB" %
          (m.cache_1/MB, m.cache_2/MB))
    print("\tcapacity:  \tused=%d%%, active=%d%%" %
          (m.cap_used * 100, m.lun_active * 100))
    print("\tLUNs:      \tsize=%dGB, %3.1f/VM, %d/primary" %
          (m.lun_size / GB, m.lun_per_vm,
           m.lun_per_vm * m.prim_vms))
    print("\tI/O load:  \t%d(%dK)IOPS/VM, %d%% writes / %d (aggregation)" %
          (m.iops, m.bsize/1024, 100 * m.write_fract, m.write_aggr))
    if s is not None:
        print("\tmirroring: \tcopies=%d, decluster=%d, max_dirty=%dMB" %
              (m.copies, m.decluster, m.max_dirty/MB))
        if (m.symmetric):
            print("\tcluster:   \tn=%d, fan-out=%d, fan-in=%d" %
                  (s.n_primary, s.fan_out, s.fan_in))
        else:
            print("\tcluster:   \tnP=%d, nS=%d, fan-out=%d, fan-in=%d" %
                  (s.n_primary, s.n_secondary,
                   s.fan_out, s.fan_in))
    else:
        print("\tmirroring: \tdecluster=%d, max_dirty=%dMB" %
              (m.decluster, m.max_dirty/MB))

    print("\tdetection:  \tnodefail=%ds, timeout=%ds" %
          (m.time_detect, m.time_timeout))
    if (m.remirror):
        print("\trecover:  \tflush=%dMiB/s, remirror=%dMiB/s" %
              (m.rate_flush/MiB, m.rate_mirror/MiB))
    else:
        print("\trecovery:  \tflush=%dMiB/s" %
              (m.rate_flush/MiB))

    if r is not None or s is not None:
        print("Cache Use Statistics:")
        if s is not None:
            print("\tcache/LUN: \tcached=%.1f%%, dirty=%.1f%%" %
                 (100 * s.cache_tot, 100 * s.cache_dirty))
        if r is not None:
            print("\tcache/Prim:\tdirty=%.1f%%, lifetime=%.3fs, DWPD=%d" %
                  (100 * r.fract_dirty, r.cache_life, r.dwpd))

    print("Reliability Parameters:")
    print("\tcontroller\t%d FITs per" % (m.f_ctlr))
    print("\tDRAM:     \t%d FITs/MB (%.2f%% uncorrectable)" %
          (m.f_dram, m.dram_2bit * 100))
    print("\tNVRAM:     \tR-BER=%6.2e, W-BER=%6.2e" %
          (m.ber_nvm_r, m.ber_nvm_w))
    print("\tfans:     \t%d/%d, %d FITs per, MTTR=%dh" %
          (m.m_fan, m.n_fan, m.f_fan, m.time_repair/HOUR))
    print("\tpower:    \t%d/%d, %d FITs per, MTTR=%dh" %
          (m.m_power, m.n_power, m.f_power, m.time_repair/HOUR))
    print("\tNICs:     \t%d/%d, %d FITs per, MTTR=%dh" %
          (m.m_nic, m.n_nic, m.f_nic, m.time_repair/HOUR))
    print("\tsoftware:  \tFITs=%d, hard=%.2f%%" % (m.f_sw, 100 * m.sw_hard))
    if r is not None:
        if (m.symmetric):
            print("\tloss:      \tFITs=%d" % (r.fits_1_loss))
        else:
            print("\tloss(1):   \tFITs=%d" % (r.fits_1_loss))
            print("\tloss(2):   \tFITs=%d" % (r.fits_2_loss))


def run(models, verbosity="default",
        capacity=1*PiB, period=1*YEAR):
    """ execute a single model and print out the results
        models -- list of models to be run
        verbosity -- what kind of output we want
        capacity -- total system capacity (bytes)
        period -- modeled time period (hours)
    """

    # define the column headings
    heads = ("configuration", "<p,s>/PiB", "durability",
             "PL(node)", "PL(NRE)", "BW(recov)", "T(recov)")
    legends = [
        "configuration being modeled",
        "<primaries, secondaries> per petabyte",
        "probability of object survival*",
        "probability of loss due to node failures*",
        "probability of loss due to NREs during recovery*",
        "peak recovery bandwidth",
        "max detect/recovery time"
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
    if verbosity == "parameters":   # per-test parameters
        parm1 = False
        descr = False
    elif verbosity == "headings":   # output and headings
        parm1 = False
        parms = False
        descr = False
    elif verbosity == "data":   # minimal - just the output
        parm1 = False
        parms = False
        descr = False
        headings = False
    elif verbosity == "all":    # pretty much everyting
        debug = True
        parm1 = False
    elif verbosity == "debug":  # debug only
        debug = True
        headings = False
        parm1 = False
        parms = False
        descr = False
    else:
        parms = False

    # print out basic parameters (assumed not to change)
    if parm1:
        printParms(models[0], None, None)

    # print out column legends
    if descr:
        print ""
        print "Column legends:"
        s = printTime(period)
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
        rates = Rates(m, debug)

        # print out the model parameters
        if parms:
            printParms(m, sizes, rates)

        # compute and print the reliability
        results = Results(m, sizes, rates, period, debug)
        s = list()
        s.append(m.descr)
        if m.symmetric:
            s.append("<%d>" % (sizes.n_primary))
        else:
            s.append("<%d,%d>" % (sizes.n_primary, sizes.n_secondary))
        s.append(printDurability(results.durability))
        s.append(printProbability(results.p_loss_node))
        s.append(printProbability(results.p_loss_copy))
        bw = max(results.bw_sfail, results.bw_pfail)
        if bw > 0:
            s.append(printSize(bw, 1000) + "/s")
            s.append(printFloat(results.Trecov)+"s")
        else:
            s.append("n/a")
            s.append("n/a")
        format.printLine(s)
