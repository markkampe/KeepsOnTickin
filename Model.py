"""
Input values to the simulation, and output values from the simulation
"""
from RelyFuncts import SECOND, MINUTE, HOUR, DAY, YEAR, FitRate, allFail

from sizes import MiB, GiB, PiB


class Results:
    """ The results of a simulation """


class Model:
    """
        1. a collection of simulation parameters
        2. methods to compute the results of the simulation
    """

    def __init__(self):
        """ initialize default simulation parameters """

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

    def calculate_size(self, capacity):
        """ compute number of primary and secodary nodes
                capacity -- total (byte) capacity of the system

            Some important parameters are best computed as functions
            of other parameters.  These computations are in a separate
            method to improve readability.
        """

        # figure out how much data we are keeping in cache
        used = capacity * self.cap_used
        active = used * self.luns_active
        cached = active * self.luns_cached
        GiB_1 = cached / GiB
        GiB_2 = cached * self.copies / GiB

        # figure out how many primary/secondary nodes that implies
        if self.n_nvram_1 == 0:
            n_1 = GiB_1 / (self.n_dram_1 * self.sz_dram)
        else:
            n_1 = GiB_1 / (self.n_nvram_1 * self.sz_nvram)
        if self.n_nvram_2 == 0:
            n_2 = GiB_2 / (self.n_dram_2 * self.sz_dram)
        else:
            n_2 = GiB_2 / (self.n_nvram_2 * self.sz_nvram)

        return (n_1, n_2)

    def calculate_rates(self, repair):
        """ compute the bottom-up FIT rates
                repair -- repair time (hours) for failed components

            Some FIT rates must be computed as functions of other
            failure, performance, and architectural parameters.
            These computations are in a separate method to
            improve readability.
        """

        # attempt a bottom-up node FITs computation
        power_fits = allFail(self.f_power, self.n_power, self.m_power, repair)
        fan_fits = allFail(self.f_fan, self.n_fan, self.m_fan, repair)
        nic_fits = allFail(self.f_nic, self.n_nic, self.m_nic, repair)

        # estimate hard s/w failures as a fraction of all s/w failures
        hard_sw_fits = self.f_sw * self.sw_hard

        # assume primary and secondary nodes are the same
        self.fits_1 = self.f_ctlr + power_fits + fan_fits + nic_fits + \
            hard_sw_fits
        self.fits_2 = self.f_ctlr + power_fits + fan_fits + nic_fits + \
            hard_sw_fits

        # estimate hard DRAM failures as a fraction of soft ones
        self.f_dram_hard = self.f_dram * self.dram_2bit

        # FIX calc memory failures resulting in resets of non-persistent copies
        # FIX calc memory failures resulting in loss of persistent copies
        # FIX calc recovery time

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

    def calculate_durability(self, primaries, secondaries, period=1 * YEAR):
        """ compute the probability of data loss
                primaries -- number of primary nodes
                secondaries -- number of secondary nodes
                period -- period (hours) to be analyzed
        """
        # compute Ploss_1(T)
        # compute Ploss_1(Tr)
        # compute Ploss_2(T)
        # compute Ploss_2(Tr)

        results = Results()
        # P(primary failures(T)) ... in entire system
        #   for each additional copy
        #       times P subsequent secondary failure(Tr) ... in mirror group
        results.p_loss_node = .0001

        # P(secondary failures(T)) ... in entire system
        #   times P(primary faiures(Tr)) ... of a particular primary
        #   for each additional copy
        #       times P subsequent secondary failure(Tr) ... in mirror group
        results.p_loss_node += .0001

        # P(lose all copies)
        results.p_loss_copy = .0002

        # compute expected data loss
        results.exp_loss_node = 100
        results.exp_loss_copy = 4096

        return results
