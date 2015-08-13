"""
Input values to the simulation, and output values from the simulation
"""
from RelyFuncts import SECOND, MINUTE, HOUR, DAY, YEAR, FitRate, Pfail, allFail

from sizes import MiB, GiB, PiB, GB

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
        self.n_dram_1 = 16      # DRAM DIMMs / primary node
        self.n_dram_2 = 0       # DRAM DIMMs / secondary node
        self.n_nvram_1 = 0      # NVRAM DIMMs / primary node
        self.n_nvram_2 = 16     # NVRAM DIMMs / secondary node
        self.n_power = 1        # total power supplies/node
        self.m_power = 1        # minimum power supplies/node
        self.n_fan = 2          # total fans/node
        self.m_fan = 1          # minimum fans/node
        self.n_nic = 2          # total NICs/node
        self.m_nic = 1          # minimum NICs/node
        self.sz_nvram = 40      # GB / NVRAM DIMM
        self.sz_dram = 2        # GB / DRAM DIMM

        # architectural parameters
        self.rate_flush = 50 * MiB      # flush to backing store
        self.time_detect = 30   # detect failure/initiate recovery
        self.fan_out = 4        # secondary/primary
        self.fan_in = 4         # primary/secondary
        self.copies = 2         # secondary copies

        # utilization parameters
        self.cap_used = 0.75    # how full is the backing store
        self.lun_active = 0.05  # fraction of LUNs in use
        self.lun_cached = 0.25  # fraction of active LUN in cache
        self.lun_dirty = 0.10   # dirty fraction of cached blocks

        # load parameters
        self.bsize = 4096       # expected block size
        self.write_iops = 500   # avg writes per second per primary
        self.write_reduce = 9   # savings from aggregation/deduplication

        # failure rates for which there is real data
        self.f_ctlr = 4000      # per board
        self.f_power = 1642     # per power supply
        self.f_fan = 518        # per fan
        self.f_nic = 200        # per NIC
        self.f_dram = 10000     # per GB
        self.uer_nvm = 1.0E-17  # typical number for MLC nand
        self.f_sw = FitRate(4, YEAR)    # node panics

        # magic numbers we can only guess at
        self.sw_hard = 0.01     # fraction of panics that don't reboot
        self.dram_2bit = 0.01   # fraction of multi-bit DRAM errors


class Sizes:
    """ The key capacities that drive the result """
    def __init__(self, model, capacity=1 * PiB, debug=False):
        """ compute the sizes of the cache and number of nodes
            model -- the base simulation parameters
            capacity -- capacity of the backing store
            debug -- enable diagnostic output
        """

        # note the total system capacity
        self.total = capacity

        # figure out total amount of data to be cached
        used = capacity * model.cap_used
        active = used * model.lun_active
        cached = active * model.lun_cached

        # figure out how much cache we can store on a primary
        if model.n_nvram_1 != 0:
            self.primary = model.n_nvram_1 * model.sz_nvram * GB
        else:
            self.primary = model.n_dram_1 * model.sz_dram * GB

        # figure out how much cache we can store on a secondary
        if model.n_nvram_2 != 0:
            self.secondary = model.n_nvram_2 * model.sz_nvram * GB
        else:
            self.secondary = model.n_dram_2 * model.sz_dram * GB

        # figure out how many primary/secondary nodes we need
        self.n_primary = cached / self.primary
        if self.secondary > 0:
            self.n_secondary = cached * model.copies / self.secondary
        else:
            self.n_secondary = 0


class Rates:
    """ The key rates that drive the result """
    def __init__(self, m, repair=24 * HOUR, debug=False):
        """ compute the sizes of the cache and number of nodes
            model -- the base simulation parameters
            repair -- time (HOURS) to replace a failed component
            debug -- enable diagnostic output
        """

        # attempt a bottom-up h/w node FITs computation
        power_fits = allFail(m.f_power, m.n_power, m.m_power, repair)
        fan_fits = allFail(m.f_fan, m.n_fan, m.m_fan, repair)
        nic_fits = allFail(m.f_nic, m.n_nic, m.m_nic, repair)
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
        self.n_dram_1 = 16      # DRAM DIMMs / primary node
        if m.n_dram_1 != 0:
            self.fits_1_loss += m.f_sw
            self.fits_1_loss += m.n_dram_1 * m.sz_dram * m.f_dram
        if m.n_dram_2 != 0:
            self.fits_2_loss += m.f_sw
            self.fits_1_loss += m.n_dram_2 * m.sz_dram * m.f_dram


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
        """

        # move stuff with long names into locals
        fi = model.fan_in           # primaries per secondary
        fo = model.fan_out          # secondaries per primary
        n1 = sizes.n_primary        # number of primaries in system
        n2 = sizes.n_secondary      # number of secondaries in system
        l1 = rates.fits_1_loss      # primary loss FIT rate
        l2 = rates.fits_2_loss      # secondary loss FIT rate
        sz = sizes.primary          # cached data on primary
        cp = model.copies           # number of secondary copies

        # accumulated results (segregated by case)
        #   compounded errors make it impossible to completely
        #   separate node induced from copy induced errors, so
        #   we base this distinction on "first cause"
        #
        P1 = 0          # node failure, starting with primary
        P2 = 0          # data error, starting with primary
        P3 = 0          # node failure, starting with secondary
        P4 = 0          # data loss, after secondary node failure
        L = sz / fo     # expected loss if things go bad

        # compute the total recovery (detect+flush) times
        tr_d = model.time_detect
        tr_r = (sz / (fo * model.rate_flush))
        self.Tr = (tr_d + tr_r) * SECOND
        if debug:
            print("Tr = %e, det=%ds, recov=%ds" % (self.Tr, tr_d, tr_r))

        # Scenario 1a: primary fails during modeled period
        P1 = 1 - Pfail(l1 * n1, period, 0)
        if debug:
            print("P1first(%d, T=%e)=%e -> P1=%e" % (n1, period, P1, P1))

        # Scenario 2a: primary suffers an NRE during modeled period
        if model.n_nvram_1 > 0:
            bits = 8 * model.bsize * model.write_iops / model.write_reduce
            bits *= period / SECOND
            errs = bits * model.uer_nvm
        else:
            errs = 0
        P2 = errs       # these can be attributed to NRE
        if debug:
            print("P1first(%d, T=%e) errs=%e -> P2=%e" %
                  (n1, period, errs, P2))

        # Scenario 1b/2b: all secondary copies are lost
        i = cp
        surv = n2
        while i > 0:
            # at most fan_out secondaries participate in recovery
            Pnext = 1 - Pfail(l2 * min(fo, surv), self.Tr, 0)
            if model.n_nvram_2 > 0:
                # all of the secondaries combined read sz bytes
                bits = 8 * sz
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
                     (i, self.Tr, Pnext, errs, P1))
                print("P2next(%d, Tr=%e) = %e, errs=%e -> P2=%e" %
                     (i, self.Tr, Pnext, errs, P1))
            i -= 1
            surv -= 1

        # Scenario 3a: secondary fails during modeled period
        P3 = 1 - Pfail(l2 * n2, period, 0)
        if debug:
            print("P2first(%d, T=%e) -> P3=%e" % (n2, period, P3))

        # Scenario 3b: primary fails during flush
        Pnext = 1 - Pfail(l1 * fi, self.Tr, 0)
        if model.n_nvram_1 > 0:
            # each affected primary will read sz/fo bytes
            bits = 8 * fi * sz / fo
            errs = bits * model.uer_nvm
        else:
            errs = 0
        P4 = P3 * errs      # these can be attributed to NRE
        P3 *= Pnext
        if debug:
            print("P1next(%d, Tr=%e) = %e, errs=%e -> P3=%e" %
                 (fi, self.Tr, Pnext, errs, P3))

        # Scenario 3c: all copies fail during recovery
        i = cp - 1
        surv = n2 - 1
        while i > 0:
            # at most fan_out secondaries participate in recovery
            # PROBABLY WRONG ... BUT LOW IMPACT
            Pnext = 1 - Pfail(l2 * min(fo, surv), self.Tr, 0)
            if model.n_nvram_2 > 0:
                # all of the secondaries combined read sz bytes
                bits = 8 * sz / model.fan_out   # FIX
                errs = bits * model.uer_nvm
            else:
                errs = 0
            P3 *= (Pnext + errs)
            P4 *= (Pnext + errs)
            if debug:
                print("P2next(%d, Tr=%e) = %e, errs=%e -> P3=%e" %
                     (i, self.Tr, Pnext, errs, P3))
            i -= 1
            surv -= 1

        # tally up the loss probabilities and expentancies
        self.p_loss_node = P1 + P3
        self.p_loss_copy = P2 + P4
        self.p_loss_all = P1 + P2 + P3 + P4
        self.exp_loss_all = (P1 + P2 + P3 + P4) * L

        # compute the durability
        d = 1 - self.p_loss_all
        self.durability = d
        self.nines = 0
        while d > .9:
            self.nines += 1
            d -= .9
            d *= 10
