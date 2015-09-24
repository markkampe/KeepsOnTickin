"""
Input values to the simulation, and output values from the simulation
"""
from RelyFuncts import FitRate, Pfail, Punion, multiFit
from RelyFuncts import SECOND, MINUTE, HOUR, DAY, YEAR, BILLION
from sizes import MiB, GiB, PiB, MB, GB

#
# TODO
#   This model assumes that disjoint primaries and secondaries.
#   If we want to support peer-to-peer mirroring, we need to:
#       1. Model: we must apportion memory between primary and secondary copies
#       2. Results: we lose distinction between primary and secondary failures
#       3. Results: node failure represents both primary and secondary failures
#       4. Results: surviving node count for subsequent failures changes


class Model:
    """ a collection of simulation parameters """

    def __init__(self, description):
        """ initialize default simulation parameters """

        # name of modeled configuration
        self.descr = description

        # hardware configuration parameters
        self.cache_1 = 1 * GB   # cache per primary node
        self.cache_2 = 40 * GB  # cache per secondary node
        self.nv_1 = False       # non-volatile primary
        self.nv_2 = True        # non-volatile secondary
        self.n_power = 1        # total power supplies/node
        self.m_power = 1        # minimum power supplies/node
        self.n_fan = 2          # total fans/node
        self.m_fan = 1          # minimum fans/node
        self.n_nic = 2          # total NICs/node
        self.m_nic = 1          # minimum NICs/node

        # architectural parameters
        self.copies = 3         # primary + secondary
        self.decluster = 1      # primary->secondary declustering
        self.symmetric = False  # distinct primaries and secondaries
        self.remirror = True    # remirror if faster than flush
        self.max_dirty = 250 * MB   # max dirty data in primary

        # performance parameters
        self.rate_flush = 50 * MiB      # flush to backing store
        self.rate_mirror = 100 * MiB    # remirroring rate
        self.time_detect = 30   # detect failure/initiate recovery
        self.time_timeout = 10  # TCP retransmit timeout

        # utilization parameters
        self.cap_used = 0.75    # how full is the backing store
        self.dedup = 3          # overall dedup savings (CAP/x)
        self.lun_active = 0.05  # fraction of LUNs in use
        self.lun_size = 50 * GB     # average LUN size

        # load parameters
        self.bsize = 4096       # expected block size
        self.prim_vms = 12      # average number of VMs per primary
        self.lun_per_vm = 1.5   # average number of LUNs per VM
        self.iops = 500         # avg IOPS per VM
        self.write_fract = 0.5  # fraction of write operations
        self.write_aggr = 4     # savings from write aggregation

        # failure rates for which there is real data
        self.f_ctlr = 4000      # per board
        self.f_power = 1642     # per power supply
        self.f_fan = 518        # per fan
        self.f_nic = 200        # per NIC
        self.f_dram = 10        # per MB
        self.uer_nvm = 1.0E-17  # typical number for MLC nand
        self.f_sw = FitRate(4, YEAR)    # node panics

        # magic numbers we can only guess at
        self.sw_hard = 0.01     # fraction of panics that don't reboot
        self.dram_2bit = 0.01   # fraction of multi-bit DRAM errors


class Sizes:
    """ The key capacities that drive the result """
    def __init__(self, m, capacity=1 * PiB, debug=False):
        """ compute the sizes of the cache and number of nodes
            model -- the base simulation parameters
            capacity -- capacity of the backing store
            debug -- enable diagnostic output
        """

        # figure out how many LUNs and VMs we can support
        self.total = capacity
        used = capacity * m.cap_used * m.dedup
        luns = used / m.lun_size
        active = luns * m.lun_active
        vms = active / m.lun_per_vm

        # figure out how many primaries and secondaries that means
        self.n_primary = vms / m.prim_vms
        if (m.symmetric):
            self.n_secondary = self.n_primary
            self.m_cache_1 /= m.copies      # NOTE:
            # This seems wasteful in that we are reserving much more remote
            # cache mirror than we have dirty pages, but the reward is
            # greatly simplified recovery, all copies being identical.
        else:
            cached = self.n_primary * m.cache_1
            self.n_secondary = cached * (m.copies - 1) / m.cache_2

        # compute what fraction of each active LUN we can cache
        lsize = m.lun_per_vm * m.lun_size
        self.cache_tot = m.cache_1 / lsize
        self.cache_dirty = m.max_dirty / lsize

        # compute the implied primary/secondary fan-out/fan-in
        if m.copies < 2:
            self.fan_out = 0
            self.fan_in = 0
        else:
            self.fan_out = min(m.decluster, m.copies - 1)
            self.fan_in = self.fan_out * self.n_primary / self.n_secondary


class Rates:
    """ The key rates that drive the result """
    def __init__(self, m, repair=24 * HOUR, debug=False):
        """ compute the sizes of the cache and number of nodes
            model -- the base simulation parameters
            repair -- time (HOURS) to replace a failed component
            debug -- enable diagnostic output
        """

        # attempt a bottom-up h/w node FITs computation
        power_fits = multiFit(m.f_power, m.n_power, m.m_power, repair)
        fan_fits = multiFit(m.f_fan, m.n_fan, m.m_fan, repair)
        nic_fits = multiFit(m.f_nic, m.n_nic, m.m_nic, repair)
        self.fits_1_loss = m.f_ctlr + power_fits + fan_fits + nic_fits
        self.fits_2_loss = m.f_ctlr + power_fits + fan_fits + nic_fits

        # any hard h/w or s/w failure takes out any copy
        self.fits_1_loss += m.f_sw * m.sw_hard
        self.fits_2_loss += m.f_sw * m.sw_hard

        # volatile copies can be taken out by reboots and double bit errors
        #
        #   Because I have DRAM reliability characterized as a FIT rate,
        #   I simply include double-bit errors in the overall data loss
        #   rate.  Because I have NVRAM reliability characterized as a
        #   UBER, its contribution is computed separately.
        #
        if not m.nv_1:
            self.fits_1_loss += m.f_sw
            self.fits_1_loss += m.cache_1 * m.f_dram * m.dram_2bit / MB
        if not m.nv_2:
            self.fits_2_loss += m.f_sw
            self.fits_2_loss += m.cache_2 * m.f_dram * m.dram_2bit / MB

        # compute a few other interesting cache rate/use parameters
        #   Note: we have modeled write-aggregation as a constant,
        #         but in actuality it is probably a function of the
        #         the interval between flushes
        self.fract_dirty = float(m.max_dirty) / m.cache_1
        self.writes_in = m.bsize * m.iops * m.write_fract
        self.new_writes_in = self.writes_in / m.write_aggr
        self.interval_flush = float(m.max_dirty) / self.new_writes_in
        self.cache_life = float(m.cache_1) / self.new_writes_in


class Results:
    """ The results of a simulation """
    def __init__(self, model, sizes, rates, period=1*YEAR, debug=False):
        """ compute the probability of data loss
                model -- base simulation parameters
                sizes -- key capacities and counts
                rates -- key fit rates
                period -- period (hours) to be analyzed
                debug -- enable diagnostic output

            NOTE:
                In this method, we begin with an initial failure:
                    1. a primary goes down and loses data
                    2. a primary suffers an NRE and loses data
                    3. a secondary goes down and loses data
                We then model the probability of loss for the data
                that was affected by the initial failure.

                In cases where the probabilities are small, I
                lazily use the expected number of failures
                rather than the 1-P(exp,n=0) ... but this is
                (if anything) a conservative approximation.
        """

        # move stuff with long names into locals
        fi = sizes.fan_in           # primaries per secondary
        fo = sizes.fan_out          # secondaries per primary
        n1 = sizes.n_primary        # number of primaries in system
        n2 = sizes.n_secondary      # number of secondaries in system
        l1 = rates.fits_1_loss      # primary loss FIT rate
        l2 = rates.fits_2_loss      # secondary loss FIT rate
        dirty = model.max_dirty     # maximum dirty data / primary
        cp = model.copies - 1       # number of secondary copies
        dc = model.decluster        # primary->secondary dispersion
        sym = model.symmetric       # peer-to-peer primary/secondary model

        # Compute the detection and recovery times
        Tt = model.time_timeout * SECOND
        Td = model.time_detect * SECOND
        b2f = dirty / dc
        Ts = (b2f / model.rate_flush * SECOND)
        if model.remirror and model.rate_mirror > model.rate_flush:
            Tp = (b2f / model.rate_mirror) * SECOND
        else:
            Tp = Ts

        # number of expected annual primary/secondary failures

        # accumulated results (segregated by case)
        #   compounded errors make it impossible to completely
        #   separate node induced from copy induced errors, so
        #   we base this distinction on "first cause"
        #
        P1 = 0          # node failure, starting with primary
        P2 = 0          # data error, starting with primary
        P3 = 0          # node failure, starting with secondary
        P4 = 0          # data loss, after secondary node failure
        L = dirty / dc  # expected loss if things go bad

        # compute the total recovery (detect+flush) times
        tr_d = model.time_detect
        tr_r = rates.time_flush
        Tr = (tr_d + tr_r) * SECOND

        # Scenario 1a: primary fails during modeled period
        P1 = 1 - Pfail(l1 * n1, period, 0)
        if debug:
            print("P1first(%d, T=%e)=%e -> P1=%e" % (n1, period, P1, P1))

        # Scenario 2a: primary suffers an NRE during modeled period
        if model.nv_1:
            bits = 8 * rates.writes_in / SECOND
            errs = bits * model.uer_nvm * BILLION
        else:
            errs = 0
        P2 = 1 - Pfail(n1 * errs, period, 0)
        if debug:
            print("P1first(%d, T=%e) errs=%e -> P2=%e" %
                  (n1, period, errs, P2))

        # Scenario 1b/2b: all secondary copies are lost
        i = cp
        surv = n2
        while i > 0:
            # at most fan_out secondaries participate in recovery
            Pnext = 1 - Pfail(l2 * min(fo, surv), Tr, 0)
            if model.nv_2:
                # all of the secondaries combined read dirty bytes
                bits = 8 * dirty
                errs = bits * model.uer_nvm
            else:
                errs = 0
            if P2 == 0:
                P2 = P1 * errs  # these can be attributed to NRE
                P1 *= Pnext
            else:
                P1 *= (Pnext + errs)
                P2 *= (Pnext + errs)
            if debug:
                print("P2next(%d, Tr=%e) = %e, errs=%e -> P1=%e" %
                     (i, Tr, Pnext, errs, P1))
                print("P2next(%d, Tr=%e) = %e, errs=%e -> P2=%e" %
                     (i, Tr, Pnext, errs, P1))
            i -= 1
            surv -= 1

        # Scenario 3a: secondary fails during modeled period
        P3 = 1 - Pfail(l2 * n2, period, 0)
        if debug:
            print("P2first(%d, T=%e) -> P3=%e" % (n2, period, P3))

        # Scenario 3b: primary fails during flush
        Pnext = 1 - Pfail(l1 * fi, Tr, 0)
        if model.nv_1:
            # each affected primary will read dirty/fo bytes
            bits = 8 * fi * dirty / dc
            errs = bits * model.uer_nvm
        else:
            errs = 0
        P4 = P3 * errs      # these can be attributed to NRE
        P3 *= Pnext
        if debug:
            print("P1next(%d, Tr=%e) = %e, errs=%e -> P3=%e" %
                 (fi, Tr, Pnext, errs, P3))

        # Scenario 3c: all copies fail during recovery
        i = cp - 1
        surv = n2 - 1
        while i > 0:
            # at most fan_out secondaries participate in recovery
            # PROBABLY WRONG ... BUT LOW IMPACT
            Pnext = 1 - Pfail(l2 * min(fo, surv), Tr, 0)
            if model.nv_2:
                # all of the secondaries combined read sz bytes
                bits = 8 * dirty / fo       # FIX
                errs = bits * model.uer_nvm
            else:
                errs = 0
            P3 *= (Pnext + errs)
            P4 *= (Pnext + errs)
            if debug:
                print("P2next(%d, Tr=%e) = %e, errs=%e -> P3=%e" %
                     (i, Tr, Pnext, errs, P3))
            i -= 1
            surv -= 1

        # tally up the loss probabilities and expentancies
        self.p_loss_node = Punion(P1, P3)
        self.p_loss_copy = Punion(P2, P4)
        self.p_loss_all = Punion(P1, P2, P3, P4)
        self.exp_loss_all = self.p_loss_all * L

        # compute the durability
        d = 1 - self.p_loss_all
        self.durability = d
        self.nines = 0
        while d > .9:
            self.nines += 1
            d -= .9
            d *= 10
