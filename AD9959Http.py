"""Server for AD9959 running on RPi.

Make sure that flask and flask_autodoc are installed. Then replace add_custom_nl2br_filters(self, app) in 
<python-installation>\Lib\site-packages\flask_autodoc\autrodoc.py by
    _paragraph_re = re.compile(r'(?:\r\n|\r|\n){3,}')

    @app.template_filter()
    @evalcontextfilter
    def nl2br(eval_ctx, value):
        result = '\n\n'.join('%s' % p.replace('\n', '<br>\n')
                             for p in _paragraph_re.split(escape(value)))
        if eval_ctx.autoescape:
            result = Markup(result)
        return result

For starting the server use (export instead of set in linux)
set FLASK_APP=<filename>
(set FLASK_DEBUG=True)
python -m flask run.
"""

import flask
from flask_autodoc import Autodoc
from AD9959 import AD9959
import json
import time

app = flask.Flask(__name__)
auto = Autodoc(app)

DDS = AD9959()

@app.route('/')
def index():
    channels = []
    for i in range(4):
        channels.append({'id': i, 'frequency': DDS.frequencies[i] / 1e6, 
                         'phase': DDS.phases[i], 'amplitude': DDS.amplitudes[i]})

    return flask.render_template('dds.html', channels=channels)

@app.route('/set_apf/<int:channel>', methods=['POST', 'GET'])
def set_APF(channel):
    r = flask.request.form
    amplitude = float(r['amplitude_' + str(channel)])
    phase = float(r['phase_' + str(channel)])
    frequency = float(r['frequency_' + str(channel)])

    print('setting amplitude=%g, phase=%g, frequency=%g for channel %d' % (amplitude, phase, frequency, channel))
    set_frequency(channel, frequency*1e6)
    
    return flask.redirect(flask.url_for('index'))

def set_frequency(channel, frequency):
    dt = 50e-3 # ramp time.

    channel = int(channel)
    f1 = float(frequency)
    
    f0 = DDS.frequencies[channel]

    if f0 > 0 and f1 != f0:
        if f0 < f1:
            DDS.set_ramp_direction(channels=channel, direction='RD')
            DDS.set_freqsweeptime(channels=channel, start_freq=f0, end_freq=f1, sweeptime=dt, no_dwell=False, ioupdate=True, trigger=False)
            DDS.set_ramp_direction(channels=channel, direction='RU')
        else:
            DDS.set_ramp_direction(channels=channel, direction='RU')
            DDS.set_freqsweeptime(channels=channel, start_freq=f1, end_freq=f0, sweeptime=1e-6, no_dwell=False, ioupdate=True, trigger=False)
            DDS.set_freqsweeptime(channels=channel, start_freq=f1, end_freq=f0, sweeptime=dt, no_dwell=False, ioupdate=True, trigger=False)
            DDS.set_ramp_direction(channels=channel, direction='RD')

    time.sleep(dt)
    DDS.set_output(channels=channel, value=f1, var='frequency', io_update=True)

    return True

@app.route('/set_frequency', methods=['POST', 'GET'])
@auto.doc('public')
def set_frequency_output():
    """Set the frequency output of the DDS

    # Function description
    Set the frequency output of the AD9959. The output of each channel will be continuously ramped from the initial frequency to the set value within 50ms. If all channels have to be updated the function will return after 200 ms.

    ### Arguments:
    * `input_data` -- dict {<channel number>: <frequency>}
                            <channel number> must be 0, 1, 2, or 3
                            <frequency> must be a valid frequency in Hz.

    Returns (for GET and POST):
    dict {<channel name>: <voltage>}
          <channel name> 'A', 'B', 'C' and 'D'. 
          <voltage> in [-10 V, 10 V].
    """

    input_data = flask.request.args.to_dict()

    for channel, frequency in input_data.items():
        set_frequency(channel, frequency)
        
    resp = DDS.frequencies

    return json.dumps(resp)

@app.route('/doc')
def documentation():
    """Shows the documentation rendered by autodoc. """

    return auto.html('public', title='AD5764 doc')

@app.route('/shutdown', methods=['POST', 'GET'])
def shutdown():
    func = flask.request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()
    return 'Server shutting down...'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

