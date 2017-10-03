from AD9959 import AD9959
import time

if __name__ == '__main__':
    dds = AD9959()

    dds.set_frequency(channels=0, frequency=10e6, ioupdate=False)
    dds.set_amplitude(channels=0, scale_factor=1, ioupdate=True)