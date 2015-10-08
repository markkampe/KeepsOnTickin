"""
Input values to the simulation, and output values from the simulation
"""
from RelyFuncts import FitRate, Pfail, Pn, Punion, multiFit
from RelyFuncts import SECOND, MINUTE, HOUR, DAY, YEAR, BILLION
from sizes import MiB, GiB, PiB, MB, GB


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
        self.read_hit = 0.05    # read hit rate from writeback cache

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
            self.n_secondary = self.n_primary if m.copies > 1 else 0
            pcache = m.cache_1 / m.copies
            # This seems wasteful in that we are reserving much more remote
            # cache mirror than we have dirty pages, but the reward is
            # greatly simplified recovery, all copies being identical.
        else:
            pcache = m.cache_1
            cached = self.n_primary * pcache
            self.n_secondary = cached * (m.copies - 1) / m.cache_2

        # compute what fraction of each active LUN we can cache
        lsize = m.lun_per_vm * m.lun_size
        self.cache_tot = pcache / lsize
        self.cache_dirty = m.max_dirty / lsize

        # compute the implied primary/secondary fan-out/fan-in
        if m.copies < 2:
            self.fan_out = 0
            self.fan_in = 0
        else:
            self.fan_out = max(m.decluster, m.copies - 1)
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
            # TODO: is this a valid modeling of fatal memory errors
        if not m.nv_2:
            self.fits_2_loss += m.f_sw
            self.fits_2_loss += m.cache_2 * m.f_dram * m.dram_2bit / MB
            # TODO: is this a valid modeling of fatal memory errors

        # compute a few other interesting cache rate/use parameters
        #   Note: we have modeled write-aggregation as a constant,
        #         but in actuality it is probably a function of the
        #         the interval between flushes
        pcache = m.cache_1 / m.copies if m.symmetric else m.cache_1
        self.fract_dirty = float(m.max_dirty) / pcache
        self.writes_in = m.bsize * m.iops * m.write_fract
        self.new_writes_in = self.writes_in / m.write_aggr
        self.interval_flush = float(m.max_dirty) / self.new_writes_in
        self.cache_life = float(pcache) / self.new_writes_in


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
        n1 = sizes.n_primary        # number of primaries in system
        n2 = sizes.n_secondary      # number of secondaries in system
        fi = min(n1, sizes.fan_in)  # primaries per secondary
        fo = min(n2, sizes.fan_out)     # secondaries per primary
        l1 = rates.fits_1_loss      # primary loss FIT rate
        l2 = rates.fits_2_loss      # secondary loss FIT rate
        dirty = model.max_dirty     # maximum dirty data / primary
        scp = model.copies - 1      # number of secondary copies
        dc = model.decluster        # primary->secondary dispersion
        BWp = model.rate_flush      # primary recovery speed
        BWs = model.rate_flush      # secondary recovery speed

        # compute the equivalent FIT rates for UREs
        if model.nv_1:  # based on average write flush speed
            u1 = rates.writes_in * 8 * model.uer_nvm * BILLION / SECOND
        else:
            u1 = 0
        if model.nv_2:  # based on maximum recovery/flush speed
            u2 = BWs * 8 * model.uer_nvm * BILLION / SECOND
            # WARNING: only lasts for revovery time, detect doesn't count
            # TODO: this assumes uer proportinal to the number of bits read
            #       it may be proportional to the number of bits written
        else:
            u2 = 0
        if debug:
            print("")
            print("FIT(uer,1) = %e, FIT(UER,2) = %e" % (u1, u2))

        # Compute the detection and recovery times
        Tt = model.time_timeout * SECOND
        Td = model.time_detect * SECOND
        b2f = dirty / dc
        Ts = b2f / BWs * SECOND
        if model.remirror and model.rate_mirror > model.rate_flush:
            BWp = model.rate_mirror
        Tp = b2f / BWp * SECOND
        self.Trecov = max(Tt+Tp, Td+Ts) / SECOND

        # estimate the network traffic associated with normal I/O
        bps = model.bsize * model.iops * model.prim_vms * n1
        self.bw_write = model.write_fract * bps
        self.bw_read = (1 - model.read_hit) * (1 - model.write_fract) * bps
        self.bw_mirror = self.bw_write * scp
        self.bw_flush = self.bw_write / model.write_aggr

        # Scenario 1 begins with a failure or NRE on a primary
        E1f = l1 * n1 * period / BILLION        # 1f: primary node failures
        E1e = u1 * n1 * period / BILLION        # 1e: primary UREs
        if debug:
            print("1a: E1fail(%d * %d, T=%e)=%f" % (n1, l1, period, E1f))
            print("1b: E1nre(%d * %d, T=%e)=%f" % (n1, u1, period, E1e))

        # ... after which all other copies are lost
        if fo == 0:
            # there are no copies ... we lose data every time
            P1f = 1 - Pn(E1f, 0)
            P1e = 1 - Pn(E1e, 0)
            self.bw_pfail = 0       # but we don't use much bw :-)
            if debug:
                print("    P1fail(E1F)=%e" % (P1f))
                print("    P1nre(E1E)=%e" % (P1e))
        else:   # C-1/fan-out secondaries fail within Td+Ts
            ue2 = u2 * Ts / (Td + Ts)       # scale UER FIT rate
            P1f = Pfail(E1f * fo * (l2 + ue2), Td + Ts, scp)
            # TODO: find a way to separate the l2 from ue2 induced losses
            P1e = Pfail(E1e * fo * (l2 + ue2), Td + Ts, scp)
            # TODO: sanity check these vs multiplied probabilities
            if debug:
                print("    P1fail(E1F * %d * (%d+%d), T=%e+%e)=%e" %
                      (fo, l2, ue2, Td, Ts, P1f))
                print("    P1nre(E1E * %d * (%d+%d), T=%e+%e)=%e" %
                      (fo, l2, ue2, Td, Ts, P1e))
            self.bw_pfail = BWs * fo        # expected recovery bandwidth

        # Scenario 2 begins with a failure on a secondary
        E2f = l2 * n2 * period / BILLION
        if debug:
            print("2:  E2fail(%d * %d, T=%e)=%f" % (n2, l2, period, E2f))

        # an affected primary fails within the timeout+flush window
        P2f1 = 1 - Pfail(E2f * fi * l1, Tt + Tp, 0)
            # NOTE: primary UREs during flushing are included in 1b
        self.bw_sfail = BWp * fi    # expected recovery bandwidth
        if debug:
            print("    P2fail1(E2F * %d * %d, T=%e+%e)=%e" %
                  (fi, l1, Tt, Tp, P2f1))

        # all surviving secondaries fail within Tt + Tp + Td + Ts
        if scp > 1:
            ue2 = u2 * Ts / (Tt + Tp + Td + Ts)     # scale UER FIT rate
            P2f2 = Pfail((fo - 1) * (l2 + ue2), Tt + Tp + Td + Ts, scp - 1)
            # TODO: find a way to separate the l2 from ue2 induced losses
            if debug:
                print("    P2fail2(%d * (%d+%d), T=%e+%e+%e+%e)=%e" %
                      (fo - 1, l2, ue2, Tt, Tp, Td, Ts, P2f2))
        else:
            P2f2 = 1.0

        P2f = P2f1 * P2f2
        if debug:
            print("    P2F = %e * %e = %e" % (P2f1, P2f2, P2f))

        # tally up the loss probabilities and expentancies
        self.p_loss_node = Punion(P1f, P2f)
        self.p_loss_copy = Punion(P1e)
        self.p_loss_all = Punion(P1f, P2f, P1e)

        # compute the durability
        d = 1 - self.p_loss_all
        self.durability = d
        self.nines = 0
        while d > .9:
            self.nines += 1
            d -= .9
            d *= 10
