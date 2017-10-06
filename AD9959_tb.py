from AD9959 import AD9959
import time

if __name__ == '__main__':
    dds = AD9959()
    

    print('Set channel 1 to 40 MHz')
    dds.set_output(channels=0, value=40e6, var='frequency', io_update=True)
    time.sleep(1)
    
    print('Ramp frequency up to 80 MHz')
    dds.set_freqsweeptime(channels=0, start_freq=40e6, end_freq=80e6, sweeptime=1, no_dwell=False, ioupdate=True, trigger=False)
    dds.pin_high(15)
    time.sleep(1)
    dds.set_output(channels=0, value=80e6, var='frequency', io_update=True)
    
    time.sleep(1)
    
    print('Ramp frequency down to 10 MHz')
    dds.pin_high(15)
    dds.set_freqsweeptime(channels=0, start_freq=10e6, end_freq=80e6, sweeptime=1e-6, no_dwell=False, ioupdate=True, trigger=False)
    dds.set_freqsweeptime(channels=0, start_freq=10e6, end_freq=80e6, sweeptime=1, no_dwell=False, ioupdate=True, trigger=False)
    time.sleep(1)
    dds.pin_low(15)

    #dds.get_state(form='bin')