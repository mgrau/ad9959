from AD9959 import AD9959
import time

if __name__ == '__main__':
    dds = AD9959()

    dds.set(channels=0, variable=10e6, var='frequency', io_update=False)
    dds.set(channels=0, variable=1, var='amplitude', io_update=False)
    dds.set_freqsweeptime(channels=0, start_freq=80e6, end_freq=40e6, sweeptime=1, no_dwell=False, ioupdate=True, trigger=True)