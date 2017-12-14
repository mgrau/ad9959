#!/usr/bin/env python

"""Server for AD9959 running on RPi.

# Overview
This script is ment to be run on an RPi connected to an AD9959 eval board. It provides a flask based API for programming frequency and amplitude of the 4 channels of the AD9959. Furthermore, this script also hosts a website on which the output of each channel can be set manually.

When changing frequency or amplitude of one channel, the AD9959 will smoothly alter the output. For changing the frequency this transition takes 50 ms per channel. Hence, when updating the freuqncy of all 4 channels at once, it will take 200 ms before all outputs are at the correct frequency.

# Web interface
The website is hosted by default on port 5000 on the RPi. Use the buttons next to each channel to update the settings to the values input to the text boxes. The website can be modified by changing `static/webinterface_settings.json`. (Not implemented yet!)

# Flask based API functions
There are functions for setting frequency and amplitude of all for channels as well as for resetting the outputs
* `/set_frequency` -- Smootly ramps the freuqncy of the specified channels to a new value. Takes 50 ms per channel.
* `/set_amplitude` -- Smootly ramps the amplitude of the specified channels. Uses the built-in transition timing.
* `/reset` -- Resets all outputs to zero output.
* `/shutdown` -- Closes the server. You will have to manually restart it.
* `/doc` -- Shows the documentation for all API functions.

### Starting the server
For starting the server use (export instead of set in linux)
set FLASK_APP=<filename>
(set FLASK_DEBUG=True)
python -m flask run.

### Notes
Make sure that flask and flask_autodoc are installed. Then replace `add_custom_nl2br_filters(self, app)` in 
`<python-installation>\Lib\site-packages\flask_autodoc\autrodoc.py` by
```python
    _paragraph_re = re.compile(r'(?:\r\n|\r|\n){3,}')

    @app.template_filter()
    @evalcontextfilter
    def nl2br(eval_ctx, value):
        result = '\n\n'.join('%s' % p.replace('\n', '<br>\n')
                             for p in _paragraph_re.split(escape(value)))
        if eval_ctx.autoescape:
            result = Markup(result)
        return result
```
Also import make sure `escape` and `Markup` are imported from `jinja2`

### Known bugs
* Frequency ramps are set by programming the lower and upper frequency in two registers and the direction is then set by the state of the data pin (P0-P3) corresponding to that channel (pin high: ramp up, pin low: ramp down). This works correctly when starting with a ramp up but does not when you want to start with a ramp down. In order to get the ramp down to work, pull the data pin high, then program the ramp with the shortest possible transition time (1 us) and immedialely after program the ramp again with the correct transition time. After that pull the data pin low and the ramp will be done correctly. See `AD9959Http.set_frequency` for reference.
* When changing the frequency at an amplitude scale factor < 1, the current divider setting (register 'CFR') will be overridden by 0. This means that the amplitude will be scaled by an additional factor of 1/8. This bug is also descirbed in `AD9959.py` and is fixed by resetting the current divider setting back to one. See `AD9959.py` documentation for details. 
"""

import flask
from flask_autodoc import Autodoc
from AD9959 import AD9959
import json
import time
import subprocess

# enable clock output
subprocess.call(['/usr/bin/minimal_clk', '50.0M', '-q'])

app = flask.Flask(__name__)
auto = Autodoc(app)

DDS = AD9959()

try:
    with open('static/webinterface_settings.json', 'r') as f:
        web_settings = json.load(f)
except FileNotFoundError:
    web_settings = {"port": 5000,
                    "channel names": {"0": "Channel 0 (DAC0/59)",
                                      "1": "Channel 1 (DAC1/59)",
                                      "2": "Channel 2 (DAC2/59)",
                                      "3": "Channel 3 (DAC3/59)"}}

    with open('static/webinterface_settings.json', 'w') as f:
        json.dump(web_settings, f)

""" ~~~Internal function~~~ """
def get_dds_state():
    """ Gets frequency,amplitude and phase of each channel. """

    channels = []
    for i in range(4):
        channels.append({'id': str(i), 'frequency': DDS.frequencies[i] / 1e6, 
                         'phase': DDS.phases[i], 'amplitude': DDS.amplitudes[i] * 100})
    return channels
    
def set_frequency(channel, frequency):
    """Smooth transition of the frequency output of one channel to a new value.
    
    # Function description
    Reads the current frequency of one channel from the DDS and then ramps to the new frequency withing 50 ms. After the ramp the frequency is set to the new value. When the current output frequency is 0, the new freuqncy is set immediately. A ramp between the two frequencies is only performed when they differ by more than 1 MHz.

    ### Arguments
    * `channel` -- Channel number in [0, 1, 2, 3].
    * `frequency` -- New frequency output in Hz.

    ### Returns
    False when channel was set correctly, otherwise error message.
    """

    dt = 50e-3 # ramp time.

    try:
        channel = int(channel)
    except ValueError:
        return 'Cannot convert <' + str(channel) + '> to int.'
    try:
        f1 = float(frequency)
    except ValueError:
        return 'Cannot convert <' + str(frequency) + '> to float.'

    f0 = DDS.frequencies[channel]
    
    if f0 > 0 and abs(f1 - f0) > 1e6:
        if f0 < f1:
            try:
                DDS.set_ramp_direction(channels=channel, direction='RD')
                DDS.set_freqsweeptime(channels=channel, start_freq=f0, end_freq=f1, sweeptime=dt, no_dwell=False, ioupdate=True, trigger=False)
                DDS.set_ramp_direction(channels=channel, direction='RU')
            except AssertionError as ae:
                return 'Error in AD9959.set_frequency ramp up. Message: ' + ae.args[0]
        else:
            try:
                DDS.set_ramp_direction(channels=channel, direction='RU')
                DDS.set_freqsweeptime(channels=channel, start_freq=f1, end_freq=f0, sweeptime=1e-6, no_dwell=False, ioupdate=True, trigger=False)
                DDS.set_freqsweeptime(channels=channel, start_freq=f1, end_freq=f0, sweeptime=dt, no_dwell=False, ioupdate=True, trigger=False)
                DDS.set_ramp_direction(channels=channel, direction='RD')
            except AssertionError as ae:
                return 'Error in AD9959.set_frequency ramp down. Message: ' + ae.args[0]
        time.sleep(dt)

    try:
        DDS.set_output(channels=channel, value=f1, var='frequency', io_update=True)
    except AssertionError as ae:
        return 'Error in AD9959.set_frequency. Message: ' + ae.args[0]

    return False

def set_amplitude(channel, amplitude):
    """Set the output amplitude of a channel. 
    
    ### Arguments
    * `channel` -- Channel number in [0, 1, 2, 3].
    * `amplitude` -- Scaling factor for new amplitude between 0 and 1

    ### Returns
    False when new amplitude was set, Error message otherwise.
    """

    try:
        channel = int(channel)
    except ValueError:
        return 'Cannot convert <' + str(channel) + '> to int.'
    try:
        amplitude = float(amplitude)
    except ValueError:
        return 'Cannot convert <' + str(amplitude) + '> to float.'

    try:
        DDS.set_output(channels=channel, value=amplitude, var='amplitude', io_update=True)
    except AssertionError as ae:
        return 'Error in set_amplitude. Message: ' + ae.args[0]

    return False

""" ~~~Functions soley used for operating the web page~~~ """

@app.route('/')
def index():
    """Generate the web interface from template file with current DDS settings. """

    channels = get_dds_state()
    return flask.render_template('dds.html', channels=channels, settings=web_settings)

@app.route('/set_apf/<int:channel>', methods=['POST', 'GET'])
def set_APF(channel):
    """Update frequency and amplitude of a DDS channel.

    # Function description
    This function is called when pressing an update button on the web interface. The naming convention for variables on the web interface is <variable type>_<channel number> where channel number is in [0, 1, 2, 3].

    ### Arguments
    * `channel` -- channel number in [0, 1, 2, 3] corresponding to DDS channels.
    * `fkask.request.form` -- The webinterface in which the new settings were entered.

    ### Returns
    Redirects to web interface which then updates the displayed DDS output settings.

    ### Notes
    There is also the possiblity of settings the phase which is currently commented out.
    """

    r = flask.request.form
    amplitude = float(r['amplitude_' + str(channel)])
    #phase = float(r['phase_' + str(channel)])
    frequency = float(r['frequency_' + str(channel)])

    set_frequency(channel, frequency*1e6)
    set_amplitude(channel, amplitude/100)
    
    return flask.redirect(flask.url_for('index'))

@app.route('/reset', methods=['POST', 'GET'])
@auto.doc('public')
def reset_DDS():
    """Resets all DDS channels to 0 output. """

    DDS.init_dds()
    return flask.redirect(flask.url_for('index'))

""" ~~~API functions~~~ """

@app.route('/outputs')
@auto.doc('public')
def get_outputs():
    """Returns the output of each DDS channel. 
    
    ### Returns
    json({<channel number>: {'frequency': <frequency>, 'amplitude': <amplitude>, 'name': <displayed name>})  with the following variables
    * `channel number` -- Physical number of the channel in [0, 1, 2, 3].
    * `frequency` -- Frequency in Hz.
    * `amplitude` -- Amplitude scaling factor between 0 (no output) and 1 (maximum output).
    * `displayed name` -- The name of the channel displayed in the web interface.
    """
    
    channels = get_dds_state()
    resp = {}
    for item in channels:
        resp[item['id']] = {'frequency': item['frequency'] * 1e6, 'amplitude': item['amplitude'], 'name': web_settings['channel names'][item['id']]}
    
    return json.dumps(resp)
    
@app.route('/set_frequency', methods=['POST', 'GET'])
@auto.doc('public')
def set_frequency_output():
    """Set the frequency output of the DDS

    # Function description
    Set the frequency output of the AD9959. The output of each channel will be continuously ramped from the initial frequency to the set value within 50ms. If all channels have to be updated the function will return after 200 ms.

    ### Arguments
    * `input_data` -- dict {<channel number>: <frequency>}
                            <channel number> must be 0, 1, 2, or 3
                            <frequency> must be a valid frequency in Hz.
    ### Returns
    State of all DDS channels.
    """

    input_data = flask.request.args.to_dict()

    for channel, frequency in input_data.items():
        err = set_frequency(channel, frequency)
        if err:
            return json.dumps({'error': err})

    return get_outputs()

@app.route('/set_amplitude', methods=['POST', 'GET'])
@auto.doc('public')
def set_amplitude_output():
    """Set the amplitude of the DDS

    # Function description
     Set the amplitude output of the AD9959. The output of each channel will be continuously ramped from the initial amplitude to the set value.

    ### Arguments
    * `input_data` -- dict {<channel number>: <amplitude>}
                            <channel number> must be 0, 1, 2, or 3
                            <amplitude> must be between 0.001 and 1

    ### Returns
    State of all DDS channels.
    """

    input_data = flask.request.args.to_dict()

    for channel, amplitude in input_data.items():
        err = set_amplitude(channel, amplitude)
        if err:
            return json.dumps({'error': err})

    return get_outputs()

@app.route('/shutdown', methods=['POST', 'GET'])
@auto.doc('public')
def shutdown():
    """ Shuts down the server. """

    func = flask.request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()
    return json.dumps('Server shutting down...')

@app.route('/doc')
def documentation():
    """Shows the documentation rendered by autodoc. """

    return auto.html('public', title='AD9959 (DDS) doc')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(web_settings['port']))
