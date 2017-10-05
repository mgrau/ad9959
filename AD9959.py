#NOTE: Need to set up RPi Ref Clock first by running:
#   ./minimal_clk 50.0M -q in [root@tiqi-pi ~]

import spidev 
import RPi.GPIO as gpio
from warnings import warn
import time


IOUPDATE_PIN = 16
RESET_PIN = 18
PIN_0 = 15
PIN_1 = 13
PIN_2 = 11
PIN_3 = 12

#Channel Pins
_CHPINS = {
0: 15, #Channel 0
1: 13, #Channel 1
2: 11, #Channel 2
3: 12  #Channel 3
}

gpio.setmode(gpio.BOARD)
gpio.setup(IOUPDATE_PIN, gpio.OUT)
gpio.setup(RESET_PIN, gpio.OUT)
gpio.setup(PIN_0, gpio.OUT)
gpio.setup(PIN_1, gpio.OUT)
gpio.setup(PIN_2, gpio.OUT)
gpio.setup(PIN_3, gpio.OUT)

#Registers
_registers = {
'CSR'               :0x00,
'FR1'               :0x01,
'FR2'               :0x02,
'CFR'               :0x03,
'CFTW0'             :0x04,
'CPOW0'             :0x05,
'ACR'               :0x06,
'LSR'               :0x07,
'RDW'               :0x08,
'FDW'               :0x09,
'CTW1'              :0x0A,
'CTW2'              :0x0B,
'CTW3'              :0x0C,
'CTW4'              :0x0D,
'CTW5'              :0x0E,
'CTW6'              :0x0F,
'CTW7'              :0x10,
'CTW8'              :0x11,
'CTW9'              :0x12,
'CTW10'             :0x13,
'CTW11'             :0x14,
'CTW12'             :0x15,
'CTW13'             :0x16,
'CTW14'             :0x17,
'CTW15'             :0x18
}

#Read and Write nibbles for instruction bytes
READ              = 0x80
WRITE             = 0x00    

#Register lengths (in bytes)
_register_len = {
'CSR'               :1,
'FR1'               :3,
'FR2'               :2,
'CFR'               :3,
'CFTW0'             :4,
'CPOW0'             :2,
'ACR'               :3,
'LSR'               :2,
'RDW'               :4,
'FDW'               :4,
'CTW1'              :4,
'CTW2'              :4,
'CTW3'              :4,
'CTW4'              :4,
'CTW5'              :4,
'CTW6'              :4,
'CTW7'              :4,
'CTW8'              :4,
'CTW9'              :4,
'CTW10'             :4,
'CTW11'             :4,
'CTW12'             :4,
'CTW13'             :4,
'CTW14'             :4,
'CTW15'             :4
}


class AD9959():

    def __init__(self, device=0):
        """Constructor. """

        # setup the GPIO
        self.spi = spidev.SpiDev()
        self.spi.open(0, device)

        self.CSR_LOW_NIBBLE = 0b0010
        self.FR1_VCO_BYTE = 0x80
           
        #Ref_clock frequency initialised at 50 MHz. Use self.set_refclock to change.
        self.refclock_freq = 50e6
        self.init_dds(freqmult=10, channels=0)

        self.set_current([0,1,2,3], 1)           

    def __del__(self):
        gpio.cleanup()

    def init_dds(self, freqmult=10, channels=0):
        """Resets the status of the DDS, then sets all register entries to default.

        Also resets the stored values from set_ functions to default.
        Activates channel 0 (and sets communication mode to 3-wire)
        """

        self.reset()

        self.set_freqmult(freqmult)
        self._set_channels(channels)
        self._io_update()
        
        self.currents = [1, 1, 1, 1]
        self.frequencies = [0, 0, 0, 0]
        self.amplitudes = [1, 1, 1, 1]
        self.phases = [0, 0, 0, 0]

    def set_output(self, channels, value, var, io_update=False):
        """Set frequency, phase or amplitude of selected channel(s). 
        
        # Function description
        Sets frequency, phase or amplitude of a channel or a list of channels.

        ### Arguments
        * `channels` -- `channels` can be a single int from `0`, `1`, `2` or `3` or a list of several channels.
        * `value` -- value
        * `var` -- `frequency`, `phase`, or `amplitude`

        ### Keyword arguments
        * `io_update` -- Setting `io_update=True` will issue an io update to write the settings into the DDS registers.
        
        ### Setting frequency
        `value` must be frequency in Hz.

        ### Setting phase
        `value` must be the phase in degress and must lie between 0 and 359.987 deg

        ### Setting the amplitude
        `value` must the scale factor and must lie between Min: 0.001 and Max: 1.
        If scale_factor == 1, ASF is switched off. Otherwise the ASF is turned on.
        """

        #Activate selected channels
        self._set_channels(channels)

        #Turn off linear sweep
        BYTE1 = self._read('CFR')[1] & 0x03
        self._write('CFR', [0x00, BYTE1, self._read('CFR')[2]])

        if var == 'frequency':
            register = 'CFTW0'  #Write FTW to CFTW0 register
            data = self._convert_frequency(value)
        
        elif var == 'phase':
            register = 'CPOW0'  #write POW bytes into correct register
            data = self._convert_phase(value)

        elif var == 'amplitude':
            register = 'ACR'  # Write to 'ACR' register
            data = self._convert_amplitude(value)

        self._write(register, data)
        self._update(var, channels, value)

        if io_update:
            self._io_update()

    def set_freqsweeptime(self, channels, start_freq, end_freq, sweeptime, no_dwell=False, ioupdate=False, trigger=False):
        """Activates linear frequency sweep mode. 

        Sweeping from start_freq to end_freq (in Hz) with a duration of sweeptime (in seconds).
        To reset frequency to start_freq after sweep, set no_dwell=True
        Setting ioupdate=True will issue an ioupdate to write the settings into the DDS registers
        Setting trigger=True will immediately trigger the ramp by setting the channel pins to high.
        Note that trigger only works if ioupdate is also set to True.
        """

        step_interval = 1e-6 #1us
        steps = sweeptime/step_interval #Number of steps
        step_size = abs(end_freq-start_freq)/steps
        
        self._init_sweep(scan_type='frequency', channels=channels, start_val=start_freq, end_val=end_freq, RSS=step_size, RSI=step_interval, no_dwell=no_dwell)
                
        if ioupdate:
            self._io_update()
            if trigger:
                PINS = self.select_CHPINS(channels)
                gpio.output(PINS, 0)
                gpio.output(PINS, 1)

    def set_ampsweeptime(self, channels, start_scale, end_scale, sweeptime, no_dwell=False, ioupdate=False, trigger=False):
        """Activates linear amplitude sweep mode. 

        Sweeping from start_scale to end_scale with a duration of sweeptime.
        To reset amplitude to start_scale after sweep, set no_dwell=True
        Setting ioupdate=True will issue an ioupdate to write the settings into the DDS registers.
        Setting trigger=True will immediately trigger the ramp by setting the channel pins to high.
        Note that trigger only works if ioupdate is also set to True.
        """
        
        step_interval = 2e-6 #1us
        steps = sweeptime/step_interval #Number of steps
        step_size = (end_scale-start_scale)/steps
        print(steps)
        
        self._init_sweep(scan_type='amplitude', channels=channels, start_val=start_scale, end_val=end_scale, RSS=step_size, RSI=step_interval, no_dwell=no_dwell)
        
        #IOUPDATE and Start
        if ioupdate:
            self._io_update()
            if trigger:
                PINS = self.select_CHPINS(channels)
                gpio.output(PINS, 0)
                gpio.output(PINS, 1)

    def get_frequency(self,):
        """Returns the frequency values set in all channels as a list. 

        The values' position indicate the corresponding channel: [CH0, CH1, CH2, CH3]
        """
        
        #TODO:
            #Find way to appropriately reconvert the frequency to its initial
            #Value or alert that the value is APPROXIMATE
        FTW = int (0)
        freq = int(0)
        
        FTW_bytes = self._read('CFTW0')
        FTW = FTW.from_bytes(FTW_bytes,'big')
        freq = FTW*self.clock_freq/2**32
        
        print('Latest frequency set: ', "{:.2e}".format(freq), 'Hz')
        print(['%.2e' % elem for elem in self.frequencies])
        
        return self.frequencies

    def get_phase(self,):    
        """Returns the phase values set in all channels as a list. 

        The values' position indicate the corresponding channel: [CH0, CH1, CH2, CH3]
        """
        
        #for comparison
        initial_state = self._read('CPOW0')
        
        POW_step = 0.02197265
        POW = 0x00 | initial_state[0] << 8| initial_state [1]
        phase = round(POW*POW_step, 2)
        
        print ('Latest phase set (i.e. currently in register):', phase)
        
        return self.phases

    def get_amplitude(self,):
        """Returns the amplitude values set in all channels as a list. 

        The values' position indicate the corresponding channel: [CH0, CH1, CH2, CH3]
        """
                
        data = self._read('ACR')
        BYTE1 = data[1]
        BYTE2 = data[2]
        
        ASF = (0x03 & BYTE1) << 8 | BYTE2
        ASF_step = 0.00097751
        scale_factor = ASF*ASF_step
        
        if scale_factor == 0:
            print ('Latest scale_factor set (i.e. currently in register):', 1)
        else:
            print ('Latest scale_factor set (i.e. currently in register):', scale_factor)

        return self.amplitudes

    def get_state(self, form='hex'):
        """Prints all values in DDS registers in hex or bin format. The default format is 'hex' but can be changed to 'bin' """
        
        assert (form == 'hex') or (form == 'bin')
        
        if form == 'hex':
            for key in _registers:
                print(key, ['0x{:02x}'.format(b) for b in self._read(key)])
        else:
            for key in _registers:
                print(key, ['{:08b}'.format(b) for b in self._read(key)])
            
    def reset(self,):
        """Resets the status of the DDS, sets all register entries to default. Also resets the stored values from set_ functions to default. """

        self._toggle_pin(RESET_PIN)                  
    
    def _set_channels(self, channels, ioupdate=False):
        """Activates one or multiple channels to write settings to.

        channels must be passed in a list or as an int, containg channels between 0,1,2 or 3.
        Additionally, always sets communication mode into 3 wire mode: CSR[1:2].
        """
        
        #Activate selected channels
        assert (type(channels) is int) or (type(channels) is list), 'Channels must be int or list'
        
        #If only one channel is selected
        if type(channels) is int:
            assert channels in [0, 1, 2, 3], 'channel must be 0, 1, 2 or 3'
            self._write('CSR', [2**(channels) << 4 | self.CSR_LOW_NIBBLE])
        
        #If several channels are given
        elif type(channels) is list:
            for channel in channels: assert channel in [0,1,2,3], 'channels must be between 0, 1, 2 or 3'
        
            #Removing duplicates
            uniq_channels = [channel for channel in set(channels)]
            
            channel_nibble = int(0)
            for channel in uniq_channels:
                channel_nibble += 2**channel
            channel_nibble << 4
            self._write('CSR', [channel_nibble << 4| self.CSR_LOW_NIBBLE])
    
        if ioupdate:
            self._io_update()
            
    def get_activechannels(self,):
        """Returns currently active channels in a list. """
        
        channels_nibble = self._read('CSR')[0] >> 4
        channels = []
        
        for i in reversed (range (4)):
            if channels_nibble >> i > 0:
                channels.append(i)
                channels_nibble -= 2**i
        
        channels.reverse()
        
        return channels    
        
    def set_refclock(self, frequency):  
        """ Sets the class variable self.refclock_freq.

        Automatically updates class variable self.clock_freq with new refclock frequency. Must pass frequency in Hz (i.e 50MHz = 50e6 Hz). Prints out current values for self.refclock_freq, self.freqmult and self.clock_freq
        """
        
        self.refclock_freq = frequency
        self.clock_freq = self.freqmult*self.refclock_freq
        if (self.clock_freq < 99.999e6 or self.clock_freq > 500.001e6):
            warn('Clock frequency out of range. Use set_freqmult to set clock \
                 frequency between 100MHz and 500MHz')
        print ('Refclock =', "{:.2e}".format(frequency), 'Hz \nFreqmult =', self.freqmult,
               '\nClock Frequency =', "{:.2e}".format(self.clock_freq), 'Hz')
        
        
    def set_freqmult(self, freqmult, ioupdate=False):
        """ Sets the frequency multiplier on the DDS.

        Automatically updates self.clock_freq with new freqmult. When changing the frequency multiplier the channel frequencies must be reset.
        
        Frequency multiplier must be between 4 and 20 or equal to 1 (turns off multiplier)
        Frequency multiplier must be chosen such that self.clock_freq lies between 100MHz and 500MHz.
        
        NOTE1: No guarantee of operation if self.clock_freq is set between 160MHz and 255MHz. 
        Setting ioupdate=True will issue an ioupdate to write the settings into the DDS registers.
        """
        
        assert (freqmult == 1 or freqmult in range(4,21)), 'Multiplier must be 1 (off) or between 4 and 20'
        assert (freqmult*self.refclock_freq > 99.999e6 and \
                freqmult*self.refclock_freq < 500.001e6), \
                'self.clock_frequency must lie between Min: 100MHz and Max 500MHz'
        
        #Read current state of FR1 register
        initial_state = self._read('FR1')
        
        if freqmult == 1:
            #toggles VCO off deletes multiplier and copies charge pump control
            BYTE0 = 0x03 & initial_state[0]
        
        else:
            #Copy charge pump control setting and set VCO control on or off depending on clock_freq threshold
            if freqmult*self.refclock_freq > 225e6:
                BYTE0 = 0x03 & initial_state [0] | (freqmult << 2) | self.FR1_VCO_BYTE
            elif freqmult*self.refclock_freq < 160e6:
                BYTE0 = 0x03 & initial_state [0] | (freqmult << 2)
            else:
                warn('Clock frequency set between 160MHz and 255MHz. No guarantee of operation')
                BYTE0 = 0x03 & initial_state [0] | (freqmult << 2)
        
        #Copy unchanged bytes from FR1 register
        BYTE1 = initial_state[1]
        BYTE2 = initial_state[2]
        
        #data for FR1 register
        new_state = [BYTE0, BYTE1, BYTE2]
        #write new state into register
        self._write('FR1', new_state)
        
        #Set new freqmult value and print clock information
        self.freqmult = freqmult
        self.clock_freq = self.refclock_freq*self.freqmult
        print ('Refclock =', "{:.2e}".format(self.refclock_freq), 'Hz \nFreqmult =', self.freqmult,
               '\nClock Frequency =', "{:.2e}".format(self.clock_freq), 'Hz')
    
        if ioupdate:
            self._io_update()
        
    def get_freqmult(self,):
        """Returns current value of frequency multiplier. """
        
        BYTE0 = (self._read('FR1')[0] & 0b01111100) >> 2
        self.freqmult = BYTE0
        
        if BYTE0 == 0:
            return 1
        else:
            return (BYTE0)
           
    def set_current(self, channels, divider, ioupdate=False):      
        """Sets current of selected channel(s).

        Current divider must be 1, 2, 4 or 8 corresponding to 1, 1/2, 1/4 and 1/8 scales respectively. Channels can be a single int from 0, 1, 2 or 3 or a list of several of 0, 1, 2 or 3. Setting ioupdate=True will issue an ioupdate to write the settings into the DDS registers.
        """

        assert divider in [1, 2, 4, 8], 'Divider must be 1, 2, 4 or 8'
        
        #Activate selected channels
        self._set_channels(channels)
                
        #Read initial state
        initial_state = self._read('CFR')
        
        #Convert divider to bits
        if divider == 1:
            bits = 0b11
        elif divider == 2:
            bits = 0b01
        elif divider == 4:
            bits = 0b10
        elif divider == 8:
            bits = 0b00
            
        #Write bits into correct byte (BYTE1)
        BYTE1 = initial_state[1] & 0b11111100
        BYTE1_new = BYTE1 | bits
            
        #New data for CFR register
        new_state = [initial_state[0], BYTE1_new, initial_state[2]]
        
        self._write('CFR', new_state)
        
        #Save Data for get_current
            #For every channel, if channel is set 'on' in set_channels
            #write the new value for that channel into list

        if type(channels) is int:
            channels = [channels]
        for channel in channels:
            self.currents[channel] = divider

        if ioupdate:
            self._io_update()

    def get_current(self,):           
        """Returns the current values set in all channels as a list. 

        The values' position indicate the corresponding channel: [CH0, CH1, CH2, CH3]
        """
        
        #for comparison
        initial_state = self._read('CFR')
        bits = initial_state[1] & 0x03
        
        if bits == 0b11:
           divider = 1
        elif bits == 0b01:
           divider = 2
        elif bits == 0b10:
           divider = 4
        elif bits == 0b00:
           divider = 8
        
        print ('Latest divider set (i.e. currently in register):', divider)
        
        # Returns values saved in set_current
        return self.currents
    
    def _init_sweep(self, scan_type, channels, start_val, end_val, RSS, RSI, FSS='same', FSI='same', no_dwell=False, ioupdate=False, trigger=False):
        """Turns on amplitude or frequency linear sweep mode and programs the settings as passed.

        channels: single channel or list of channels from [0, 1, 2, 3],
        start_val: starting amplitude (between 0 and 1) or frequency
        end_val: final amplitude or frequency
        RSS: Rising Step Size (between 0 and 1)
        RSI: Rising Step Interval (limited by clock frequency, RSI_min = 1/(self.clock_freq/4), RSI_max = 255/(self.clock_freq/4))
        FSS: Falling Step Size (if not given, takes same value as RSS)
        FSI: Falling Step Interval (if not given, takes same value as RSI)
        no_dwell: True turns on no_dwell mode, which clears amplitude after ramp finishes
        
        For sweep to take effect, an ioupdate must be issued after inputing parameters.
        RSS and RSI take effect when the respective channel pin is set to high
        FSS and FSI take effect when the respective channel pin is set to low
        
        Setting ioupdate=True will issue an ioupdate to write the settings into the DDS registers
        Setting trigger=True will immediately trigger the ramp by setting the channel pins to high.
        Note that trigger only works if ioupdate is also set to True.
        """
        
        #Assign values if none are given
        if FSS == 'same': FSS = RSS
        if FSI == 'same': FSI = RSI  

        #Assert RSI and FSI are in allowed ranges. Compute and print allowed ranges.
        RSI_min = 1/(self.clock_freq/4)
        RSI_max = 255/(self.clock_freq/4)
        assert RSI > RSI_min, 'RSI is set below minimum: %r s. To lower minimum, clock frequency needs to be increased' %RSI_min
        assert FSI > RSI_min, 'FSI is set below minimum: %r s. To lower minimum, clock frequency needs to be increased' %RSI_min
        assert RSI < RSI_max, 'RSI is set above maximum: %r s. To increase maximum, clock frequency needs to be decreased' %RSI_max
        assert FSI < RSI_max, 'FSI is set above maximum: %r s. To increase maximum, clock frequency needs to be decreased' %RSI_max

        #Activate selected channels
        self._set_channels(channels)
        
        #Set modulation level to two-level modulation (FR1[9:8]=00)
        FR1_BYTES = self._read('FR1')
        if(FR1_BYTES[1] & 0b00000011):
            FR1_BYTES[1] = FR1_BYTES[1] & 0b11111100
            self._write('FR1', FR1_BYTES)
            #If modulation level is already set to two-level, do nothing
        else:
            pass
        #Input sweep settings

        if scan_type == 'frequency':
            self._init_freq_sweep(start_val, end_val, RSS, FSS, no_dwell)
        elif scan_type == 'amplitude':
            self._init_amp_sweep(start_val, end_val, RSS, FSS, no_dwell)

        #Set Linear Sweep Ramp Rates (LSR):
        LSR_BYTES = [0, 0]
        
        #Write F(alling)SRR in LSR[15:8], R(ising)SRR in LSR[7:0]
        #RSI_min = 1/(clock_freq/4), RSI_max = 255/(clock_freq/4)
        #RSRR = clock_freq*RSI/4    
        RSRR = round(RSI*self.clock_freq/4)
        FSRR = round(FSI*self.clock_freq/4)

        LSR_BYTES[0] = FSRR
        LSR_BYTES[1] = RSRR
        
        self._write('LSR', LSR_BYTES)
                
        #IOUPDATE and Start
        if ioupdate:
            self._io_update()
            if trigger:
                PINS = self.select_CHPINS(channels)
                gpio.output(PINS, 0)
                gpio.output(PINS, 1)
            

    def _init_amp_sweep(self, start_scale, end_scale, RSS, FSS, no_dwell): 
        #Assert start_scale, end_scale, RSS and FSS are between min and max values, like in set_amplitude
        ASF_step = 1/(2**10 - 1) #Corrected bug. ASF_step must not be 1/2**10 to avoid writing 11 bits into 10 bit register, when setting scale to 1.
        
        start_ASF = round(start_scale/ASF_step)
        assert start_ASF > 0, 'Minimum start_scale factor is 0.001'
        end_ASF = round(end_scale/ASF_step)
        assert end_ASF > 0, 'Minimum end_scale factor is 0.001'
        RDW = round(RSS/ASF_step)
        assert RDW > 0, 'Minimum RSS factor is 0.001'
        FDW = round(FSS/ASF_step)           
        assert FDW > 0, 'Minimum FSS factor is 0.001'
        
        
        assert start_ASF < 2**10, 'Choose a start_scale factor smaller or equal 1'
        assert end_ASF < 2**10, 'Choose an end_scale factor smaller or equal 1'
        assert RDW < 2**10, 'Choose a RSS factor smaller or equal 1'
        assert FDW < 2**10, 'Choose a FSS factor smaller or equal 1'
        
        assert start_ASF < end_ASF, 'start_scale must be smaller than end_scale'   

        #Setting up linear sweep mode
        CFR_BYTES = [0, 0, 0]
        CFR_initial = self._read('CFR')
            #Set AFP select to amplitude sweep (CFR[23:22]=01)
        CFR_BYTES[0] = 0x40    
            #Enable Linear Sweep (CFR[14]=1) (copy last two bits)
        CFR_BYTES[1] = 0x40 | (0x03 & CFR_initial[1])
            #Enable no-dwell if true: CFR[15]=1 else 0
        CFR_BYTES[1] = CFR_BYTES[1] | no_dwell << 7
            #Copy BYTE2 from initial state (More options can be set here. Need to enlarge this function)
        CFR_BYTES[2] = CFR_initial[2]
            #Write bytes to CFR
        self._write('CFR', CFR_BYTES)
            
        ######
        ACR_BYTES = [0, 0, 0]
        CTW1_BYTES = [0, 0, 0, 0]
        RDW_BYTES = [0, 0, 0, 0]
        FDW_BYTES = [0, 0, 0, 0]
        
        #Write start_scale word into register, switching all other amplitude modes off
        ACR_BYTES[1] = 0x03 & start_ASF >> 8
        ACR_BYTES[2] = 0x00 | start_ASF
        
        #End value into CTW1[31:22]
        #NOTE: Must be MSB aligned
        
        #Write end_scale factor bytes
        CTW1_BYTES[0] = 0x00 | end_ASF >> 2
        CTW1_BYTES[1] = 0x03 & end_ASF
        
        #Write RDW to RDW[31:22], FDW to FDW[31:22]
        RDW_BYTES[0] = 0x00 | RDW >> 2
        RDW_BYTES[1] = 0x03 & RDW
        
        FDW_BYTES[0] = 0x00 | FDW >> 2
        FDW_BYTES[1] = 0x03 & FDW
        
        self._write('CFR', CFR_BYTES)
        self._write('ACR', ACR_BYTES)
        self._write('CTW1', CTW1_BYTES)
        self._write('RDW', RDW_BYTES)
        self._write('FDW', FDW_BYTES)

    def _init_freq_sweep(self, start_freq, end_freq, RSS, FSS, no_dwell):   
        FTW_step = self.clock_freq/2**32
        Min_freq = FTW_step
        Max_freq = (2**32-1)*FTW_step
        
         #Asserts
            #Assert start_freq, end_freq, RSS and FSS are between min and max values, like in set_frequency
        
        start_FTW = round(start_freq/FTW_step)
        assert start_FTW > 0, 'Minimum start_freq is %r' %Min_freq
        end_FTW = round(end_freq/FTW_step)
        assert end_FTW > 0, 'Minimum end_freq  is %r' %Min_freq
        RDW = round(RSS/FTW_step)
        assert RDW > 0, 'Minimum RSS is %r' %Min_freq
        FDW = round(FSS/FTW_step)        
        assert FDW > 0, 'Minimum FSS is %r' %Min_freq
        
        assert start_FTW < end_FTW, 'start_freq must be smaller than end_freq'
        
        assert start_FTW <= 2**32, 'Maximum start_freq is %r' %Max_freq
        assert end_FTW <= 2**32, 'Maximum end_freq is %r' %Max_freq
        assert RDW <= 2**32, 'Maximum RSS is %r' %Max_freq
        assert FDW <= 2**32, 'Maximum FSS is %r' %Max_freq


        #Setting up linear sweep mode
        CFR_BYTES = [0, 0, 0]
        CFTW0_BYTES = [0, 0, 0, 0]
        CTW1_BYTES = [0, 0, 0, 0]
        RDW_BYTES = [0, 0, 0, 0]
        FDW_BYTES = [0, 0, 0, 0]

        #Setting up linear sweep mode
        CFR_initial = self._read('CFR')

        #Set AFP select to amplitude sweep (CFR[23:22]=01)
        CFR_BYTES[0] = 0x80
        #Enable Linear Sweep (CFR[14]=1) (copy last two bits)
        CFR_BYTES[1] = 0x40 | (0x03 & CFR_initial[1])
        #Enable no-dwell if true: CFR[15]=1 else 0
        CFR_BYTES[1] = CFR_BYTES[1] | no_dwell << 7
        #Copy BYTE2 from initial state (More options can be set here. Need to enlarge this function)
        CFR_BYTES[2] = CFR_initial[2]
        #Write bytes to CFR
        

        #Input sweep settings
        #Set start point (in CFTW0)
        #Write start_FTW in bytes
        CFTW0_BYTES = [start_FTW.to_bytes(4,'big')[i] for i in range(4)]
        #Set end point (in CTW1[31:0])            
        #Write end_FTW in bytes
        CTW1_BYTES = [end_FTW.to_bytes(4,'big')[i] for i in range(4)]

        #Write RDW to RDW[31:0], FDW to FDW[31:0]
        RDW_BYTES = [RDW.to_bytes(4,'big')[i] for i in range(4)]
        FDW_BYTES = [FDW.to_bytes(4,'big')[i] for i in range(4)]

        self._write('CFR', CFR_BYTES)
        self._write('CFR', CFR_BYTES)
        self._write('CFTW0', CFTW0_BYTES)
        self._write('CTW1', CTW1_BYTES)
        self._write('RDW', RDW_BYTES)
        self._write('FDW', FDW_BYTES)
        
    def sweep_loop(self, channels, reps, interval):
        """Initiates a loop of reps PIN toggles with an interval between every toggle. channels indicates which channel PINS should be toggled. Interval indicates the interval between every toggle in seconds.
        """
        
        PINS = self.select_CHPINS(channels)
                
        for i in range(reps):
            time.sleep(interval)
            gpio.output(PINS, 0)
            time.sleep(interval)
            gpio.output(PINS, 1)
            i += 1
            if i ==1:
                print ('1st cycle')
            elif i ==2:
                print ('2nd cycle')
            elif i ==3:
                print ('3rd cycle')
            else:
                print ('%rth cycle' %i)
            
        gpio.output(PINS, 0)

    def select_CHPINS(self, channels):
        assert (type(channels) is int) or (type(channels) is list), 'channels must be passed as int or list'
        if type(channels) is list:
            for channel in channels:
                assert channel in [0, 1, 2, 3]
            PINS = [_CHPINS[channel] for channel in channels]
        elif type (channels) is int:
            assert channels in [0, 1, 2, 3]
            PINS = _CHPINS[channels]
        
        return PINS

    def _write(self, register, data):
        """Writes a list of bytes (data) into selected register. 

        Register must be given as a string and must be contained in _registers. data must be given as a list with appropriate number of bytes, as stated in _register_len.
        """
        
        #data: list of bytes to write to register
        assert register in _registers, '%r is not a valid register. Register must be passed as string.' %register
        assert len(data) == _register_len[register], 'Must pass %r byte(s) to %r register.' %(_register_len[register], register)
        
        # send the register we want to write to
        self.spi.writebytes([_registers[register]])
        
        # send the bytes we write to the register
        self.spi.writebytes(data)   

    def _read(self, register):
        """Returns list of bytes (data), currently stored in register. """
        
        assert register in _registers, 'Not a valid register. Register must be passed as string.'
        
        #send read command to register        
        self.spi.writebytes([READ | _registers[register]])
        
        #return values in register
        return self.spi.readbytes(_register_len[register])

    def _io_update(self,):
        """ Toggles IO_UPDATE pin on the RPi to load all commands to the DDS sent since last ioupdate. """

        self._toggle_pin(IOUPDATE_PIN)

    def _toggle_pin(self, pin):
        gpio.output(pin, 0)
        gpio.output(pin, 1)
        gpio.output(pin, 0)

    def _update(self, var, channels, value):
        """Updates class internal list of output states. """

        if type(channels) is int:
                channels = [channels]

        if var =='frequency':
            for channel in channels:
                self.frequencies[channel] = value
        elif var =='phase':
            for channel in channels:
                self.phases[channel] = value
        elif var == 'amplitude':
            for channel in channels:
                self.amplitudes[channel] = value

    def _convert_frequency(self, frequency):
        """Convert a frequency to correct spi message. """

        #Assert frequency lies within allowed range
        FTW_step = self.clock_freq/2**32
        FTW = round(frequency/FTW_step)
        Min_freq = FTW_step
        Max_freq = (2**32-1)*FTW_step
            
        assert FTW > 0, 'Minimum frequency is %r' %Min_freq
        assert FTW <= 2**32, 'Maximum frequency is %r' %Max_freq

        #Compute frequency tuning word for given frequency and clock frequency
        #Write FTW in list of 4 bytes (CFTW0 is a 32-bit register)
        return [FTW.to_bytes(4,'big')[i] for i in range(4)]

    def _convert_phase(self, phase):
        """Convert a phase to correct spi message. """

        assert (phase >= 0 and phase < 359.988), 'Phase must be between 0 and 359.987 degrees'

        #Convert phase into POW
        POW_step = 0.02197265
        POW = round(phase/POW_step)
    
        #Convert POW into bytes
        BYTE0 = 0x00 | (POW >> 8)
        BYTE1 = 0xFF & POW
        return [BYTE0, BYTE1]

    def _convert_amplitude(self, scale_factor):
        """Convert an amplitude to correct spi message. """

        initial_state = self._read('ACR')

        if scale_factor == 1:
            BYTE0 = initial_state[0]
            BYTE1 = initial_state[1] & 0b11101100
            BYTE2 = 0x00
            return [BYTE0, BYTE1, BYTE2]    
        else:            
            ASF_step = 1/2**10
            ASF = round(scale_factor/ASF_step)
            assert ASF > 0, 'Minimum scale factor is 0.001'
            assert ASF < 2**10, 'Choose a scale factor equal or below 1'
                
            ASF = round(scale_factor/ASF_step)
            
            BYTE0 = initial_state[0]
            BYTE1 = (((initial_state[1] >> 2) & 0b111011) << 2) | 0x10 | (ASF >> 8)
            BYTE2 = ASF & 0xFF
            return [BYTE0, BYTE1, BYTE2]