"""
Input values to the simulation, and output values from the simulation
"""
from RelyFuncts import SECOND, MINUTE, HOUR, DAY, YEAR, FitRate, allFail

from sizes import MiB, GiB, PiB


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
        self.sz_nvram = 40      # gigabytes / NVRAM DIMM
        self.sz_dram = 2        # gigabytes / DRAM DIMM

        # architectural parameters
        self.rate_flush = 50 * MiB      # flush to backing store
        self.time_detect = 30 * SECOND  # failure detect time
        self.fan_out = 4                # secondary/primary
        self.fan_in = 4                 # primary/secondary
        self.copies = 2                 # secondary copies

        # utilization parameters
        self.cap_used = 0.75            # how full is the backing store
        self.luns_active = 0.05         # fraction of LUNs in use
        self.luns_cached = 0.25         # fraction of active LUN in cache
        self.luns_dirty = 0.10          # dirty fraction of cached blocks

        # failure rates for which there is real data
        self.f_ctlr = 4000      # per board
        self.f_power = 1642     # per power supply
        self.f_fan = 518        # per fan
        self.f_nic = 200        # per NIC
        self.f_dram = 50        # DRAM DIMM
        self.uer_nvm = 1.0E-17  # typical number for MLC nand
        self.f_sw = FitRate(4, YEAR)    # node panics

        # magic numbers we can only guess at
        self.sw_hard = 0.01     # fraction of panics that don't reboot
        self.dram_2bit = 0.02    # fraction of multi-bit errors


class Sizes:
    """ The key capacities that drive the result """
    def __init__(self, model, capacity=1 * PiB):
        """ compute the sizes of the cache and number of nodes
            model -- the base simulation parameters
            capacity -- capacity of the backing store
        """

        # note the total system capacity
        self.total = capacity

        # figure out how much data we are keeping in cache
        used = capacity * model.cap_used
        active = used * model.luns_active
        cached = active * model.luns_cached
        GiB_1 = cached / GiB
        GiB_2 = cached * model.copies / GiB

        # figure out how much cache we can store on a primary
        if model.n_nvram_1 == 0:
            self.primary = model.n_dram_1 * model.sz_dram
        else:
            self.primary = model.n_nvram_1 * model.sz_nvram

        # figure out how much cache we can store on a secondary
        if model.n_nvram_2 == 0:
            self.secondary = model.n_dram_2 * model.sz_dram
        else:
            self.secondary = model.n_nvram_2 * model.sz_nvram

        # figure out how many primaries and secondaries we need
        self.n_primary = GiB_1 / self.primary
        self.n_secondary = GiB_2 / self.secondary


class Rates:
    """ The key rates that drive the result """
    def __init__(self, m, repair=24 * HOUR):
        """ compute the sizes of the cache and number of nodes
            model -- the base simulation parameters
            repair -- time (HOURS) to replace a failed component
        """

        # attempt a bottom-up h/w node FITs computation
        power_fits = allFail(m.f_power, m.n_power, m.m_power, repair)
        fan_fits = allFail(m.f_fan, m.n_fan, m.m_fan, repair)
        nic_fits = allFail(m.f_nic, m.n_nic, m.m_nic, repair)
        self.fits_primary_hw = m.f_ctlr + power_fits + fan_fits + nic_fits
        self.fits_secondary_hw = m.f_ctlr + power_fits + fan_fits + nic_fits

        # estimate hard s/w failures as a fraction of all s/w failures
        self.fits_primary_sw = m.f_sw * m.sw_hard
        self.fits_secondary_sw = m.f_sw * m.sw_hard

        # estimate hard DRAM failures as a fraction of soft ones
        self.f_dram_hard = m.f_dram * m.dram_2bit

        # FIX calc memory failures resulting in resets of non-persistent copies
        # FIX calc memory failures resulting in loss of persistent copies

        # DRAM trivia
        #   (a) 1 DRAM fault every 6-7 hours
        #       29% of errors are non-recurring
        #       25K-75K/B device hours (for a few Gig?)
        #   (b) cosmic ray ~10-100 FIT/MB
        #   double bit errors are 1-5% of single bit errors
        # figure out how much data flows through a primary
        # figure out how much data flows through a secondary
        # figure out what that means for UBERs in the secondary
        # recalculate complex multi-component FIT rates
        #f_hw_hard = self.hw_hard
        #f_hw_hard += self.f_mem * self.mem_dimm * self.mem_hard

        #f_hw_soft = 1     # FIX ... use UBER
        #f_hw_hard += f_hw_soft * self.nvm_hard


class Results:
    """ The results of a simulation """
    def __init__(self, model, sizes, rates, period=1*YEAR):
        """ compute the probability of data loss
                model -- base simulation parameters
                sizes -- key capacities and counts
                rates -- key fit rates
                period -- period (hours) to be analyzed
        """

        # initial primary failures
        #   1-P(n=0) p primaries, period
        #   x, for each remaining copy
        #       1-P(n=0) surviving copies, Tr

        # initial seconary failures
        #   1-P(n=0) s secondaries, period
        #   x 1-P(n=0) 1 primary, Tr
        #   x, for each remaining copy
        #       1-P(n=0) surviving copies, Tr

        # initial secondary failures
        # P(primary failures(T)) ... in entire system
        #   for each additional copy
        #       times P subsequent secondary failure(Tr) ... in mirror group
        self.p_loss_node = .0001

        # P(secondary failures(T)) ... in entire system
        #   times P(primary faiures(Tr)) ... of a particular primary
        #   for each additional copy
        #       times P subsequent secondary failure(Tr) ... in mirror group
        self.p_loss_node += .0001
        self.exp_loss_node = 100

        # P(lose all copies)
        self.p_loss_copy = .0002
        self.exp_loss_copy = 4096

        # compute the overall probability of data loss
        self.p_loss_all = self.p_loss_node + self.p_loss_copy
        self.exp_loss_all = self.p_loss_node * self.exp_loss_node +\
            self.p_loss_copy * self.exp_loss_copy

        # compute the durability
        d = 1 - self.p_loss_all
        self.durability = d
        self.nines = 0
        while d > .9:
            self.nines += 1
            d -= .9
            d *= 10
