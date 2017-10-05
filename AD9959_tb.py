from AD9959 import AD9959
import time

if __name__ == '__main__':
    dds = AD9959()

    dds.set_output(channels=0, value=40e6, var='frequency', io_update=True)
    dds.set_output(channels=0, value=1, var='amplitude', io_update=True)
    
    dds.set_freqsweeptime(channels=0, start_freq=40e6, end_freq=80e6, sweeptime=5, no_dwell=True, ioupdate=True, trigger=True)
    #dds.set_ampsweeptime(channels=0, start_scale=0.99, end_scale=1, sweeptime=0.1, no_dwell=False, ioupdate=False, trigger=False)