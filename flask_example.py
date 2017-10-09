import flask
app = flask.Flask(__name__)

@app.route('/')
def index():
    global channels
    return flask.render_template('dds.html', channels=channels)#amplitude_0=amplitude, phase_0=phase, frequency_0=frequency, amplitude_1=0.5, phase_1=0, frequency_1=2*frequency)

@app.route('/set_apf/<int:channel>', methods=['POST', 'GET'])
def set_APF(channel):
    global channels
    r = flask.request.form
    amplitude = float(r['amplitude_' + str(channel)])
    phase = float(r['phase_' + str(channel)])
    frequency = float(r['frequency_' + str(channel)])

    channels[channel]['amplitude'] = amplitude
    channels[channel]['phase'] = phase
    channels[channel]['frequency'] = frequency

    print('setting amplitude=%g, phase=%g, frequency=%g for channel %d' % (amplitude, phase, frequency, channel))
    return flask.redirect(flask.url_for('index'))


@app.route('/shutdown', methods=['POST', 'GET'])
def shutdown():
    func = flask.request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()
    return 'Server shutting down...'

if __name__ == '__main__':
    global channels
    channels = [{'id':0, 'amplitude': 1, 'phase': 0, 'frequency': 80}, 
                {'id':1, 'amplitude': 0.75, 'phase': 10, 'frequency': 40}, 
                {'id':2, 'amplitude': 0.5, 'phase': 20, 'frequency': 20}, 
                {'id':3, 'amplitude': 0.25, 'phase': 30, 'frequency': 10}]

    app.run(port=80)
