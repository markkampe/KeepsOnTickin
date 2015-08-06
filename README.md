# KeepsOnTickin

This is a python model that uses architectural parameters and Poisson
event probabilities associated estimated FIT rates to estimate the 
probability of data loss in a write-back cache with peer-to-peer mirroring.

This model is intended to report:
	number of primary and secondary nodes to support specified capacity
	hard and soft failure probabilities for primary/secondary nodes
	durability of the specified capicity over specified period
	expected data loss for sepecified capacity and period

Scope:
	it is, at present, only a reliability model, tho I expect to
	add availability soon.

Caveats:
	This model considers only loss of dirty data that has not yet been 
	flushed to and acked by the backing store.

	This model does not include soft failures of QEMU because these
	have no affect our our exposure to data loss.

	data loss requires:
		hard failures of all non-volatile copies
		hard or soft failures of all volatile copies
		all within the detection/flush window

Overview of Modules:
	Model.py ... modelling parameters and computations

	RelyGUI.py ... tkinter GUI for setting parameters and running tests
	main.py ... CLI command to instantiate and run models
	uun.py ... run and report the results of a particular model
	

	RelyFuncts.py ... Poisson probability functions and time constants
	sizes.py ... useful capacity/speed constants

