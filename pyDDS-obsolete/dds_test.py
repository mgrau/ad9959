from dds import DDS

dds = DDS()


#dds.set_frequency(3, 80e6, True)


dds.set_amplitude(3, 0.855, True)

dds.set_freqsweeptime(3, 80e6, 85e6, 1, ioupdate=True, trigger=False)
dds.sweep_loop(3, 5, 1)
